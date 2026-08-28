"""Tests for the reconcile command builders and worker-thread entry points.

The pure-functional command builders below are what most of the
reconcile correctness depends on.

The DB-loading paths (`_load_driver_init_payload`, `_load_meters`) run in
worker threads via `asyncio.to_thread` from the FastAPI lifespan, where
Flask's `current_app` is unavailable. They are tested with `app` fixture
calls that intentionally invoke them from a fresh thread.
"""

import threading
from types import SimpleNamespace

import pytest
from meter_driver_spec.http.models import (
    ConfigureElectricalMeterCompatRequest,
    ElectricalMeterCommandName,
    RegisterNodeRequest,
    SetBalanceAndFlagsRequest,
)

from sparkmeter.config import provider_settings
from sparkmeter.meter.meterdomain import MeterConfig
from sparkmeter.metering import reconcile


def _raise(*args, **kwargs):
    raise RuntimeError("derivation boom")


class TestBuildRegister:
    def test_with_mac(self):
        body = reconcile._build_register({"meter_id": "100", "meter_type": "SM5R", "mac": 0xABCD})
        assert isinstance(body, RegisterNodeRequest)
        assert body.node_id == 100
        assert body.node_type == "SM5R"
        assert body.mac == 0xABCD

    def test_without_mac(self):
        body = reconcile._build_register({"meter_id": "100", "meter_type": "SM5R"})
        assert body.mac is None

    def test_unknown_meter_type_passes_through(self):
        # Type validation happens upstream in `_resolve_meter_type`.
        body = reconcile._build_register({"meter_id": "100", "meter_type": "WIBBLE"})
        assert body.node_type == "WIBBLE"


class TestBuildConfigure:
    def test_config_behavior_takes_precedence(self):
        body = reconcile._build_configure(
            {
                "meter_id": "42",
                "is_active": False,
                "config": {
                    "behavior": "enable",
                    "power_limit": 1500,
                    "current_limit": 10,
                    "startup_delay": 2,
                    "throttle_on_time": 5,
                    "throttle_off_time": 10,
                    "throttle_count_limit": 5,
                },
            }
        )
        assert isinstance(body, ConfigureElectricalMeterCompatRequest)
        assert body.command is ElectricalMeterCommandName.ELECTRICALMETERCOMMANDENABLE

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
        assert body.command is ElectricalMeterCommandName.ELECTRICALMETERCOMMANDENABLE
        assert body.configuration.power_limit == pytest.approx(1500.0)

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
        assert body.command is ElectricalMeterCommandName.ELECTRICALMETERCOMMANDDISABLE

    def test_no_config_returns_none(self):
        assert reconcile._build_configure({"meter_id": "42", "is_active": True}) is None

    def test_unmappable_behavior_returns_none(self, monkeypatch):
        # If the behavior verb has no spec command, no configure is emitted.
        monkeypatch.setattr(reconcile, "behavior_to_command", lambda behavior: None)
        assert reconcile._build_configure({"meter_id": "42", "is_active": True, "config": {}}) is None


class TestBuildBalance:
    def test_with_balance(self):
        body = reconcile._build_balance({"meter_id": "9", "balance": 12.5, "low_balance": True})
        assert isinstance(body, SetBalanceAndFlagsRequest)
        assert body.balance.model_dump() == {"sign": 1, "coef": 125, "exp": -1}
        assert body.low_balance_flag is True

    def test_no_balance_returns_none(self):
        assert reconcile._build_balance({"meter_id": "9"}) is None

    def test_decimal_preserves_precision(self):
        body = reconcile._build_balance({"meter_id": "9", "balance": "0.00001", "low_balance": False})
        assert body is not None
        assert body.balance.model_dump() == {"sign": 1, "coef": 1, "exp": -5}


class TestResolveMeterType:
    class _MockModel:
        def __init__(self, name):
            self.name = name

    class _MockMeter:
        def __init__(self, model_name=None):
            self.model = TestResolveMeterType._MockModel(model_name) if model_name else None

    def test_known_type_uppercase(self):
        assert reconcile._resolve_meter_type(self._MockMeter("SM5R")) == "SM5R"

    def test_lowercase_normalizes(self):
        assert reconcile._resolve_meter_type(self._MockMeter("smhce")) == "SMHCE"

    def test_unknown_falls_back_to_sm5r(self):
        assert reconcile._resolve_meter_type(self._MockMeter("WIBBLE")) == "SM5R"

    def test_no_model_falls_back_to_sm5r(self):
        assert reconcile._resolve_meter_type(self._MockMeter(None)) == "SM5R"


