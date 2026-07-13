"""
FastAPI lifespan piece for the metering-provider integration.

On ground deployments the lifespan opens an httpx-backed APIClient
against the metering provider, runs the startup reconcile, starts the
SSE consumer task, and hosts the dispatcher. On cloud deployments the
radio code paths are dormant and this lifespan is a no-op.

Other code pulls the client from `app.state.metering` (which is `None`
in cloud mode).
"""

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sparkmeter.metering._generated import APIClient, ClientConfig, HttpxTransport

logger = logging.getLogger(__name__)


def _is_ground() -> bool:
    """Whether this deployment should drive a meter network."""
    try:
        from sparkmeter.config.configdict import config

        return config.is_ground()
    except Exception:  # noqa: BLE001
        return os.environ.get("SPARKMETER_MODE", "ground") == "ground"


@asynccontextmanager
async def metering_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Owns the metering-provider connection on ground; no-op on cloud."""
    if not _is_ground():
        app.state.metering = None
        yield
        return

    base_url = os.environ.get("METERING_PROVIDER_URL", "http://localhost:8000")
    client_id = "webapp-" + uuid.uuid4().hex[:8]

    logger.info("connecting to metering provider: %s (client_id=%s)", base_url, client_id)

    transport = HttpxTransport(
        base_url=base_url,
        timeout=30.0,
        default_headers={"X-Client-Id": client_id},
    )
    client = APIClient(ClientConfig(base_url=base_url), transport=transport)
    app.state.metering = client
    app.state.metering_client_id = client_id

    from sparkmeter.metering import dispatch

    command_queue: asyncio.Queue = asyncio.Queue()
    app.state.metering_command_queue = command_queue
    dispatch.register_loop(asyncio.get_running_loop(), command_queue)
    dispatcher_task = asyncio.create_task(
        dispatch.command_dispatcher(client, command_queue),
        name="metering-command-dispatcher",
    )

    sse_task = asyncio.create_task(_run_sse_consumer(app, client, client_id), name="metering-sse-consumer")

    try:
        from sparkmeter.metering.reconcile import reconcile_all

        # The Flask app is stashed on FastAPI state in asgi.create_public_app
        # so that reconcile's worker-thread DB queries can push an explicit
        # app context. Without this, `current_app` would fail in the thread.
        flask_app = getattr(app.state, "flask_app", None)
        if flask_app is None:
            raise RuntimeError(
                "metering lifespan: app.state.flask_app is not set; the ASGI "
                "entrypoint must stash the Flask app there before the lifespan "
                "runs"
            )

        await reconcile_all(client, flask_app)
    except Exception:
        logger.exception("metering reconcile failed; aborting startup")
        sse_task.cancel()
        dispatcher_task.cancel()
        await client.close()
        raise

    try:
        yield
    finally:
        dispatch.unregister_loop()
        dispatcher_task.cancel()
        sse_task.cancel()
        for task in (dispatcher_task, sse_task):
            try:
                await task
            except asyncio.CancelledError:
                pass
        await client.close()
        app.state.metering = None
        app.state.metering_command_queue = None


async def _run_sse_consumer(app: FastAPI, client: APIClient, client_id: str) -> None:
    """Long-lived task: read events off SSE and dispatch to handlers.

    Reconnects with exponential backoff on disconnect. The generated
    client's iterator yields untyped dicts; `events.dispatch_dict_event`
    structures each into the right typed dataclass before invoking
    handlers.
    """
    from sparkmeter.metering.events import build_handlers, dispatch_dict_event

    handlers = build_handlers(app)
    backoff = 1.0
    while True:
        try:
            async for raw_event in client.default.stream_events_v1_events_get(
                client_id=client_id,
            ):
                backoff = 1.0
                await dispatch_dict_event(raw_event, handlers)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("metering SSE stream broke; reconnecting in %.1fs", backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30.0)
