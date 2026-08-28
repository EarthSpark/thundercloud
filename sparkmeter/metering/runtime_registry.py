"""Process-global handle on the running public ASGI app.

The sync→async metering bridge (`activate_metering_runtime_in_process`) runs
inside a synchronous Flask request handler with no request-scoped reference to
the ASGI app it needs to reach. `create_public_app` publishes the app here via
`set_running_app`; the bridge reads it back via `get_running_app`. This is an
explicit typed accessor in place of reflecting over `sys.modules`.

Dependency-free by design: it imports only `typing`, so it can be pulled in from
anywhere without dragging in FastAPI at import time.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

_running_public_app = None


def set_running_app(app: "FastAPI | None") -> None:
    """Publish the running public ASGI app for the sync bridge to reach."""
    global _running_public_app
    _running_public_app = app


def get_running_app() -> "FastAPI | None":
    """Return the running public ASGI app, or `None` if none is published."""
    return _running_public_app
