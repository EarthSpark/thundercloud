"""
FastAPI lifespan piece for the metering-provider integration.

On ground deployments the lifespan opens the selected command/event
transports against the metering provider, runs the startup reconcile,
starts the event consumer task, and hosts the dispatcher. On cloud
deployments the radio code paths are dormant and this lifespan is a
no-op.

Other code pulls the client from `app.state.metering` (which is `None`
in cloud mode).
"""

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncIterator
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from sparkmeter.metering.provider_config import configured_provider_url
from sparkmeter.metering.runtime_client import build_command_client, build_event_client
from sparkmeter.metering.runtime_registry import get_running_app

logger = logging.getLogger(__name__)
_GATEWAY_RECOVERY_POLL_SECONDS = 5.0


class _ProviderRemovedDuringRecovery(RuntimeError):
    """Raised when the configured driver disappears during gateway recovery."""


def _is_ground() -> bool:
    """Whether this deployment should drive a meter network."""
    try:
        from sparkmeter.config.configdict import config

        return config.is_ground()
    except Exception:  # noqa: BLE001
        return os.environ.get("SPARKMETER_MODE", "ground") == "ground"


def _metering_enabled() -> bool:
    """Whether metering-provider startup should run for this process."""
    try:
        from sparkmeter.config.configdict import config

        return not bool(config.get("OFFLINE", False))
    except Exception:  # noqa: BLE001
        return os.environ.get("SM_OFFLINE", "").lower() not in {"1", "true", "yes", "on"}


def _initialize_configured_providers_with_app_context(flask_app, timeout):
    """Run the startup init pass inside an explicit Flask app context."""
    from sparkmeter.config.provider_settings import initialize_configured_providers_on_startup

    if flask_app is None:
        raise RuntimeError(
            "metering lifespan: app.state.flask_app is not set; the ASGI "
            "entrypoint must stash the Flask app there before startup init runs"
        )

    with flask_app.app_context():
        return initialize_configured_providers_on_startup(timeout)


def _enabled_provider_signature(flask_app):
    """Return a stable signature for the currently enabled provider."""
    if flask_app is None:
        return None

    try:
        from sparkmeter.config.provider_settings import get_enabled_provider

        with flask_app.app_context():
            provider = get_enabled_provider()
    except Exception:  # noqa: BLE001
        logger.exception("failed to load enabled provider signature")
        return None

    if provider is None:
        return None

    return _provider_signature(provider)


def _provider_signature(provider):
    """Return a stable signature tuple for a provider record."""
    if provider is None:
        return None

    return (
        str(provider.get("id") or ""),
        str(provider.get("base_url") or ""),
        str(provider.get("selected_interface") or ""),
        bool(provider.get("enabled")),
    )


async def shutdown_metering_runtime(app: FastAPI) -> None:
    """Stop the live metering runtime owned by this FastAPI app."""
    from sparkmeter.metering import dispatch

    dispatch.unregister_loop()

    dispatcher_task = getattr(app.state, "metering_dispatcher_task", None)
    sse_task = getattr(app.state, "metering_sse_task", None)
    for task in (dispatcher_task, sse_task):
        if task is not None:
            task.cancel()
    for task in (dispatcher_task, sse_task):
        if task is None:
            continue
        try:
            await task
        except asyncio.CancelledError:
            pass

    event_client = getattr(app.state, "metering_event_client", None)
    if event_client is not None:
        await event_client.close()

    client = getattr(app.state, "metering", None)
    if client is not None:
        await client.close()

    app.state.metering = None
    app.state.metering_client_id = None
    app.state.metering_command_queue = None
    app.state.metering_gateway_state = None
    app.state.metering_dispatcher_task = None
    app.state.metering_sse_task = None
    app.state.metering_event_client = None
    app.state.metering_provider_signature = None


