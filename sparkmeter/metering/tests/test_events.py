"""Tests for the SSE envelope dispatcher and reading handlers."""

import asyncio
import contextlib
import logging
from types import SimpleNamespace

import pytest
from meter_driver_spec.http.models import (
    ElectricalMeterReading,
    HeartbeatStatistics,
)

from sparkmeter.exceptions import DatabaseLockTimeoutException, DuplicateReadingException
from sparkmeter.metering import events

# ---------------------------------------------------------------------------
# Helpers building valid generated-model payloads
# ---------------------------------------------------------------------------


def _reading_data(**overrides):
    """A full `electrical_meter_reading` "data" payload (spec field names)."""
    data = dict(
        node_id=100,
        period_start=1700000000,
        period_end=1700000900,
        state=1,  # ElectricalMeterState id for "on"
        frequency=50.0,
        current_avg=5.0,
        current_min=1.0,
        current_max=10.0,
        voltage_avg=230.5,
        voltage_min=220.0,
        voltage_max=235.0,
        true_power_avg=1000.0,
        true_power_inst=1100.0,
        apparent_power_avg=1200.0,
        power_factor_avg=0.95,
        energy=1234.5,
        uptime_secs=12345,
        user_power_limit=1500.0,
    )
    data.update(overrides)
    return data


def _reading(**overrides):
    return ElectricalMeterReading.model_validate(_reading_data(**overrides))


def _stats():
    return {"count": 1, "last_value": 10.0, "max": 10.0, "min": 10.0, "avg": 10.0}


def _heartbeat_data(total, attempted, responded):
    return dict(
        timestamp=1700000000,
        total_registered_nodes=total,
        total_packets_sent=attempted,
        total_packets_received=responded,
        nodes_reached_out_to_in_current_heartbeat=attempted,
        nodes_heard_from_in_current_heartbeat=responded,
        packets_sent_in_current_heartbeat=attempted,
        packets_received_in_current_heartbeat=responded,
        millisecond_read_reply_stats=_stats(),
        millisecond_set_config_reply_stats=_stats(),
    )


def _heartbeat(total, attempted, responded):
    return HeartbeatStatistics.model_validate(_heartbeat_data(total, attempted, responded))


# ---------------------------------------------------------------------------
# dispatch_dict_event — parses SSE envelopes into generated models
# ---------------------------------------------------------------------------


