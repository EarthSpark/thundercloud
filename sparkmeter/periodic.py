"""
Periodic asyncio job runner.

Three jobs:

    process_events                       — every 1 min
    process_transactions                 — every 1 min
    nightly_dashboard_tariff_summary     — daily at 00:05 local

Each job's blocking SQLAlchemy work runs in `asyncio.to_thread` so the
event loop stays responsive. `periodic_lifespan` is the FastAPI lifespan
piece that starts these tasks on app startup and cancels them on shutdown.

The job functions reach for Flask's `current_app` for DB access, but
`asyncio.to_thread` runs them on a worker thread that has no Flask
context. `_run_blocking` pushes an explicit app context using the Flask
app stashed on `app.state.flask_app` (by `asgi.create_public_app`)
before invoking the job, so `current_app` resolves correctly inside.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)


async def _run_blocking(fn: Callable[[], None], flask_app: "Flask") -> None:
    """Wrap a sync function in `asyncio.to_thread` with logging.

    Pushes a Flask app context on the worker thread before calling `fn`
    so `current_app` resolves. The job functions still call
    `current_app.app_context()` themselves; Flask allows re-entering an
    app context on the same thread — the inner push stacks on the outer
    and is correctly popped by its `with` block.
    """
    def _wrapped() -> None:
        with flask_app.app_context():
            fn()

    try:
        await asyncio.to_thread(_wrapped)
    except Exception:  # noqa: BLE001
        logger.exception("periodic job %s raised", fn.__name__)


async def every_minute_loop(flask_app: "Flask") -> None:
    """Run `process_events` and `process_transactions` once per minute.

    They run sequentially in the same loop iteration to keep DB contention
    deterministic — they touch overlapping tables in real workloads.
    """
    from sparkmeter.tasks import process_events
    from sparkmeter.transaction.transactiontasks import process_transactions

    while True:
        await _run_blocking(process_events, flask_app)
        await _run_blocking(process_transactions, flask_app)
        await asyncio.sleep(60)


async def nightly_loop(flask_app: "Flask") -> None:
    """Run the daily tariff summary at 00:05 local time."""
    from sparkmeter.dashboard.dashboardtasks import nightly_dashboard_tariff_summary

    while True:
        await asyncio.sleep(_seconds_until(hour=0, minute=5))
        await _run_blocking(nightly_dashboard_tariff_summary, flask_app)


def _seconds_until(hour: int, minute: int) -> float:
    """Seconds from now until the next occurrence of HH:MM local time."""
    now = datetime.now()
    target = datetime.combine(now.date(), time(hour=hour, minute=minute))
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def start_periodic_tasks(flask_app: "Flask") -> list[asyncio.Task]:
    """Spawn the periodic-job loops as asyncio tasks.

    Returns the list of started tasks so the caller can cancel them on
    shutdown.
    """
    tasks = [
        asyncio.create_task(every_minute_loop(flask_app), name="periodic-every-minute"),
        asyncio.create_task(nightly_loop(flask_app), name="periodic-nightly"),
    ]
    logger.info("started %d periodic jobs", len(tasks))
    return tasks


async def stop_periodic_tasks(tasks: list[asyncio.Task]) -> None:
    """Cancel and await all periodic tasks."""
    for t in tasks:
        t.cancel()
    for t in tasks:
        try:
            await t
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            logger.exception("periodic task %s exited with error", t.get_name())


@asynccontextmanager
async def periodic_lifespan(app) -> AsyncIterator[None]:
    """FastAPI lifespan piece that owns the periodic asyncio tasks."""
    flask_app = getattr(app.state, "flask_app", None)
    if flask_app is None:
        raise RuntimeError(
            "periodic lifespan: app.state.flask_app is not set; the ASGI "
            "entrypoint must stash the Flask app there before the lifespan "
            "runs"
        )
    tasks = start_periodic_tasks(flask_app)
    try:
        yield
    finally:
        await stop_periodic_tasks(tasks)