# ----------------------------------------------------------------------
# Regression: worker-thread entry points must not rely on Flask's
# `current_app` proxy. The reconcile loaders are invoked from the
# FastAPI lifespan via `asyncio.to_thread`, which spawns a fresh OS
# thread that has no Flask app context.
# ----------------------------------------------------------------------


def _run_in_fresh_thread(fn, *args):
    """Invoke `fn(*args)` on a fresh `threading.Thread`, re-raising errors."""
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
    def test_load_meters_runs_in_thread_without_outer_context(self, app, session):
        rows = _run_in_fresh_thread(reconcile._load_meters, app)
        assert isinstance(rows, list)

    def test_load_meters_maps_meter_row_shape(self, app, session):
        from sparkmeter.tests.test_data_factory import MeterFactory

        meter = MeterFactory()
        session.commit()

        rows = _run_in_fresh_thread(reconcile._load_meters, app)

        assert len(rows) == 1
        row = rows[0]
        assert set(row) == {
            "meter_id",
            "meter_type",
            "mac",
            "balance",
            "low_balance",
            "config",
            "is_active",
        }
        # meter_id and mac are derived from the meter's code.
        assert row["meter_id"] == str(meter.code)
        assert row["mac"] == int(meter.code)

    def test_load_meters_signature_takes_flask_app(self):
        with pytest.raises(TypeError):
            reconcile._load_meters()  # type: ignore[call-arg]

    def test_load_driver_init_payload_reads_driver_fields(self, app, session, monkeypatch):
        monkeypatch.setattr(
            provider_settings,
            "get_enabled_provider",
            lambda: {"base_url": "http://127.0.0.1:18080", "selected_interface": "http"},
        )
        monkeypatch.setattr(
            provider_settings,
            "load_provider_runtime_settings",
            lambda provider: {
                "field_values": {
                    "aes_key": "00112233445566778899AABBCCDDEEFF",
                    "channel": "26",
                    "heartbeat_period_duration": "60",
                }
            },
        )

        payload = _run_in_fresh_thread(reconcile._load_driver_init_payload, app)

        assert payload == {
            "aes_key": "00112233445566778899AABBCCDDEEFF",
            "channel": 26,
            "heartbeat_period_duration": 60,
        }

    def test_load_driver_init_payload_skips_invalid_aes_key(self, app, session, monkeypatch):
        monkeypatch.setattr(
            provider_settings,
            "get_enabled_provider",
            lambda: {"base_url": "http://127.0.0.1:18080", "selected_interface": "http"},
        )
        monkeypatch.setattr(
            provider_settings,
            "load_provider_runtime_settings",
            lambda provider: {
                "field_values": {
                    "aes_key": "not-hex",
                    "channel": "12",
                    "heartbeat_period_duration": "60",
                }
            },
        )

        payload = _run_in_fresh_thread(reconcile._load_driver_init_payload, app)

        assert payload is None

    def test_load_driver_init_payload_requires_heartbeat(self, app, session, monkeypatch):
        monkeypatch.setattr(
            provider_settings, "get_enabled_provider", lambda: {"base_url": "http://127.0.0.1:18080"}
        )
        monkeypatch.setattr(
            provider_settings,
            "load_provider_runtime_settings",
            lambda provider: {"field_values": {"aes_key": "00112233445566778899AABBCCDDEEFF"}},
        )

        # No heartbeat period means there is nothing to init the driver with.
        assert _run_in_fresh_thread(reconcile._load_driver_init_payload, app) is None

    def test_load_driver_init_payload_skips_invalid_channel(self, app, session, monkeypatch):
        monkeypatch.setattr(
            provider_settings, "get_enabled_provider", lambda: {"base_url": "http://127.0.0.1:18080"}
        )
        monkeypatch.setattr(
            provider_settings,
            "load_provider_runtime_settings",
            lambda provider: {
                "field_values": {
                    "aes_key": "00112233445566778899AABBCCDDEEFF",
                    "channel": "not-an-int",
                    "heartbeat_period_duration": "60",
                }
            },
        )

        payload = _run_in_fresh_thread(reconcile._load_driver_init_payload, app)

        # The bad channel is dropped; the rest of the payload still comes through.
        assert payload == {
            "aes_key": "00112233445566778899AABBCCDDEEFF",
            "heartbeat_period_duration": 60,
        }

    def test_load_driver_init_payload_requires_aes_key(self, app, session, monkeypatch):
        monkeypatch.setattr(
            provider_settings, "get_enabled_provider", lambda: {"base_url": "http://127.0.0.1:18080"}
        )
        monkeypatch.setattr(
            provider_settings,
            "load_provider_runtime_settings",
            lambda provider: {"field_values": {"heartbeat_period_duration": "60"}},
        )

        # No AES key means there is nothing to initialize the driver with.
        assert _run_in_fresh_thread(reconcile._load_driver_init_payload, app) is None