async def ensure_metering_runtime(
    app: FastAPI,
    *,
    skip_provider_init: bool = False,
) -> bool:
    """Ensure live metering is active for the currently configured provider."""
    if not _is_ground():
        app.state.metering = None
        return False

    if not _metering_enabled():
        logger.info("metering provider disabled in offline mode; skipping startup")
        app.state.metering = None
        return False

    flask_app = getattr(app.state, "flask_app", None)
    desired_signature = _enabled_provider_signature(flask_app)
    existing_client = getattr(app.state, "metering", None)
    running_signature = getattr(app.state, "metering_provider_signature", None)

    if (
        existing_client is not None
        and running_signature == desired_signature
        and desired_signature is not None
    ):
        logger.info("metering runtime already active; re-running init and reconcile")
        await _run_provider_reconcile(app, skip_provider_init=skip_provider_init)
        return True

    if existing_client is not None:
        logger.info("metering runtime configuration changed; restarting live metering")
        await shutdown_metering_runtime(app)

    runtime_provider_initialized = False
    if not skip_provider_init:
        try:
            init_results = await asyncio.to_thread(
                _initialize_configured_providers_with_app_context,
                flask_app,
                10.0,
            )
            for result in init_results:
                provider = result.get("provider") or {}
                provider_name = provider.get("name") or provider.get("base_url") or "meter driver"
                if _provider_signature(provider) == desired_signature and result.get("success"):
                    runtime_provider_initialized = True
                if result.get("success"):
                    logger.info("metering startup init succeeded for %s", provider_name)
                elif result.get("attempted"):
                    logger.warning(
                        "metering startup init failed for %s: %s",
                        provider_name,
                        result.get("reason") or "unknown error",
                    )
                else:
                    logger.info(
                        "metering startup init skipped for %s: %s",
                        provider_name,
                        result.get("reason") or "not configured",
                    )
        except Exception:
            logger.exception("metering startup init pass failed")

    base_url = configured_provider_url(default="", flask_app=flask_app)
    if not base_url:
        logger.info("metering provider is not configured; skipping startup")
        app.state.metering = None
        return False

    client_id = "webapp-" + uuid.uuid4().hex[:8]
    logger.info("connecting to metering provider: %s (client_id=%s)", base_url, client_id)

    provider = None
    provider_details = None
    try:
        from sparkmeter.config.provider_settings import get_enabled_provider, get_live_interface_details

        with flask_app.app_context():
            provider = get_enabled_provider()
            if provider is not None:
                provider_details = get_live_interface_details(
                    provider["base_url"],
                    selected_interface=provider["selected_interface"],
                )
    except Exception:  # noqa: BLE001
        logger.exception("failed to resolve selected provider interface; falling back to HTTP")

    if provider is None:
        provider = {
            "base_url": base_url,
            "selected_interface": "http",
        }

    client = build_command_client(provider, client_id, provider_details=provider_details)
    event_client = build_event_client(provider, client_id, provider_details=provider_details)
    logger.info(
        "metering provider command transport=%s event transport=%s",
        getattr(client, "transport_name", type(client).__name__),
        getattr(event_client, "transport_name", type(event_client).__name__),
    )

    from sparkmeter.metering import dispatch

    command_queue: asyncio.Queue = asyncio.Queue()
    commands_allowed = asyncio.Event()
    commands_allowed.set()

    app.state.metering = client
    app.state.metering_client_id = client_id
    app.state.metering_command_queue = command_queue
    app.state.metering_gateway_state = {
        "gateway_connected": None,
        "gateway_paused": False,
        "gateway_recovery_task": None,
        "needs_full_restart": False,
        "commands_allowed": commands_allowed,
    }
    app.state.metering_event_client = event_client
    app.state.metering_provider_signature = desired_signature

    dispatch.register_loop(asyncio.get_running_loop(), command_queue)
    dispatcher_task = asyncio.create_task(
        dispatch.command_dispatcher(client, command_queue, commands_allowed=commands_allowed),
        name="metering-command-dispatcher",
    )
    sse_task = asyncio.create_task(
        _run_sse_consumer(app, event_client, client_id), name="metering-sse-consumer"
    )
    app.state.metering_dispatcher_task = dispatcher_task
    app.state.metering_sse_task = sse_task

    try:
        await _run_provider_reconcile(
            app,
            skip_provider_init=skip_provider_init or runtime_provider_initialized,
        )
    except Exception:
        logger.exception("metering reconcile failed; aborting startup")
        await shutdown_metering_runtime(app)
        raise

    return True


