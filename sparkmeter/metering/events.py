"""
Event handlers consuming the metering provider's SSE stream.

`http_sse.stream_json_events` yields each SSE frame's `data:` payload as a
JSON dict. Per the Meter Driver Specification every frame is an envelope
`{"type": <event name>, "data": <payload>}`. `dispatch_dict_event` parses
the payload into the matching generated model
(`meter_driver_spec.http.models`) and invokes every registered handler.

Two handlers wired up by `lifespan.py`:

- `build_reading_consumer(app)`: buffers `ElectricalMeterReading` /
  `ElectricalMeterReadingPhased` and flushes them to the reading table in
  batches of 50 or on a flush boundary (a `heartbeat_read_hops` frame or a
  `heartbeat_statistics` frame).

- `build_watchdog(app)`: observes `HeartbeatStatistics`, logs persistent
  network dropouts, and can request a full provider reconnect when the
  active roster unexpectedly drops to zero.

Each handler is `async def handler(event: Any) -> None`.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from meter_driver_spec.http.models import (
    ElectricalMeterReading,
    ElectricalMeterReadingPhased,
    HeartbeatStatistics,
)

from sparkmeter.meter.meterstate import MeterState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import FastAPI

    EventHandler = Callable[[Any], Awaitable[None]]

logger = logging.getLogger(__name__)

# Same batch-size rationale as before: 50 amortizes per-event DB
# transaction overhead at fleet scale.
READING_BATCH_SIZE = 50
READING_FLUSH_INTERVAL_SECONDS = 2.0

# Envelope "type" values that carry a meter reading, mapped to the model
# their "data" payload structures into.
_READING_EVENT_TYPES: dict[str, type] = {
    "electrical_meter_reading": ElectricalMeterReading,
    "electrical_meter_reading_phased": ElectricalMeterReadingPhased,
}

# Envelope "type" values that are observed but not acted on beyond logging.
_SIDE_CHANNEL_TYPES = {
    "gateway_status",
    "node_registered",
    "node_already_registered",
    "node_unregistered",
    "node_to_unregister_unknown",
    "node_firmware_version_changed",
    "invalid_electrical_meter_configuration",
    "electrical_meter_configuration_accepted",
    "electrical_meter_configuration_applied",
    "electrical_meter_balance_and_flags_accepted",
    # "sparknet_configuration_applied" is what SparkNet-Http-New's live HTTP
    # SSE stream actually emits for this event (its own server-side naming,
    # not something Thundercloud controls) -- kept for as long as that
    # specific driver is in use. "driver_configuration_applied" is the
    # vendor-neutral name from the meter-driver-spec.
    "sparknet_configuration_applied",
    "driver_configuration_applied",
}

# Side-channel types worth an INFO line rather than DEBUG.
_SIDE_CHANNEL_INFO_TYPES = {
    "electrical_meter_configuration_accepted",
    "electrical_meter_configuration_applied",
    "invalid_electrical_meter_configuration",
}

# A `heartbeat_read_hops` frame carries no reading but marks a flush boundary.
_READING_FLUSH_MARKER = object()


def build_handlers(app: "FastAPI") -> list["EventHandler"]:
    """Construct the handlers wired up by the SSE consumer task."""
    return [
        build_reading_consumer(app),
        build_watchdog(app),
    ]


async def dispatch_dict_event(raw: dict[str, Any], handlers: list["EventHandler"]) -> None:
    """Parse a raw SSE envelope into the matching event and dispatch it."""
    event_type = raw.get("type")
    if not event_type:
        logger.warning("metering SSE event missing type: %r", raw)
        return
    data = raw.get("data") or {}

    reading_cls = _READING_EVENT_TYPES.get(event_type)
    if reading_cls is not None:
        try:
            event = reading_cls.model_validate(data)
        except Exception:  # noqa: BLE001
            logger.exception("metering SSE reading failed to parse (type=%s)", event_type)
            return
        await _dispatch(event, handlers, event_type)
        return

    if event_type == "heartbeat_statistics":
        try:
            event = HeartbeatStatistics.model_validate(data)
        except Exception:  # noqa: BLE001
            logger.exception("metering SSE heartbeat failed to parse (type=%s)", event_type)
            return
        await _dispatch(event, handlers, event_type)
        return

    if event_type == "heartbeat_read_hops":
        await _dispatch(_READING_FLUSH_MARKER, handlers, event_type)
        return

    if event_type in _SIDE_CHANNEL_TYPES:
        if event_type in _SIDE_CHANNEL_INFO_TYPES:
            logger.info("metering provider side-channel event observed: %s", event_type)
        else:
            logger.debug("metering provider side-channel event observed: %s", event_type)
        return

    logger.warning("metering SSE event unknown type=%r", event_type)


async def _dispatch(event: Any, handlers: list["EventHandler"], event_type: str) -> None:
    """Invoke every handler with the event, isolating handler failures."""
    for handler in handlers:
        try:
            await handler(event)
        except Exception:  # noqa: BLE001
            logger.exception("metering event handler failed (type=%s)", event_type)


def build_reading_consumer(app: "FastAPI") -> "EventHandler":
    """Buffer reading events and flush them at batch size or heartbeat boundaries."""
    pending: list[ElectricalMeterReading | ElectricalMeterReadingPhased] = []
    flush_lock = asyncio.Lock()
    flask_app = getattr(app.state, "flask_app", None) if app is not None else None
    flush_task: asyncio.Task | None = None

    async def flush_pending() -> None:
        nonlocal flush_task
        async with flush_lock:
            if not pending:
                flush_task = None
                return
            batch = list(pending)
            pending.clear()
            flush_task = None
        await _flush_readings(batch, flask_app)

    async def cancel_flush_task() -> None:
        nonlocal flush_task
        task = flush_task
        if task is None or task.done():
            return
        flush_task = None
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def delayed_flush() -> None:
        try:
            await asyncio.sleep(READING_FLUSH_INTERVAL_SECONDS)
            await flush_pending()
        except asyncio.CancelledError:
            raise

    async def consumer(event: Any) -> None:
        nonlocal flush_task
        if event is _READING_FLUSH_MARKER or isinstance(event, HeartbeatStatistics):
            await cancel_flush_task()
            await flush_pending()
            return
        if not isinstance(event, (ElectricalMeterReading, ElectricalMeterReadingPhased)):
            return
        should_flush = False
        should_start_timer = False
        async with flush_lock:
            pending.append(event)
            should_flush = len(pending) >= READING_BATCH_SIZE
            should_start_timer = not should_flush and (flush_task is None or flush_task.done())
            if should_start_timer:
                flush_task = asyncio.create_task(
                    delayed_flush(),
                    name="metering-reading-flush",
                )
        if should_flush:
            await cancel_flush_task()
            await flush_pending()

    return consumer


async def _flush_readings(
    batch: list[ElectricalMeterReading | ElectricalMeterReadingPhased],
    flask_app,
) -> None:
    """Persist a batch of reading events to the DB.

    DB writes are blocking SQLAlchemy operations; run them in a thread
    so the event loop stays responsive.
    """
    try:
        await asyncio.to_thread(_write_readings_sync, batch, flask_app)
    except Exception:  # noqa: BLE001
        logger.exception("metering reading flush failed (batch size=%d)", len(batch))


def _write_readings_sync(
    batch: list[ElectricalMeterReading | ElectricalMeterReadingPhased],
    flask_app,
) -> None:
    from sparkmeter.controller import add_reading
    from sparkmeter.exceptions import DatabaseLockTimeoutException, DuplicateReadingException
    from sparkmeter.misc.datetimeutils import datetime_from_timestamp_string

    if flask_app is None:
        raise RuntimeError(
            "metering reading flush requires a Flask app context; app.state.flask_app is not set"
        )

    with flask_app.app_context():
        for event in batch:
            try:
                if not (event.period_start and event.period_end):
                    logger.warning(
                        "discarding reading from meter %s: incomplete heartbeat window "
                        "(period_start=%r, period_end=%r)",
                        event.node_id,
                        event.period_start,
                        event.period_end,
                    )
                    continue
                heartbeat_start = datetime_from_timestamp_string(event.period_start)
                heartbeat_end = datetime_from_timestamp_string(event.period_end)

                # The phased variant carries the same aggregate figures at the
                # top level as the non-phased one (plus per-phase fields the
                # reading table does not store), so both write identically.
                # The spec's ElectricalMeterState ids are sparkmeter's MeterState
                # ids (both -1..13); add_reading takes the state *name*.
                reading_data = dict(
                    meter=int(event.node_id),
                    state=MeterState.get_state_name_from_id(int(event.state.value)),
                    uptime=int(event.uptime_secs),
                    heartbeat_start=heartbeat_start,
                    heartbeat_end=heartbeat_end,
                    frequency=float(event.frequency),
                    voltage_min=float(event.voltage_min),
                    voltage_max=float(event.voltage_max),
                    voltage_avg=float(event.voltage_avg),
                    current_min=float(event.current_min),
                    current_max=float(event.current_max),
                    current_avg=float(event.current_avg),
                    energy=float(event.energy),
                    true_power_inst=float(event.true_power_inst),
                    true_power_avg=float(event.true_power_avg),
                    apparent_power_avg=float(event.apparent_power_avg),
                    power_factor_avg=float(event.power_factor_avg),
                    user_power_limit=float(event.user_power_limit),
                )
                try:
                    add_reading(reading_data, update_meter_state=False)
                except DatabaseLockTimeoutException:
                    logger.error(
                        "discarding reading from meter %s: db lock timeout",
                        event.node_id,
                    )
                    flask_app.sentry.captureException(
                        message=f"Meter {event.node_id} reading lock timeout",
                        tags={"action": "reading"},
                    )
                except DuplicateReadingException:
                    logger.warning("discarding duplicate reading from meter %s", event.node_id)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "failed to write reading for node_id=%s",
                    getattr(event, "node_id", "?"),
                )


def build_watchdog(app: "FastAPI") -> "EventHandler":
    """Observe heartbeat summaries; log persistent dropouts.

    The webapp no longer owns the provider process, but it can still
    request a reconnect when the provider unexpectedly reports an empty
    roster after previously seeing active meters. Tunables:
        METERING_WATCHDOG_MIN_NODES   minimum registered-node count
                                       before the dropout check is
                                       meaningful (default 10)
        METERING_WATCHDOG_MAX_DROPOUTS  consecutive dropout heartbeats
                                         that trigger a warning
                                         (default 3)
    """
    import os

    min_nodes_for_check = int(os.environ.get("METERING_WATCHDOG_MIN_NODES", "10"))
    max_consecutive_dropouts = int(os.environ.get("METERING_WATCHDOG_MAX_DROPOUTS", "3"))

    state = {
        "consecutive_dropouts": 0,
        "warned": False,
        "saw_registered_meters": False,
        "restart_requested": False,
    }

    async def watchdog(event: Any) -> None:
        if not isinstance(event, HeartbeatStatistics):
            return

        registered = event.total_registered_nodes
        attempted = event.nodes_reached_out_to_in_current_heartbeat
        responded = event.nodes_heard_from_in_current_heartbeat

        logger.info(
            "metering heartbeat summary: registered=%d attempted=%d responded=%d",
            registered,
            attempted,
            responded,
        )

        if registered > 0:
            state["saw_registered_meters"] = True
            state["restart_requested"] = False
        elif state["saw_registered_meters"] and not state["restart_requested"]:
            logger.warning("metering watchdog: provider roster dropped to zero; scheduling reconcile")
            gateway_state = getattr(getattr(app, "state", None), "metering_gateway_state", None)
            if gateway_state is not None:
                gateway_state["needs_full_restart"] = True
            state["restart_requested"] = True

        if registered < min_nodes_for_check:
            state["consecutive_dropouts"] = 0
            state["warned"] = False
            return

        all_dropped = attempted > 0 and responded == 0
        if all_dropped:
            state["consecutive_dropouts"] += 1
        else:
            state["consecutive_dropouts"] = 0
            state["warned"] = False

        if state["consecutive_dropouts"] >= max_consecutive_dropouts and not state["warned"]:
            logger.warning(
                "metering watchdog: %d consecutive dropout heartbeats; provider may be stuck",
                state["consecutive_dropouts"],
            )
            state["warned"] = True

    return watchdog