class _RecordingClient:
    """Metering client double that records every reconcile command."""

    def __init__(self):
        self.inits: list = []
        self.registered: list = []
        self.configured: list = []
        self.balances: list = []

    async def init_driver(self, payload):
        self.inits.append(payload)

    async def register_node(self, req):
        self.registered.append(req)

    async def configure_meter(self, req):
        self.configured.append(req)

    async def set_balance(self, node_id, req):
        self.balances.append((node_id, req))

    async def unregister_node(self, node_id):
        pass


class TestReconcileAllLoop:
    @pytest.mark.asyncio
    async def test_registers_configures_and_sets_balance(self, monkeypatch):
        meters = [
            {
                "meter_id": "1",
                "meter_type": "SM5R",
                "mac": 1,
                "is_active": True,
                "config": {
                    "behavior": "enable",
                    "power_limit": 1500,
                    "current_limit": 10,
                    "startup_delay": 0,
                    "throttle_on_time": 5,
                    "throttle_off_time": 10,
                    "throttle_count_limit": 5,
                },
                "balance": 12.5,
                "low_balance": True,
            },
            {
                "meter_id": "2",
                "meter_type": "SM5R",
                "mac": 2,
                "is_active": True,
                "config": None,
                "balance": None,
                "low_balance": False,
            },
        ]
        monkeypatch.setattr(reconcile, "_load_driver_init_payload", lambda flask_app: None)
        monkeypatch.setattr(reconcile, "_load_meters", lambda flask_app: meters)

        client = _RecordingClient()
        await reconcile.reconcile_all(client, object())

        # Both meters registered; only the one with config/balance drove those calls.
        assert [req.node_id for req in client.registered] == [1, 2]
        assert [req.node_id for req in client.configured] == [1]
        assert [node_id for node_id, _ in client.balances] == [1]

    @pytest.mark.asyncio
    async def test_meter_failure_is_isolated(self, monkeypatch):
        meters = [
            {"meter_id": "1", "meter_type": "SM5R", "mac": 1, "is_active": True, "config": None},
            {"meter_id": "2", "meter_type": "SM5R", "mac": 2, "is_active": True, "config": None},
        ]

        class _FlakyClient(_RecordingClient):
            async def register_node(self, req):
                if req.node_id == 1:
                    raise RuntimeError("provider down")
                self.registered.append(req)

        monkeypatch.setattr(reconcile, "_load_driver_init_payload", lambda flask_app: None)
        monkeypatch.setattr(reconcile, "_load_meters", lambda flask_app: meters)

        client = _FlakyClient()
        # A failure on meter 1 must not stop meter 2 from being reconciled.
        await reconcile.reconcile_all(client, object())

        assert [req.node_id for req in client.registered] == [2]


