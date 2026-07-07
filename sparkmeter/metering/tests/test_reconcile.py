"""Tests for the reconcile command builders and worker-thread entry points.

The pure-functional command builders below are what most of the
reconcile correctness depends on.

The DB-loading paths (`_load_provider_command`, `_load_meters`) run in
worker threads via `asyncio.to_thread` from the FastAPI lifespan, where
Flask's `current_app` is unavailable. They are tested with `app` fixture
calls that intentionally invoke them from a fresh thread.
"""

import threading

import pytest

from sparkmeter.metering import reconcile
from sparkmeter.metering._generated.models.meter_behavior_command import MeterBehaviorCommand
from sparkmeter.metering._generated.models.submit_command_v_1_commands_post_request_body_command_type_enum import \
    SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum as CommandTypeEnum


class TestBuildRegister:
    def test_with_mac(self):
        body = reconcile._build_register(
            {"meter_id": "100", "meter_type": "SM5R", "mac": 0xABCD}
        )
        assert body.command_type is CommandTypeEnum.REGISTER_METER
        assert body.params.meter_id == "100"
        assert body.params.meter_type == "SM5R"
        assert body.vendor_options is not None
        assert body.vendor_options["mac"] == 0xABCD

    def test_without_mac_omits_vendor_options(self):
        body = reconcile._build_register({"meter_id": "100", "meter_type": "SM5R"})
        assert body.vendor_options is None

    def test_unknown_meter_type_falls_back(self):
        body = reconcile._build_register({"meter_id": "100", "meter_type": "WIBBLE"})
        # The dict already has the type; reconcile passes it through.
        # Type validation only happens in `_resolve_meter_type` upstream.
        assert body.params.meter_type == "WIBBLE"


class TestBuildConfigure:
    def test_active_meter_emits_enable(self):
        body = reconcile._build_configure(
            {
                "meter_id": "42",
                "is_active": True,
                "config": {
                    "power_limit": 1500,
                    "current_limit": 10,
                    "startup_delay": 2,
                    "throttle_on_time": 5,
                    "throttle_off_time": 10,
                    "throttle_count_limit": 5,
                },
            }
        )
        assert body is not None
        assert body.command_type is CommandTypeEnum.CONFIGURE_METER
        assert body.params.behavior is MeterBehaviorCommand.ENABLE
        assert body.params.configuration.power_limit_watts == pytest.approx(1500.0)

    def test_inactive_meter_emits_disable(self):
        body = reconcile._build_configure(
            {
                "meter_id": "42",
                "is_active": False,
                "config": {
                    "power_limit": 1500,
                    "current_limit": 10,
                    "startup_delay": 0,
                    "throttle_on_time": 5,
                    "throttle_off_time": 10,
                    "throttle_count_limit": 5,
                },
            }
        )
        assert body is not None
        assert body.params.behavior is MeterBehaviorCommand.DISABLE

    def test_no_config_returns_none(self):
        assert reconcile._build_configure({"meter_id": "42", "is_active": True}) is None


class TestBuildBalance:
    def test_with_balance(self):
        body = reconcile._build_balance(
            {"meter_id": "9", "balance": 12.5, "low_balance": True}
        )
        assert body is not None
        assert body.command_type is CommandTypeEnum.SET_BALANCE
        assert body.params.meter_id == "9"
        assert body.params.balance == "12.5"
        assert body.params.low_balance is True

    def test_no_balance_returns_none(self):
        assert reconcile._build_balance({"meter_id": "9"}) is None

    def test_decimal_string_preserves_precision(self):
        body = reconcile._build_balance(
            {"meter_id": "9", "balance": "0.00001", "low_balance": False}
        )
        assert body is not None
        assert body.params.balance == "0.00001"


class TestResolveMeterType:
    class _MockModel:
        def __init__(self, name):
            self.name = name

    class _MockMeter:
        def __init__(self, model_name=None):
            self.model = TestResolveMeterType._MockModel(model_name) if model_name else None

    def test_known_type_uppercase(self):
        meter = self._MockMeter("SM5R")
        assert reconcile._resolve_meter_type(meter) == "SM5R"

    def test_lowercase_normalizes(self):
        meter = self._MockMeter("smhce")
        assert reconcile._resolve_meter_type(meter) == "SMHCE"

    def test_unknown_falls_back_to_sm5r(self):
        meter = self._MockMeter("WIBBLE")
        assert reconcile._resolve_meter_type(meter) == "SM5R"

    def test_no_model_falls_back_to_sm5r(self):
        meter = self._MockMeter(None)
        assert reconcile._resolve_meter_type(meter) == "SM5R"


# ----------------------------------------------------------------------
# Regression: worker-thread entry points must not rely on Flask's
# `current_app` proxy. The reconcile loaders are invoked from the
# FastAPI lifespan via `asyncio.to_thread`, which spawns a fresh OS
# thread that has no Flask app context.
# ----------------------------------------------------------------------


def _run_in_fresh_thread(fn, *args):
    """Invoke `fn(*args)` on a fresh `threading.Thread` and return its
    result, re-raising any exception. The fresh thread has no Flask
    context — this is what `asyncio.to_thread` does inside FastAPI's
    lifespan.
    """
    container: dict = {}

    def _target():
        try:
            container["result"] = fn(*args)
        except BaseException as exc:  # noqa: BLE001
            container["error"] = exc

    t = threading.Thread(target=_target)
    t.start()
    t.join()
    if "error" in container:
        raise container["error"]
    return container["result"]


class TestWorkerThreadEntryPoints:
    """Guard the contract that reconcile loaders accept an explicit
    Flask app and push their own context on the worker thread.

    Against the pre-fix code (`_load_meters()` with no arg, body using
    `current_app.app_context()`), the calls below would raise
    `RuntimeError: Working outside of application context` from the
    worker thread.
    """

    def test_load_meters_runs_in_thread_without_outer_context(self, app, session):
        rows = _run_in_fresh_thread(reconcile._load_meters, app)
        assert isinstance(rows, list)

    def test_load_provider_command_runs_in_thread_without_outer_context(self, app, session, config):
        # `_load_provider_command` reads `HEARTBEAT_PERIOD`; without it
        # the function returns None. Either return value is acceptable
        # — the test asserts no exception escapes the worker thread.
        result = _run_in_fresh_thread(reconcile._load_provider_command, app)
        assert result is None or hasattr(result, "params")

    def test_load_meters_signature_takes_flask_app(self):
        """Calling `_load_meters` with no arg must fail loudly. The
        no-arg form was the original (broken) signature; allowing it
        again would reintroduce the bug.
        """
        with pytest.raises(TypeError):
            reconcile._load_meters()  # type: ignore[call-arg]
