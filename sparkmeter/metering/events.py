"""
Event handlers consuming the metering provider's SSE stream.

The generated `stream_events_v1_events_get` yields untyped dicts.
`dispatch_dict_event` routes each into a typed dataclass via the
discriminator metadata, then invokes every registered handler.

Three handlers wired up by `lifespan.py`:

- `build_reading_consumer(app)`: buffers `MeterReadingEvent` /
  `MeterReadingPhasedEvent` and flushes them to the reading table in
  batches.

- `build_log_consumer(app)`: forwards `LogEvent` into the Python
  logging system.

- `build_watchdog(app)`: observes `HeartbeatSummaryEvent`, logs
  persistent network dropouts. The webapp no longer owns the
  underlying provider process so the watchdog only logs.

Each handler is `async def handler(event: Any) -> None`.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from sparkmeter.metering._generated.core.cattrs_converter import structure_from_dict
from sparkmeter.metering._generated.models.heartbeat_summary_event import HeartbeatSummaryEvent
from sparkmeter.metering._generated.models.log_event import LogEvent
from sparkmeter.metering._generated.models.log_level import LogLevel
from sparkmeter.metering._generated.models.meter_reading_event import MeterReadingEvent
from sparkmeter.metering._generated.models.meter_reading_phased_event import MeterReadingPhasedEvent
from sparkmeter.metering._generated.models.stream_events_v_1_events_get_200_response import (
    StreamEventsV1EventsGet200ResponseDiscriminator,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import FastAPI

    EventHandler = Callable[[Any], Awaitable[None]]

logger = logging.getLogger(__name__)

# Same batch-size rationale as before: 50 amortizes per-event DB
# transaction overhead at fleet scale.
READING_BATCH_SIZE = 50

_EVENT_DISCRIMINATOR = StreamEventsV1EventsGet200ResponseDiscriminator()


def build_handlers(app: "FastAPI") -> list["EventHandler"]:
    """Construct the handlers wired up by the SSE consumer task."""
    return [
        build_reading_consumer(app),
        build_log_consumer(app),
        build_watchdog(app),
    ]


async def dispatch_dict_event(raw: dict[str, Any], handlers: list["EventHandler"]) -> None:
    """Structure a raw SSE dict into the right typed event and dispatch it."""
    event_type = raw.get("event_type")
    if not event_type:
        logger.warning("metering SSE event missing event_type: %r", raw)
        return
    target_class = _EVENT_DISCRIMINATOR.get_mapping().get(event_type)
    if target_class is None:
        logger.warning("metering SSE event unknown event_type=%r", event_type)
        return
    try:
        event = structure_from_dict(raw, target_class)
    except Exception:  # noqa: BLE001
        logger.exception("metering SSE event failed to structure (event_type=%s)", event_type)
        return
    for handler in handlers:
        try:
            await handler(event)
        except Exception:  # noqa: BLE001
            logger.exception("metering event handler failed (event_type=%s)", event_type)


def build_reading_consumer(app: "FastAPI") -> "EventHandler":
    """Buffer reading events and flush them to the DB in batches."""
    pending: list[MeterReadingEvent | MeterReadingPhasedEvent] = []

    async def consumer(event: Any) -> None:
        if not isinstance(event, (MeterReadingEvent, MeterReadingPhasedEvent)):
            return
        pending.append(event)
        if len(pending) >= READING_BATCH_SIZE:
            batch = list(pending)
            pending.clear()
            await _flush_readings(batch)

    return consumer


async def _flush_readings(
    batch: list[MeterReadingEvent | MeterReadingPhasedEvent],
) -> None:
    """Persist a batch of reading events to the DB.

    DB writes are blocking SQLAlchemy operations; run them in a thread
    so the event loop stays responsive.
    """
    try:
        await asyncio.to_thread(_write_readings_sync, batch)
    except Exception:  # noqa: BLE001
        logger.exception("metering reading flush failed (batch size=%d)", len(batch))


def _write_readings_sync(
    batch: list[MeterReadingEvent | MeterReadingPhasedEvent],
) -> None:
    from flask import current_app

    from sparkmeter.controller import add_reading
    from sparkmeter.exceptions import DatabaseLockTimeoutException, DuplicateReadingException
    from sparkmeter.misc.datetimeutils import datetime_from_timestamp_string

    with current_app.app_context():
        for event in batch:
            try:
                if not (event.period_start and event.period_end):
                    logger.warning(
                        "discarding reading from meter %s: missing heartbeat timestamps",
                        event.meter_id,
                    )
                    continue
                heartbeat_start = datetime_from_timestamp_string(event.period_start)
                heartbeat_end = datetime_from_timestamp_string(event.period_end)

                if isinstance(event, MeterReadingPhasedEvent):
                    agg = event.aggregate
                    reading_data = dict(
                        meter=int(event.meter_id),
                        state=event.state.value if event.state else "unknown",
                        uptime=int(event.uptime_seconds),
                        heartbeat_start=heartbeat_start,
                        heartbeat_end=heartbeat_end,
                        frequency=int(agg.frequency_hz),
                        voltage_min=int(agg.voltage_min),
                        voltage_max=int(agg.voltage_max),
                        voltage_avg=int(agg.voltage_avg),
                        current_min=int(agg.current_min_amps),
                        current_max=int(agg.current_max_amps),
                        current_avg=int(agg.current_avg_amps),
                        energy=int(event.energy_wh),
                        true_power_inst=int(agg.true_power_inst_watts),
                        true_power_avg=int(agg.true_power_avg_watts),
                        apparent_power_avg=int(agg.apparent_power_avg_va),
                        power_factor_avg=int(agg.power_factor_avg),
                        user_power_limit=int(event.user_power_limit_watts),
                    )
                else:
                    reading_data = dict(
                        meter=int(event.meter_id),
                        state=event.state.value if event.state else "unknown",
                        uptime=int(event.uptime_seconds),
                        heartbeat_start=heartbeat_start,
                        heartbeat_end=heartbeat_end,
                        frequency=int(event.frequency_hz),
                        voltage_min=int(event.voltage_min),
                        voltage_max=int(event.voltage_max),
                        voltage_avg=int(event.voltage_avg),
                        current_min=int(event.current_min_amps),
                        current_max=int(event.current_max_amps),
                        current_avg=int(event.current_avg_amps),
                        energy=int(event.energy_wh),
                        true_power_inst=int(event.true_power_inst_watts),
                        true_power_avg=int(event.true_power_avg_watts),
                        apparent_power_avg=int(event.apparent_power_avg_va),
                        power_factor_avg=int(event.power_factor_avg),
                        user_power_limit=int(event.user_power_limit_watts),
                    )
                try:
                    add_reading(reading_data)
                except DatabaseLockTimeoutException:
                    logger.error(
                        "discarding reading from meter %s: db lock timeout",
                        event.meter_id,
                    )
                    current_app.sentry.captureException(
                        message=f"Meter {event.meter_id} reading lock timeout",
                        tags={"action": "reading"},
                    )
                except DuplicateReadingException:
                    logger.warning("discarding duplicate reading from meter %s", event.meter_id)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "failed to write reading for meter_id=%s",
                    getattr(event, "meter_id", "?"),
                )


def build_log_consumer(app: "FastAPI") -> "EventHandler":
    """Forwards `LogEvent` into the Python logging system."""

    level_map = {
        LogLevel.TRACE: logging.DEBUG,
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARN: logging.WARNING,
        LogLevel.ERROR: logging.ERROR,
    }
    provider_logger = logging.getLogger("sparkmeter.metering.provider")

    async def consumer(event: Any) -> None:
        if not isinstance(event, LogEvent):
            return
        provider_logger.log(level_map.get(event.level, logging.INFO), event.message)

    return consumer


def build_watchdog(app: "FastAPI") -> "EventHandler":
    """Observe heartbeat summaries; log persistent dropouts.

    The webapp no longer owns the provider process; the watchdog only
    logs. Tunables:
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

    state = {"consecutive_dropouts": 0, "warned": False}

    async def watchdog(event: Any) -> None:
        if not isinstance(event, HeartbeatSummaryEvent):
            return

        if event.total_registered_meters < min_nodes_for_check:
            state["consecutive_dropouts"] = 0
            state["warned"] = False
            return

        all_dropped = event.meters_attempted > 0 and event.meters_responded == 0
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
