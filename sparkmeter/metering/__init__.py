"""
Metering-provider integration package.

The webapp talks to a vendor-agnostic metering provider over HTTP+SSE.
The generated client (in `_generated/`) is regenerated from the
provider's `openapi.json` via `scripts/regen-metering-wire.sh`.

Custom modules layered on top:
- `lifespan`    FastAPI lifespan; owns the client + SSE consumer + dispatch
- `dispatch`    sync→async bridge for Flask request handlers
- `events`      SSE event handlers (DB writes, log forwarding, watchdog)
- `reconcile`   startup reconcile registering every meter from DB
- `api`         sync Flask surface (kept stable across this migration)
"""