def activate_metering_runtime_in_process(
    timeout: float = 15.0,
    *,
    skip_provider_init: bool = False,
) -> tuple[bool, str | None]:
    """Try to activate live metering inside the already-running ASGI process."""
    try:
        public_app = get_running_app()
        if public_app is None:
            return False, "public app is not available"

        loop = getattr(public_app.state, "main_loop", None)
        if loop is None:
            return False, "main event loop is not available"

        future = asyncio.run_coroutine_threadsafe(
            ensure_metering_runtime(public_app, skip_provider_init=skip_provider_init),
            loop,
        )
        return bool(future.result(timeout=timeout)), None
    except FutureTimeoutError:
        logger.exception("timed out activating live metering runtime")
        return False, "timed out activating live metering runtime"
    except Exception as exc:  # noqa: BLE001
        logger.exception("failed to activate live metering runtime")
        return False, str(exc)


@asynccontextmanager
async def metering_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Owns the metering-provider connection on ground; no-op on cloud."""
    if not _is_ground():
        app.state.metering = None
        yield
        return

    if not _metering_enabled():
        logger.info("metering provider disabled in offline mode; skipping startup")
        app.state.metering = None
        yield
        return

    started = await ensure_metering_runtime(app)
    if not started:
        yield
        return

    try:
        yield
    finally:
        await shutdown_metering_runtime(app)


async def _run_sse_consumer(app: FastAPI, event_client, client_id: str) -> None:
    """Long-lived task: read events off SSE and dispatch to handlers.

    Reconnects with exponential backoff on disconnect. The generated
    client's iterator yields untyped dicts; `events.dispatch_dict_event`
    structures each into the right typed dataclass before invoking
    handlers.
    """
    from sparkmeter.metering.events import build_handlers, dispatch_dict_event

    handlers = build_handlers(app)
    backoff = 1.0
    has_connected_once = False
    while True:
        await _run_pending_provider_restart(app)
        gateway_state = getattr(app.state, "metering_gateway_state", {}) or {}
        try:
            saw_event_this_connection = False
            async for raw_event in event_client.stream_events(
                client_id=client_id,
            ):
                backoff = 1.0
                saw_event_this_connection = True
                has_connected_once = True
                await _observe_gateway_status(app, raw_event)
                await dispatch_dict_event(raw_event, handlers)
                await _run_pending_provider_restart(app)
            if has_connected_once or saw_event_this_connection:
                logger.warning("metering SSE stream ended; treating provider as restarted")
                gateway_state["needs_full_restart"] = True
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("metering SSE stream broke; reconnecting in %.1fs", backoff)
            if has_connected_once:
                gateway_state["needs_full_restart"] = True
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30.0)


async def _run_pending_provider_restart(app: FastAPI) -> None:
    """Run a deferred init/reconcile pass when provider state demands it."""
    gateway_state = getattr(app.state, "metering_gateway_state", {}) or {}
    if not gateway_state.get("needs_full_restart"):
        return
    if gateway_state.get("gateway_paused"):
        logger.info("metering provider is paused for gateway recovery; deferring restart reconcile")
        return
    logger.warning("metering provider state changed; re-running init and reconcile")
    await _run_provider_reconcile(app)
    gateway_state["needs_full_restart"] = False


async def _run_provider_reconcile(
    app: FastAPI,
    *,
    skip_provider_init: bool = False,
) -> None:
    """Re-run full provider init and meter reconcile."""
    from sparkmeter.metering.reconcile import reconcile_all

    client = getattr(app.state, "metering", None)
    flask_app = getattr(app.state, "flask_app", None)
    if client is None or flask_app is None:
        raise RuntimeError("metering provider reconcile requires active client and flask app")
    await reconcile_all(client, flask_app, skip_provider_init=skip_provider_init)


async def _observe_gateway_status(app: FastAPI, raw_event) -> None:
    """Pause command flow when the gateway disconnects and trigger recovery."""
    if raw_event.get("type") != "gateway_status":
        return

    gateway_state = getattr(app.state, "metering_gateway_state", None)
    if gateway_state is None:
        return

    gateway_data = raw_event.get("data") or {}
    connected = bool(gateway_data.get("connected"))
    previous_connected = gateway_state.get("gateway_connected")
    gateway_state["gateway_connected"] = connected

    if connected:
        if previous_connected is not True:
            logger.info("metering provider gateway reported connected")
        if gateway_state.get("gateway_paused"):
            logger.info("metering provider gateway reconnected via event stream; stopping recovery polling")
            await _cancel_gateway_recovery_poll(gateway_state)
            gateway_state["gateway_paused"] = False
            gateway_state["needs_full_restart"] = True
            gateway_state["commands_allowed"].set()
        return

    if gateway_state.get("gateway_paused"):
        return

    if previous_connected is not False:
        logger.warning("metering provider gateway reported disconnected; pausing commands until recovery")
    gateway_state["gateway_paused"] = True
    gateway_state["commands_allowed"].clear()

    recovery_task = gateway_state.get("gateway_recovery_task")
    if recovery_task is None or recovery_task.done():
        gateway_state["gateway_recovery_task"] = asyncio.create_task(
            _recover_provider_after_gateway_loss(app),
            name="metering-gateway-recovery",
        )


async def _cancel_gateway_recovery_poll(gateway_state) -> None:
    """Stop the disconnect polling task once live gateway events say it recovered."""
    recovery_task = gateway_state.get("gateway_recovery_task")
    if recovery_task is None or recovery_task.done():
        gateway_state["gateway_recovery_task"] = None
        return

    recovery_task.cancel()
    try:
        await recovery_task
    except asyncio.CancelledError:
        pass
    gateway_state["gateway_recovery_task"] = None


async def _recover_provider_after_gateway_loss(app: FastAPI) -> None:
    """Poll for gateway recovery, then re-run init/reconcile before resuming commands."""
    gateway_state = getattr(app.state, "metering_gateway_state", None)
    if gateway_state is None:
        return

    try:
        while True:
            try:
                await _wait_for_gateway_online(app)
            except _ProviderRemovedDuringRecovery:
                logger.info(
                    "metering provider configuration was removed during gateway recovery; "
                    "shutting down live metering"
                )
                await shutdown_metering_runtime(app)
                return
            logger.info("metering provider gateway is reachable again; re-running init and reconcile")
            try:
                await _run_provider_reconcile(app)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "metering provider recovery reconcile failed; retrying in %.1fs",
                    _GATEWAY_RECOVERY_POLL_SECONDS,
                )
                await asyncio.sleep(_GATEWAY_RECOVERY_POLL_SECONDS)
                continue

            gateway_state["gateway_connected"] = True
            gateway_state["gateway_paused"] = False
            gateway_state["needs_full_restart"] = False
            gateway_state["commands_allowed"].set()
            logger.info("metering provider resumed after gateway recovery")
            return
    except asyncio.CancelledError:
        raise
    finally:
        latest_state = getattr(app.state, "metering_gateway_state", None)
        if latest_state is not None:
            latest_state["gateway_recovery_task"] = None


async def _wait_for_gateway_online(app: FastAPI) -> None:
    """Poll the provider status endpoint until the gateway reports connected."""
    flask_app = getattr(app.state, "flask_app", None)
    while True:
        base_url = configured_provider_url(default="", flask_app=flask_app).rstrip("/")
        if not base_url:
            raise _ProviderRemovedDuringRecovery
        status_url = base_url + "/v1/status"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(status_url)
                response.raise_for_status()
                payload = response.json()
            if bool(payload.get("connected")):
                return
            logger.info(
                "metering provider gateway still disconnected; waiting %.1fs before retry",
                _GATEWAY_RECOVERY_POLL_SECONDS,
            )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.info(
                "metering provider status unavailable during gateway recovery; retrying in %.1fs",
                _GATEWAY_RECOVERY_POLL_SECONDS,
            )
        await asyncio.sleep(_GATEWAY_RECOVERY_POLL_SECONDS)
