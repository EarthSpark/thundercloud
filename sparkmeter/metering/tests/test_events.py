"""Tests for the SSE event handler / typed-event dispatcher."""

import logging

import pytest

from sparkmeter.metering import events
from sparkmeter.metering._generated.models.heartbeat_summary_event import HeartbeatSummaryEvent
from sparkmeter.metering._generated.models.log_event import LogEvent
from sparkmeter.metering._generated.models.log_level import LogLevel
from sparkmeter.metering._generated.models.meter_reading_event import MeterReadingEvent
from sparkmeter.metering._generated.models.meter_state import MeterState

# ---------------------------------------------------------------------------
# dispatch_dict_event — structures raw dicts into typed events
# ---------------------------------------------------------------------------


class TestDispatchDictEvent:
    @pytest.mark.asyncio
    async def test_meter_reading_routes_to_handler(self):
        captured: list = []

        async def capture(event):
            captured.append(event)

        raw = {
            "event_type": "meter_reading",
            "event_id": 42,
            "meter_id": "100",
            "period_start": 1700000000,
            "period_end": 1700000900,
            "state": "on",
            "uptime_seconds": 12345,
            "frequency_hz": 50.0,
            "voltage_min": 220.0,
            "voltage_avg": 230.5,
            "voltage_max": 235.0,
            "current_min_amps": 1.0,
            "current_avg_amps": 5.0,
            "current_max_amps": 10.0,
            "true_power_avg_watts": 1000.0,
            "true_power_inst_watts": 1100.0,
            "apparent_power_avg_va": 1200.0,
            "power_factor_avg": 0.95,
            "energy_wh": 1234.5,
            "user_power_limit_watts": 1500.0,
        }
        await events.dispatch_dict_event(raw, [capture])

        assert len(captured) == 1
        event = captured[0]
        assert isinstance(event, MeterReadingEvent)
        assert event.meter_id == "100"
        assert event.state is MeterState.ON
        assert event.energy_wh == pytest.approx(1234.5)

    @pytest.mark.asyncio
    async def test_unknown_event_type_logged_and_skipped(self, caplog):
        captured: list = []

        async def capture(event):
            captured.append(event)

        with caplog.at_level(logging.WARNING):
            await events.dispatch_dict_event({"event_type": "wat", "event_id": 1}, [capture])

        assert captured == []
        assert any("unknown event_type" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_missing_event_type_skipped(self, caplog):
        captured: list = []

        async def capture(event):
            captured.append(event)

        with caplog.at_level(logging.WARNING):
            await events.dispatch_dict_event({"event_id": 1}, [capture])

        assert captured == []

    @pytest.mark.asyncio
    async def test_handler_exception_is_isolated(self, caplog):
        captured: list = []

        async def failing(event):
            raise RuntimeError("boom")

        async def capture(event):
            captured.append(event)

        raw = {
            "event_type": "log",
            "event_id": 1,
            "level": "info",
            "message": "hi",
        }
        with caplog.at_level(logging.ERROR):
            await events.dispatch_dict_event(raw, [failing, capture])

        # Second handler still runs.
        assert len(captured) == 1
        assert isinstance(captured[0], LogEvent)


# ---------------------------------------------------------------------------
# Reading consumer batching
# ---------------------------------------------------------------------------


class TestReadingConsumer:
    @pytest.mark.asyncio
    async def test_buffers_until_batch_full(self, monkeypatch):
        """Below the batch size, no flush happens."""
        flushed: list = []

        async def fake_flush(batch):
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        consumer = events.build_reading_consumer(app=None)

        for i in range(events.READING_BATCH_SIZE - 1):
            await consumer(
                MeterReadingEvent(
                    event_id=i,
                    event_type="meter_reading",
                    meter_id=str(i),
                    period_start=1,
                    period_end=2,
                    state=MeterState.ON,
                    uptime_seconds=0,
                    frequency_hz=50.0,
                    voltage_min=0.0,
                    voltage_avg=0.0,
                    voltage_max=0.0,
                    current_min_amps=0.0,
                    current_avg_amps=0.0,
                    current_max_amps=0.0,
                    true_power_avg_watts=0.0,
                    true_power_inst_watts=0.0,
                    apparent_power_avg_va=0.0,
                    power_factor_avg=0.0,
                    energy_wh=0.0,
                    user_power_limit_watts=0.0,
                )
            )
        assert flushed == []

    @pytest.mark.asyncio
    async def test_flushes_on_batch_full(self, monkeypatch):
        flushed: list = []

        async def fake_flush(batch):
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        consumer = events.build_reading_consumer(app=None)

        for i in range(events.READING_BATCH_SIZE):
            await consumer(
                MeterReadingEvent(
                    event_id=i,
                    event_type="meter_reading",
                    meter_id=str(i),
                    period_start=1,
                    period_end=2,
                    state=MeterState.ON,
                    uptime_seconds=0,
                    frequency_hz=50.0,
                    voltage_min=0.0,
                    voltage_avg=0.0,
                    voltage_max=0.0,
                    current_min_amps=0.0,
                    current_avg_amps=0.0,
                    current_max_amps=0.0,
                    true_power_avg_watts=0.0,
                    true_power_inst_watts=0.0,
                    apparent_power_avg_va=0.0,
                    power_factor_avg=0.0,
                    energy_wh=0.0,
                    user_power_limit_watts=0.0,
                )
            )
        assert len(flushed) == 1
        assert len(flushed[0]) == events.READING_BATCH_SIZE

    @pytest.mark.asyncio
    async def test_non_reading_events_ignored(self, monkeypatch):
        flushed: list = []

        async def fake_flush(batch):
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        consumer = events.build_reading_consumer(app=None)

        await consumer(LogEvent(event_id=1, event_type="log", level=LogLevel.INFO, message="hi"))
        assert flushed == []


# ---------------------------------------------------------------------------
# Log consumer
# ---------------------------------------------------------------------------


class TestLogConsumer:
    @pytest.mark.asyncio
    async def test_log_event_forwards_to_logger(self, caplog):
        consumer = events.build_log_consumer(app=None)
        with caplog.at_level(logging.WARNING, logger="sparkmeter.metering.provider"):
            await consumer(LogEvent(event_id=1, event_type="log", level=LogLevel.WARN, message="hello"))
        assert any(rec.message == "hello" for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_non_log_event_ignored(self, caplog):
        consumer = events.build_log_consumer(app=None)
        with caplog.at_level(logging.DEBUG, logger="sparkmeter.metering.provider"):
            await consumer(
                MeterReadingEvent(
                    event_id=1,
                    event_type="meter_reading",
                    meter_id="x",
                    period_start=1,
                    period_end=2,
                    state=MeterState.ON,
                    uptime_seconds=0,
                    frequency_hz=50.0,
                    voltage_min=0.0,
                    voltage_avg=0.0,
                    voltage_max=0.0,
                    current_min_amps=0.0,
                    current_avg_amps=0.0,
                    current_max_amps=0.0,
                    true_power_avg_watts=0.0,
                    true_power_inst_watts=0.0,
                    apparent_power_avg_va=0.0,
                    power_factor_avg=0.0,
                    energy_wh=0.0,
                    user_power_limit_watts=0.0,
                )
            )
        # No record from the metering.provider logger.
        provider_records = [r for r in caplog.records if r.name == "sparkmeter.metering.provider"]
        assert provider_records == []


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------


def _heartbeat(total: int, attempted: int, responded: int) -> HeartbeatSummaryEvent:
    return HeartbeatSummaryEvent(
        event_id=1,
        event_type="heartbeat_summary",
        timestamp=1700000000,
        total_registered_meters=total,
        meters_attempted=attempted,
        meters_responded=responded,
        packets_sent=attempted,
        packets_received=responded,
    )


class TestWatchdog:
    @pytest.mark.asyncio
    async def test_below_threshold_does_not_warn(self, monkeypatch, caplog):
        monkeypatch.setenv("METERING_WATCHDOG_MIN_NODES", "10")
        monkeypatch.setenv("METERING_WATCHDOG_MAX_DROPOUTS", "3")
        watchdog = events.build_watchdog(app=None)
        with caplog.at_level(logging.WARNING):
            for _ in range(5):
                await watchdog(_heartbeat(total=5, attempted=5, responded=0))
        assert not any("dropout heartbeats" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_warns_after_consecutive_dropouts(self, monkeypatch, caplog):
        monkeypatch.setenv("METERING_WATCHDOG_MIN_NODES", "10")
        monkeypatch.setenv("METERING_WATCHDOG_MAX_DROPOUTS", "3")
        watchdog = events.build_watchdog(app=None)
        with caplog.at_level(logging.WARNING):
            for _ in range(3):
                await watchdog(_heartbeat(total=20, attempted=20, responded=0))
        assert sum(1 for r in caplog.records if "dropout heartbeats" in r.message) == 1

    @pytest.mark.asyncio
    async def test_resets_on_recovery(self, monkeypatch, caplog):
        monkeypatch.setenv("METERING_WATCHDOG_MIN_NODES", "10")
        monkeypatch.setenv("METERING_WATCHDOG_MAX_DROPOUTS", "3")
        watchdog = events.build_watchdog(app=None)
        with caplog.at_level(logging.WARNING):
            for _ in range(2):
                await watchdog(_heartbeat(total=20, attempted=20, responded=0))
            # Recovery resets the counter.
            await watchdog(_heartbeat(total=20, attempted=20, responded=15))
            await watchdog(_heartbeat(total=20, attempted=20, responded=0))
            await watchdog(_heartbeat(total=20, attempted=20, responded=0))
        # Two dropouts before reset, then two more — still below threshold.
        assert not any("dropout heartbeats" in r.message for r in caplog.records)
