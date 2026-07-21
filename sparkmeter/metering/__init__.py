"""
Metering-provider integration package.

The webapp talks to a vendor-agnostic metering provider over HTTP+SSE
(with an optional gRPC profile). The gRPC stubs and HTTP models come
from the `meter-driver-spec` package.

Custom modules layered on top:
- `lifespan`    FastAPI lifespan; owns the client + SSE consumer + dispatch
- `dispatch`    sync→async bridge for Flask request handlers
- `events`      SSE event handlers (DB writes, watchdog)
- `reconcile`   startup reconcile registering every meter from DB
- `api`         sync Flask surface (kept stable across this migration)
"""