class TestDispatchDictEvent:
    @pytest.mark.asyncio
    async def test_meter_reading_routes_to_handler(self):
        captured: list = []

        async def capture(event):
            captured.append(event)

        raw = {"type": "electrical_meter_reading", "data": _reading_data()}
        await events.dispatch_dict_event(raw, [capture])

        assert len(captured) == 1
        event = captured[0]
        assert isinstance(event, ElectricalMeterReading)
        assert event.node_id == 100
        assert event.state.value == 1
        assert event.energy == pytest.approx(1234.5)

    @pytest.mark.asyncio
    async def test_unknown_type_logged_and_skipped(self, caplog):
        captured: list = []

        async def capture(event):
            captured.append(event)

        with caplog.at_level(logging.WARNING):
            await events.dispatch_dict_event({"type": "wat", "data": {}}, [capture])

        assert captured == []
        assert any("unknown type" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_missing_type_skipped(self, caplog):
        captured: list = []

        async def capture(event):
            captured.append(event)

        with caplog.at_level(logging.WARNING):
            await events.dispatch_dict_event({"data": {}}, [capture])

        assert captured == []
        assert any("missing type" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_side_channel_logged_and_skipped(self, caplog):
        captured: list = []

        async def capture(event):
            captured.append(event)

        with caplog.at_level(logging.DEBUG):
            await events.dispatch_dict_event({"type": "node_registered", "data": {"node_id": 1}}, [capture])

        assert captured == []
        assert any("side-channel" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_heartbeat_statistics_parsed(self):
        captured: list = []

        async def capture(event):
            captured.append(event)

        raw = {"type": "heartbeat_statistics", "data": _heartbeat_data(1, 1, 1)}
        await events.dispatch_dict_event(raw, [capture])

        assert len(captured) == 1
        event = captured[0]
        assert isinstance(event, HeartbeatStatistics)
        assert event.total_registered_nodes == 1
        assert event.nodes_reached_out_to_in_current_heartbeat == 1
        assert event.nodes_heard_from_in_current_heartbeat == 1

    @pytest.mark.asyncio
    async def test_heartbeat_read_hops_flushes_pending_readings(self, monkeypatch):
        flushed: list = []

        async def fake_flush(batch, flask_app):
            del flask_app
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        consumer = events.build_reading_consumer(app=None)

        await consumer(_reading(period_start=1, period_end=2))
        await events.dispatch_dict_event(
            {"type": "heartbeat_read_hops", "data": {}},
            [consumer],
        )

        assert len(flushed) == 1
        assert len(flushed[0]) == 1

    @pytest.mark.asyncio
    async def test_handler_exception_is_isolated(self, caplog):
        captured: list = []

        async def failing(event):
            raise RuntimeError("boom")

        async def capture(event):
            captured.append(event)

        raw = {"type": "electrical_meter_reading", "data": _reading_data()}
        with caplog.at_level(logging.ERROR):
            await events.dispatch_dict_event(raw, [failing, capture])

        # Second handler still runs.
        assert len(captured) == 1
        assert isinstance(captured[0], ElectricalMeterReading)


# ---------------------------------------------------------------------------
# Reading consumer batching
# ---------------------------------------------------------------------------


class TestReadingConsumer:
    @pytest.mark.asyncio
    async def test_buffers_until_batch_full(self, monkeypatch):
        """Below the batch size, no flush happens."""
        flushed: list = []

        async def fake_flush(batch, flask_app):
            del flask_app
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        consumer = events.build_reading_consumer(app=None)

        for i in range(events.READING_BATCH_SIZE - 1):
            await consumer(_reading(node_id=i))
        assert flushed == []

    @pytest.mark.asyncio
    async def test_flushes_on_batch_full(self, monkeypatch):
        flushed: list = []

        async def fake_flush(batch, flask_app):
            del flask_app
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        consumer = events.build_reading_consumer(app=None)

        for i in range(events.READING_BATCH_SIZE):
            await consumer(_reading(node_id=i))
        assert len(flushed) == 1
        assert len(flushed[0]) == events.READING_BATCH_SIZE

    @pytest.mark.asyncio
    async def test_non_reading_events_ignored(self, monkeypatch):
        flushed: list = []

        async def fake_flush(batch, flask_app):
            del flask_app
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        consumer = events.build_reading_consumer(app=None)

        await consumer(object())
        assert flushed == []

    @pytest.mark.asyncio
    async def test_flushes_partial_batch_on_heartbeat(self, monkeypatch):
        flushed: list = []

        async def fake_flush(batch, flask_app):
            del flask_app
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        consumer = events.build_reading_consumer(app=None)

        await consumer(_reading(node_id=1))
        await consumer(_heartbeat(1, 1, 1))

        assert len(flushed) == 1
        assert len(flushed[0]) == 1

    @pytest.mark.asyncio
    async def test_flushes_partial_batch_on_timer(self, monkeypatch):
        flushed: list = []

        async def fake_flush(batch, flask_app):
            del flask_app
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        monkeypatch.setattr(events, "READING_FLUSH_INTERVAL_SECONDS", 0)
        consumer = events.build_reading_consumer(app=None)

        await consumer(_reading(node_id=1))

        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert len(flushed) == 1
        assert len(flushed[0]) == 1


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------


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

    @pytest.mark.asyncio
    async def test_zero_roster_after_registered_meter_requests_restart(self, monkeypatch, caplog):
        monkeypatch.setenv("METERING_WATCHDOG_MIN_NODES", "10")
        gateway_state = {"needs_full_restart": False}
        app = SimpleNamespace(state=SimpleNamespace(metering_gateway_state=gateway_state))
        watchdog = events.build_watchdog(app=app)

        with caplog.at_level(logging.WARNING):
            await watchdog(_heartbeat(total=1, attempted=1, responded=1))
            await watchdog(_heartbeat(total=0, attempted=0, responded=0))

        assert gateway_state["needs_full_restart"] is True
        assert any("provider roster dropped to zero" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# dispatch_dict_event — parse failures and info-level side channels
# ---------------------------------------------------------------------------


class TestDispatchParseFailures:
    @pytest.mark.asyncio
    async def test_unparseable_reading_is_logged_and_dropped(self, caplog):
        captured: list = []

        async def capture(event):
            captured.append(event)

        with caplog.at_level(logging.ERROR):
            await events.dispatch_dict_event(
                {"type": "electrical_meter_reading", "data": {"unexpected": "shape"}},
                [capture],
            )

        assert captured == []
        assert any("failed to parse" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_unparseable_heartbeat_is_logged_and_dropped(self, caplog):
        captured: list = []

        async def capture(event):
            captured.append(event)

        with caplog.at_level(logging.ERROR):
            await events.dispatch_dict_event(
                {"type": "heartbeat_statistics", "data": {"unexpected": "shape"}},
                [capture],
            )

        assert captured == []
        assert any("heartbeat failed to parse" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_info_side_channel_logged_at_info(self, caplog):
        with caplog.at_level(logging.INFO):
            await events.dispatch_dict_event(
                {"type": "electrical_meter_configuration_accepted", "data": {}}, []
            )

        info_records = [rec for rec in caplog.records if rec.levelno == logging.INFO]
        assert any("side-channel" in rec.message for rec in info_records)


# ---------------------------------------------------------------------------
# Flush lifecycle edge cases and DB writeback
# ---------------------------------------------------------------------------


class _FakeSentry:
    def __init__(self):
        self.captured: list = []

    def captureException(self, message=None, tags=None):
        self.captured.append((message, tags))


class _FakeFlaskApp:
    def __init__(self):
        self.sentry = _FakeSentry()

    def app_context(self):
        return contextlib.nullcontext()


class TestFlushLifecycle:
    @pytest.mark.asyncio
    async def test_heartbeat_with_no_pending_readings_does_not_flush(self, monkeypatch):
        flushed: list = []

        async def fake_flush(batch, flask_app):
            del flask_app
            flushed.append(list(batch))

        monkeypatch.setattr(events, "_flush_readings", fake_flush)
        consumer = events.build_reading_consumer(app=None)

        # No reading has been buffered, so the heartbeat's cancel+flush is a no-op.
        await consumer(_heartbeat(1, 1, 1))

        assert flushed == []

    @pytest.mark.asyncio
    async def test_flush_readings_tolerates_missing_flask_app(self, caplog):
        # _write_readings_sync raises without a Flask app; _flush_readings swallows it.
        with caplog.at_level(logging.ERROR):
            await events._flush_readings([_reading()], None)

        assert any("flush failed" in rec.message for rec in caplog.records)


class TestWriteReadingsSync:
    def test_persists_valid_reading(self, monkeypatch):
        calls: list = []

        def fake_add_reading(reading_data, update_meter_state=False):
            calls.append((reading_data, update_meter_state))

        monkeypatch.setattr("sparkmeter.controller.add_reading", fake_add_reading)

        events._write_readings_sync([_reading(node_id=100, energy=1234.5)], _FakeFlaskApp())

        assert len(calls) == 1
        reading_data, update_meter_state = calls[0]
        assert update_meter_state is False
        assert reading_data["meter"] == 100
        # The spec state id (1) is translated to its MeterState name, not passed through.
        assert reading_data["state"] == "on"
        assert reading_data["uptime"] == 12345
        # Both period timestamps are converted; end - start is the 900s window.
        assert (reading_data["heartbeat_end"] - reading_data["heartbeat_start"]).total_seconds() == 900
        # Every electrical field maps to its own slot — distinct values catch a swap.
        assert reading_data["frequency"] == pytest.approx(50.0)
        assert reading_data["voltage_min"] == pytest.approx(220.0)
        assert reading_data["voltage_max"] == pytest.approx(235.0)
        assert reading_data["voltage_avg"] == pytest.approx(230.5)
        assert reading_data["current_min"] == pytest.approx(1.0)
        assert reading_data["current_max"] == pytest.approx(10.0)
        assert reading_data["current_avg"] == pytest.approx(5.0)
        assert reading_data["true_power_inst"] == pytest.approx(1100.0)
        assert reading_data["true_power_avg"] == pytest.approx(1000.0)
        assert reading_data["apparent_power_avg"] == pytest.approx(1200.0)
        assert reading_data["power_factor_avg"] == pytest.approx(0.95)
        assert reading_data["energy"] == pytest.approx(1234.5)
        assert reading_data["user_power_limit"] == pytest.approx(1500.0)

    def test_lock_timeout_is_reported_to_sentry(self, monkeypatch):
        def fake_add_reading(reading_data, update_meter_state=False):
            raise DatabaseLockTimeoutException("locked")

        monkeypatch.setattr("sparkmeter.controller.add_reading", fake_add_reading)
        flask_app = _FakeFlaskApp()

        events._write_readings_sync([_reading(node_id=77)], flask_app)

        assert flask_app.sentry.captured
        message, tags = flask_app.sentry.captured[0]
        assert message == "Meter 77 reading lock timeout"
        assert tags == {"action": "reading"}

    def test_duplicate_reading_is_skipped(self, monkeypatch, caplog):
        def fake_add_reading(reading_data, update_meter_state=False):
            raise DuplicateReadingException("dupe")

        monkeypatch.setattr("sparkmeter.controller.add_reading", fake_add_reading)

        with caplog.at_level(logging.WARNING):
            events._write_readings_sync([_reading(node_id=88)], _FakeFlaskApp())

        assert any("duplicate reading" in rec.message for rec in caplog.records)

    def test_incomplete_heartbeat_window_is_discarded(self, monkeypatch, caplog):
        calls = []

        def fake_add_reading(reading_data, update_meter_state=False):
            calls.append(reading_data)

        monkeypatch.setattr("sparkmeter.controller.add_reading", fake_add_reading)

        # A falsy period_start means the heartbeat window is incomplete, so the
        # reading is dropped before it ever reaches add_reading.
        with caplog.at_level(logging.WARNING):
            events._write_readings_sync([_reading(node_id=55, period_start=0)], _FakeFlaskApp())

        assert calls == []
        assert any("incomplete heartbeat window" in rec.message for rec in caplog.records)