class TestConfigOf:
    def _customer_meter(self):
        cfg = SimpleNamespace(
            startup_delay=3, throttle_on_time=6, throttle_off_time=11, throttle_count_limit=4
        )
        meter = SimpleNamespace(
            code=42,
            config=cfg,
            continuous_current_limit=10.0,
            provider_id=None,
            state_value=MeterConfig.STATE_ON,
            model=SimpleNamespace(inrush_limit=100.0, name="SM5R"),
            scalars=SimpleNamespace(power_scalar=2.0, current_scalar=2.0),
            tariff=SimpleNamespace(get_current_load_limit=lambda: 5000.0),
            ground=SimpleNamespace(private=SimpleNamespace(override_meter_state=False)),
        )
        meter.is_customer_meter = lambda: True
        return meter

    def test_derives_customer_meter_config(self, session):
        from sparkmeter.config.configparameter import parameters

        result = reconcile._config_of(self._customer_meter())
        assert result["behavior"] == "enable"

        # power_limit = min(continuous_current_limit * nominal_voltage, tariff
        # load limit) / power_scalar. With continuous_current_limit=10.0,
        # tariff=5000, power_scalar=2.0 and no provider_id (engineering units off).
        nominal_voltage = parameters.NOMINAL_VOLTAGE
        expected_power = min(10.0 * nominal_voltage, 5000.0) / 2.0
        assert result["power_limit"] == pytest.approx(expected_power)
        # current_limit = min(inrush_limit / current_scalar, 65535) = 100/2 = 50.
        assert result["current_limit"] == pytest.approx(50.0)
        assert result["startup_delay"] == 3
        assert result["throttle_count_limit"] == 4

    def test_no_config_returns_none(self, session):
        meter = self._customer_meter()
        meter.config = None
        assert reconcile._config_of(meter) is None

    def test_non_customer_meter_returns_none(self, session):
        meter = self._customer_meter()
        meter.is_customer_meter = lambda: False
        assert reconcile._config_of(meter) is None

    def test_derivation_error_returns_none(self, session):
        meter = self._customer_meter()
        meter.tariff = SimpleNamespace(get_current_load_limit=_raise)
        assert reconcile._config_of(meter) is None

    def test_engineering_units_skip_scalar_division(self, session):
        # A provider_id marks the meter as reporting in engineering units, so
        # limits are not divided by the meter's scalars.
        scalar_meter = self._customer_meter()
        eng_meter = self._customer_meter()
        eng_meter.provider_id = "provider-1"

        scalar_result = reconcile._config_of(scalar_meter)
        eng_result = reconcile._config_of(eng_meter)

        # Same inputs but scalar=2.0 division only applies without a provider_id,
        # so the engineering-units current limit is the larger (undivided) value.
        assert eng_result["current_limit"] > scalar_result["current_limit"]

    def test_override_meter_state_forces_disable(self, session):
        meter = self._customer_meter()
        meter.ground = SimpleNamespace(private=SimpleNamespace(override_meter_state=True))
        # STATE_ON but overridden → the derived behavior is "disable".
        assert reconcile._config_of(meter)["behavior"] == "disable"

    def test_config_import_failure_returns_none(self, session, monkeypatch):
        import sys

        # Force the deferred config imports inside _config_of to fail so the
        # ImportError guard returns None rather than deriving a config.
        monkeypatch.setitem(sys.modules, "sparkmeter.config.configparameter", None)
        assert reconcile._config_of(self._customer_meter()) is None


class TestReconcileProviderInit:
    class _Client:
        def __init__(self):
            self.inits: list = []

        async def init_driver(self, payload):
            self.inits.append(payload)

        async def register_node(self, req):
            raise AssertionError("no meters in this test")

        async def configure_meter(self, req):
            raise AssertionError("no meters in this test")

        async def set_balance(self, node_id, req):
            raise AssertionError("no meters in this test")

        async def unregister_node(self, node_id):
            raise AssertionError("no meters in this test")

    @pytest.mark.asyncio
    async def test_reconcile_calls_provider_init_by_default(self, monkeypatch):
        payload = {"aes_key": "00" * 16, "channel": 26, "heartbeat_period_duration": 60}
        monkeypatch.setattr(reconcile, "_load_driver_init_payload", lambda flask_app: payload)
        monkeypatch.setattr(reconcile, "_load_meters", lambda flask_app: [])
        client = self._Client()
        await reconcile.reconcile_all(client, object())
        assert client.inits == [payload]

    @pytest.mark.asyncio
    async def test_reconcile_can_skip_provider_init(self, monkeypatch):
        payload = {"aes_key": "00" * 16, "channel": 26, "heartbeat_period_duration": 60}
        monkeypatch.setattr(reconcile, "_load_driver_init_payload", lambda flask_app: payload)
        monkeypatch.setattr(reconcile, "_load_meters", lambda flask_app: [])
        client = self._Client()
        await reconcile.reconcile_all(client, object(), skip_provider_init=True)
        assert client.inits == []
