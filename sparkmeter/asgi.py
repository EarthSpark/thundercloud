#!/usr/bin/env python
"""
ASGI entrypoint.

Wraps the existing Flask WSGI app inside a FastAPI ASGI app via Starlette's
WSGIMiddleware. The Flask app handles all existing routes; native FastAPI
routes are added separately for new functionality (metering-provider
integration, admin proxy, etc.).

Two ASGI servers run in this process:
- Public app on port 5000 (mapped externally) — Flask routes + public FastAPI routes
- Internal app on port 5001 (NOT mapped) — admin endpoints

Run as:
    python -m sparkmeter.asgi
or directly via Hypercorn against `sparkmeter.asgi:public_app` for development.
"""

import asyncio
import os
import signal
import sys

from a2wsgi import WSGIMiddleware
from fastapi import FastAPI

# Ensure the webapp dir is importable when running as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contextlib import asynccontextmanager  # noqa: E402

from sparkmeter.app import SparkmeterApplication  # noqa: E402
from sparkmeter.cli import register_cli_commands  # noqa: E402
from sparkmeter.metering.lifespan import metering_lifespan  # noqa: E402
from sparkmeter.periodic import periodic_lifespan  # noqa: E402


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Compose periodic_lifespan and metering_lifespan.

    metering_lifespan is wrapped on the inside so its teardown (drain
    SSE / dispatch) runs before periodic jobs are cancelled.
    """
    async with periodic_lifespan(app):
        async with metering_lifespan(app):
            yield


def create_flask_app() -> SparkmeterApplication:
    """Build and bootstrap the underlying Flask app."""
    flask_app = SparkmeterApplication(mode=SparkmeterApplication.MODE_PRODUCTION)
    register_cli_commands(flask_app)
    flask_app.bootstrap()
    return flask_app


def create_public_app() -> FastAPI:
    """The public-facing ASGI app: wraps Flask, plus any public FastAPI routes.

    The metering-provider client is owned by this app's lifespan and lives
    for the lifetime of the public app. The internal app shares it via
    `app.state.metering` (see `create_internal_app`).
    """
    api = FastAPI(
        title="sparkmeter-public",
        docs_url=None,
        redoc_url=None,
        lifespan=app_lifespan,
    )

    @api.get("/health")
    async def health():
        # Lightweight liveness probe used by the compose healthcheck.
        return {"status": "ok"}

    flask_app = create_flask_app()
    # Stash the Flask app on FastAPI state so the metering lifespan (and any
    # other background coroutine that needs to run Flask-context-bound DB
    # work in a worker thread) can reach it without using `current_app`,
    # which is bound to a per-request thread-local that lifespan threads
    # never enter.
    api.state.flask_app = flask_app
    # Mount Flask under "/" — FastAPI's own routes take precedence; everything
    # else falls through to the WSGI app.
    api.mount("/", WSGIMiddleware(flask_app))
    return api


def create_internal_app(public_app: FastAPI) -> FastAPI:
    """The internal ASGI app: admin endpoints. Not network-exposed.

    Shares the public app's metering-provider client via
    `app.state.metering`. CLI tools that talk directly to the metering
    provider use the provider's HTTP API, not this app.
    """
    api = FastAPI(title="sparkmeter-internal", docs_url=None, redoc_url=None)

    @api.middleware("http")
    async def share_metering_state(request, call_next):
        request.app.state.metering = getattr(public_app.state, "metering", None)
        return await call_next(request)

    return api


# Module-level apps are constructed lazily on first attribute access so that
# `import sparkmeter.asgi` does not trigger a full Flask bootstrap (which needs
# a live DB connection). ASGI servers reference these by attribute, which fires
# the factory at first access. Tests / introspection that just want to import
# the module don't pay that cost.


def __getattr__(name):  # PEP 562 module-level __getattr__
    if name == "public_app":
        app = create_public_app()
        globals()["public_app"] = app
        return app
    if name == "internal_app":
        public = globals().get("public_app") or create_public_app()
        globals()["public_app"] = public
        app = create_internal_app(public)
        globals()["internal_app"] = app
        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def _serve_both() -> None:
    """Run both ASGI servers in this process, sharing one shutdown signal."""
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    public = create_public_app()
    internal = create_internal_app(public)

    public_cfg = Config()
    public_cfg.bind = [os.environ.get("PUBLIC_BIND", "0.0.0.0:5000")]
    public_cfg.accesslog = "-"
    public_cfg.errorlog = "-"

    internal_cfg = Config()
    internal_cfg.bind = [os.environ.get("INTERNAL_BIND", "0.0.0.0:5001")]
    internal_cfg.accesslog = "-"
    internal_cfg.errorlog = "-"

    shutdown = asyncio.Event()

    def _trigger():
        shutdown.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _trigger)

    await asyncio.gather(
        serve(public, public_cfg, shutdown_trigger=shutdown.wait),
        serve(internal, internal_cfg, shutdown_trigger=shutdown.wait),
    )


def main() -> None:
    asyncio.run(_serve_both())


if __name__ == "__main__":
    main()
