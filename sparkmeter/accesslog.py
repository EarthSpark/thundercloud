"""
HTTP access log and request ids for the ASGI listeners.

`AccessLogMiddleware` replaces Hypercorn's access log (turned off in
`asgi._serve_both`). It writes one line per request to the
`sparkmeter.access` logger with structured fields: method, path, route
template, status, duration, bytes sent, client, user agent and listener.
The query string is never logged, since it can carry credentials.

Each request gets an id: the caller's `X-Request-ID` when it is well formed
(so an id set by a proxy carries through), otherwise a new one. It is bound
to the logging context while the request is served, so every line logged on
its behalf carries `request_id`, including lines from Flask views, because
a2wsgi runs them in a copy of the context. It is also returned in the
response's `X-Request-ID` header.
"""

import logging
import re
import time
import uuid

import structlog
from structlog.contextvars import bound_contextvars

from sparkmeter.metrics import route_template

_log = structlog.stdlib.get_logger("sparkmeter.access")

REQUEST_ID_HEADER = b"x-request-id"

# A caller-supplied id is used only if it is short and plain, so it can't
# break or forge log lines.
_VALID_REQUEST_ID = re.compile(rb"[A-Za-z0-9._:-]{1,128}")


def _request_id(scope):
    for name, value in scope.get("headers", ()):
        if name.lower() == REQUEST_ID_HEADER and _VALID_REQUEST_ID.fullmatch(value):
            return value.decode("ascii")
    return uuid.uuid4().hex


def _header(scope, wanted):
    for name, value in scope.get("headers", ()):
        if name.lower() == wanted:
            return value.decode("latin-1")
    return None


class AccessLogMiddleware:
    """Pure ASGI middleware: bind a request id, write one access line per request.

    `listener` names the listener in each line (public or internal).
    Successful requests to `quiet_paths`, such as health probes and metrics
    scrapes, are logged at DEBUG so they stay out of the log at the default
    level.
    """

    def __init__(self, app, listener, quiet_paths=()):
        self.app = app
        self.listener = listener
        self.quiet_paths = frozenset(quiet_paths)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id(scope)
        status = 500
        sent = 0

        async def send_logged(message):
            nonlocal status, sent
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", ()))
                if not any(name.lower() == REQUEST_ID_HEADER for name, _ in headers):
                    headers.append((REQUEST_ID_HEADER, request_id.encode("ascii")))
                message = {**message, "headers": headers}
            elif message["type"] == "http.response.body":
                sent += len(message.get("body", b""))
            await send(message)

        started = time.perf_counter()
        with bound_contextvars(request_id=request_id):
            try:
                await self.app(scope, receive, send_logged)
            finally:
                self._write(scope, status, sent, time.perf_counter() - started)

    def _write(self, scope, status, sent, duration):
        path = scope.get("path", "")
        quiet = path in self.quiet_paths and status < 400
        client = scope.get("client")
        _log.log(
            logging.DEBUG if quiet else logging.INFO,
            "%s %s %s",
            scope.get("method"),
            path,
            status,
            method=scope.get("method"),
            path=path,
            route=route_template(scope),
            status=status,
            duration_ms=round(duration * 1000, 1),
            bytes=sent,
            client=client[0] if client else None,
            user_agent=_header(scope, b"user-agent"),
            listener=self.listener,
        )
