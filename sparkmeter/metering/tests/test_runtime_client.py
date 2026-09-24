"""Tests for metering runtime transport helpers."""

from types import SimpleNamespace

import pytest
from meter_driver_spec.grpc import meter_driver_pb2 as pb2
from meter_driver_spec.http.models import (
    ConfigureElectricalMeterCompatRequest,
    ElectricalMeterCommandName,
    ElectricalMeterConfiguration,
    GatewayStatus,
    HeartbeatStatistics,
    RegisterNodeRequest,
    SetBalanceAndFlagsRequest,
)

from sparkmeter.metering import runtime_client


def test_grpc_target_falls_back_to_saved_target():
    provider = {
        "base_url": "http://127.0.0.1:18080",
        "selected_interface_target": "127.0.0.1:50051",
    }

    assert runtime_client._grpc_target(provider, provider_details=None) == "127.0.0.1:50051"


def test_grpc_target_prefers_advertised_interface_details():
    provider = {"base_url": "http://127.0.0.1:18080", "selected_interface_target": "stale:1"}
    details = {"selected_interface_details": {"type": "grpc", "target": "h:50051"}}

    assert runtime_client._grpc_target(provider, provider_details=details) == "h:50051"


def test_grpc_target_is_none_when_no_grpc_interface_is_advertised():
    # The spec fixes no gRPC port, so nothing is derived from the HTTP host.
    provider = {
        "base_url": "http://127.0.0.1:18080",
        "selected_interface_target": "",
    }

    assert runtime_client._grpc_target(provider, provider_details=None) is None
    assert runtime_client._grpc_target(provider, provider_details={"selected_interface_details": {}}) is None


@pytest.mark.asyncio
async def test_http_event_client_delegates_to_shared_sse_helper(monkeypatch):
    captured = {}

    async def fake_stream_json_events(base_url, client_id):
        captured["base_url"] = base_url
        captured["client_id"] = client_id
        yield {"type": "gateway_status"}

    monkeypatch.setattr(runtime_client, "stream_json_events", fake_stream_json_events)

    client = runtime_client.HttpEventClient("http://127.0.0.1:18080/", "saved-client")
    events = [event async for event in client.stream_events("")]

    assert events == [{"type": "gateway_status"}]
    assert captured == {
        "base_url": "http://127.0.0.1:18080",
        "client_id": "saved-client",
    }


@pytest.mark.asyncio
async def test_http_event_client_close_is_noop():
    client = runtime_client.HttpEventClient("http://127.0.0.1:18080", "cid")
    assert await client.close() is None


# ---------------------------------------------------------------------------
# Pure value helpers
# ---------------------------------------------------------------------------


def test_to_spec_decimal_defaults_invalid_to_zero():
    result = runtime_client.to_spec_decimal("not-a-number")
    assert result.model_dump() == {"sign": 1, "coef": 0, "exp": 0}


def test_to_spec_decimal_negative_sets_sign():
    assert runtime_client.to_spec_decimal("-12.5").model_dump() == {
        "sign": -1,
        "coef": 125,
        "exp": -1,
    }


def test_aes_key_bytes_accepts_hex_bytes_and_iterables():
    assert runtime_client._aes_key_bytes("00ff10") == b"\x00\xff\x10"
    assert runtime_client._aes_key_bytes(b"\x01\x02") == b"\x01\x02"
    assert runtime_client._aes_key_bytes(bytearray(b"\x03")) == b"\x03"
    assert runtime_client._aes_key_bytes([1, 2, 3]) == b"\x01\x02\x03"


def test_version_dict_defaults_missing_components():
    assert runtime_client._version_dict(SimpleNamespace(major=1, minor=2, patch=3)) == {
        "major": 1,
        "minor": 2,
        "patch": 3,
    }
    assert runtime_client._version_dict(SimpleNamespace()) == {"major": 0, "minor": 0, "patch": 0}


# The per-phase measurements of ElectricalMeterReadingPhased (spec section 6).
_AGG_PHASE_FIELDS = (
    "apparent_power_avg",
    "current_avg",
    "current_max",
    "current_min",
    "frequency",
    "power_factor_avg",
    "true_power_avg",
    "true_power_inst",
    "voltage_avg",
    "voltage_max",
    "voltage_min",
)


def test_selected_interface_details_prefers_provider_details():
    details = {"selected_interface_details": {"type": "grpc", "target": "h:1"}}
    assert runtime_client._selected_interface_details({}, details) == {"type": "grpc", "target": "h:1"}
    assert runtime_client._selected_interface_details({}, None) == {}


# ---------------------------------------------------------------------------
# Command client base + HTTP transport
# ---------------------------------------------------------------------------


class _FakeHttpResponse:
    def raise_for_status(self):
        return None


class _FakeHttpxClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.calls: list = []

    async def post(self, path, json=None):
        self.calls.append(("POST", path, json))
        return _FakeHttpResponse()

    async def delete(self, path):
        self.calls.append(("DELETE", path, None))
        return _FakeHttpResponse()

    async def aclose(self):
        self.calls.append(("CLOSE", None, None))


@pytest.mark.asyncio
async def test_base_command_client_methods_are_abstract():
    client = runtime_client.MeteringCommandClient()
    with pytest.raises(NotImplementedError):
        await client.init_driver({})
    with pytest.raises(NotImplementedError):
        await client.register_node(RegisterNodeRequest(node_id=1, node_type="SM5R"))
    with pytest.raises(NotImplementedError):
        await client.configure_meter(_configure_request_model())
    with pytest.raises(NotImplementedError):
        await client.set_balance(1, _balance_request_model())
    with pytest.raises(NotImplementedError):
        await client.unregister_node(1)
    with pytest.raises(NotImplementedError):
        await client.close()


def _configure_request_model():
    return ConfigureElectricalMeterCompatRequest(
        node_id=42,
        command=ElectricalMeterCommandName.ELECTRICALMETERCOMMANDENABLE,
        configuration=ElectricalMeterConfiguration(
            power_limit=1500.0,
            current_limit=10.0,
            startup_delay=0,
            throttle_on_time=5,
            throttle_off_time=10,
            throttle_count_limit=5,
        ),
    )


def _balance_request_model():
    return SetBalanceAndFlagsRequest(balance=runtime_client.to_spec_decimal("12.5"), low_balance_flag=True)


class TestHttpCommandClient:
    @pytest.mark.asyncio
    async def test_all_endpoints_and_close(self, monkeypatch):
        monkeypatch.setattr(runtime_client.httpx, "AsyncClient", _FakeHttpxClient)
        client = runtime_client.HttpCommandClient("http://driver:18080/", "cid")

        await client.init_driver({"heartbeat_period_duration": 60})
        await client.register_node(RegisterNodeRequest(node_id=7, node_type="SM5R"))
        await client.configure_meter(_configure_request_model())
        await client.set_balance(7, _balance_request_model())
        await client.unregister_node(7)
        await client.close()

        calls = client._client.calls
        methods_and_paths = [(method, path) for method, path, _ in calls]
        assert methods_and_paths == [
            ("POST", "/v1/init"),
            ("POST", "/v1/nodes/register"),
            ("POST", "/v1/meters/configure"),
            ("POST", "/v1/nodes/7/balance-and-flags"),
            ("DELETE", "/v1/nodes/7"),
            ("CLOSE", None),
        ]

        # The serialized request bodies, not just routing, must be correct.
        assert calls[0][2] == {"heartbeat_period_duration": 60}
        register_body = calls[1][2]
        assert register_body["node_id"] == 7
        assert register_body["node_type"] == "SM5R"
        assert "mac" not in register_body  # exclude_none drops the unset mac
        assert calls[2][2]["node_id"] == 42  # configure body carries node_id
        assert calls[3][2]["low_balance_flag"] is True  # balance body


# ---------------------------------------------------------------------------
# gRPC transport construction / event client stream
# ---------------------------------------------------------------------------


class _FakeChannel:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class _RecordingStub:
    def __init__(self, channel):
        self.channel = channel
        self.calls: dict = {}

    def _record(self, name, request):
        self.calls.setdefault(name, []).append(request)

    async def InitDriver(self, request):
        self._record("InitDriver", request)

    async def RegisterNode(self, request):
        self._record("RegisterNode", request)

    async def ConfigureElectricalMeter(self, request):
        self._record("ConfigureElectricalMeter", request)

    async def SetElectricalMeterBalanceAndFlags(self, request):
        self._record("SetElectricalMeterBalanceAndFlags", request)

    async def UnregisterNode(self, request):
        self._record("UnregisterNode", request)


def _patch_grpc(monkeypatch, stub_factory):
    channel = _FakeChannel()
    monkeypatch.setattr(runtime_client.grpc.aio, "insecure_channel", lambda target: channel)
    monkeypatch.setattr(runtime_client.pb2_grpc, "MeterDriverControlStub", stub_factory)
    return channel


class TestGrpcCommandClient:
    def _client_with_stub(self, monkeypatch):
        holder = {}

        def factory(channel):
            holder["stub"] = _RecordingStub(channel)
            return holder["stub"]

        channel = _patch_grpc(monkeypatch, factory)
        client = runtime_client.GrpcCommandClient("host:50051")
        return client, holder, channel

    @pytest.mark.asyncio
    async def test_init_driver_marshals_payload(self, monkeypatch):
        client, holder, channel = self._client_with_stub(monkeypatch)

        await client.init_driver({"heartbeat_period_duration": 60, "aes_key": "00" * 16, "channel": 26})

        request = holder["stub"].calls["InitDriver"][0]
        assert request.heartbeat_period_duration == 60
        assert request.aes_key == bytes.fromhex("00" * 16)
        assert request.channel.value == 26

        await client.close()
        assert channel.closed is True

    @pytest.mark.asyncio
    async def test_init_driver_omits_channel_when_absent(self, monkeypatch):
        client, holder, _ = self._client_with_stub(monkeypatch)

        await client.init_driver({"heartbeat_period_duration": 60, "aes_key": "00" * 16})

        request = holder["stub"].calls["InitDriver"][0]
        assert request.HasField("channel") is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "payload, missing",
        [
            ({"aes_key": "00" * 16}, "heartbeat_period_duration"),
            ({"heartbeat_period_duration": 60}, "aes_key"),
            ({"heartbeat_period_duration": 60, "aes_key": ""}, "aes_key"),
        ],
    )
    async def test_init_driver_names_the_fixed_fields_it_is_missing(self, monkeypatch, payload, missing):
        # ConfigureDriver has fixed proto fields; a driver whose /v1/requirements
        # omitted one cannot be initialized over gRPC, and the error says which.
        client, holder, _ = self._client_with_stub(monkeypatch)

        with pytest.raises(ValueError) as exc:
            await client.init_driver(payload)

        assert "gRPC ConfigureDriver requires" in str(exc.value)
        assert missing in str(exc.value)
        assert "InitDriver" not in holder["stub"].calls

    @pytest.mark.asyncio
    async def test_command_methods_delegate_to_stub(self, monkeypatch):
        client, holder, _ = self._client_with_stub(monkeypatch)

        await client.register_node(RegisterNodeRequest(node_id=100, node_type="SM5R"))
        await client.configure_meter(_configure_request_model())
        await client.set_balance(7, _balance_request_model())
        await client.unregister_node(55)

        stub = holder["stub"]
        assert stub.calls["RegisterNode"][0].node_id == 100
        assert stub.calls["ConfigureElectricalMeter"][0].node_id == 42
        assert stub.calls["SetElectricalMeterBalanceAndFlags"][0].node_id == 7
        assert stub.calls["UnregisterNode"][0].node_id == 55


class TestGrpcEventClientStream:
    @pytest.mark.asyncio
    async def test_stream_translates_and_skips_none(self, monkeypatch):
        class _StreamStub:
            def __init__(self, channel):
                self.channel = channel

            def SubscribeEvents(self, request):
                async def _gen():
                    yield SimpleNamespace(tag="a")
                    yield SimpleNamespace(tag="skip")
                    yield SimpleNamespace(tag="b")

                return _gen()

        _patch_grpc(monkeypatch, _StreamStub)

        def fake_translate(event, event_id):
            if event.tag == "skip":
                return None
            return {"tag": event.tag, "event_id": event_id}

        monkeypatch.setattr(runtime_client, "_grpc_event_to_raw_dict", fake_translate)

        client = runtime_client.GrpcEventClient("host:50051")
        events = [event async for event in client.stream_events("ignored")]

        # The "skip" event (translated to None) is dropped; ids increment per event.
        assert events == [{"tag": "a", "event_id": 1}, {"tag": "b", "event_id": 3}]

    @pytest.mark.asyncio
    async def test_close_closes_channel(self, monkeypatch):
        channel = _patch_grpc(monkeypatch, _RecordingStub)
        client = runtime_client.GrpcEventClient("host:50051")
        await client.close()
        assert channel.closed is True


# ---------------------------------------------------------------------------
# Transport selection + provider initialization
# ---------------------------------------------------------------------------


class TestBuildClients:
    def test_build_command_client_uses_grpc_when_target_available(self, monkeypatch):
        _patch_grpc(monkeypatch, _RecordingStub)
        provider = {
            "selected_interface": "grpc",
            "selected_interface_target": "host:50051",
            "base_url": "http://driver:18080",
        }
        client = runtime_client.build_command_client(provider, "cid")
        assert isinstance(client, runtime_client.GrpcCommandClient)

    def test_build_command_client_uses_advertised_grpc_target(self, monkeypatch):
        holder = {}

        def factory(channel):
            holder["stub"] = _RecordingStub(channel)
            return holder["stub"]

        targets = []
        monkeypatch.setattr(
            runtime_client.grpc.aio, "insecure_channel", lambda target: targets.append(target)
        )
        monkeypatch.setattr(runtime_client.pb2_grpc, "MeterDriverControlStub", factory)
        provider = {"selected_interface": "grpc", "base_url": "http://driver:18080"}
        details = {"selected_interface_details": {"type": "grpc", "target": "h:50051"}}

        client = runtime_client.build_command_client(provider, "cid", provider_details=details)

        assert isinstance(client, runtime_client.GrpcCommandClient)
        assert targets == ["h:50051"]

    def test_build_command_client_errors_when_grpc_selected_without_target(self):
        # gRPC selected but the contract advertises no grpc interface: no
        # derived host:50051 and no silent HTTP fallback.
        provider = {"selected_interface": "grpc", "base_url": "http://driver:18080"}
        with pytest.raises(runtime_client.GrpcTargetUnavailable) as exc:
            runtime_client.build_command_client(provider, "cid")
        assert "advertises no grpc interface target" in str(exc.value)

    def test_build_command_client_defaults_to_http(self):
        provider = {"base_url": "http://driver:18080"}
        client = runtime_client.build_command_client(provider, "cid")
        assert isinstance(client, runtime_client.HttpCommandClient)

    def test_build_event_client_uses_grpc_when_target_available(self, monkeypatch):
        _patch_grpc(monkeypatch, _RecordingStub)
        provider = {
            "selected_interface": "grpc",
            "selected_interface_target": "host:50051",
            "base_url": "http://driver:18080",
        }
        client = runtime_client.build_event_client(provider, "cid")
        assert isinstance(client, runtime_client.GrpcEventClient)

    def test_build_event_client_errors_when_grpc_selected_without_target(self):
        provider = {"selected_interface": "grpc", "base_url": "http://driver:18080"}
        with pytest.raises(runtime_client.GrpcTargetUnavailable):
            runtime_client.build_event_client(provider, "cid")

    def test_build_event_client_defaults_to_http(self):
        provider = {"base_url": "http://driver:18080"}
        client = runtime_client.build_event_client(provider, "cid")
        assert isinstance(client, runtime_client.HttpEventClient)


class _RecordingCommandClient:
    def __init__(self):
        self.inited: list = []
        self.closed = False

    async def init_driver(self, payload):
        self.inited.append(payload)

    async def close(self):
        self.closed = True


class TestInitializeProvider:
    @pytest.mark.asyncio
    async def test_initialize_provider_inits_then_closes(self, monkeypatch):
        client = _RecordingCommandClient()
        monkeypatch.setattr(runtime_client, "build_command_client", lambda *a, **k: client)
        await runtime_client.initialize_provider({"base_url": "http://x"}, {"aes_key": "00"})
        assert client.inited == [{"aes_key": "00"}]
        assert client.closed is True

    @pytest.mark.asyncio
    async def test_initialize_provider_closes_even_on_error(self, monkeypatch):
        class _BoomClient(_RecordingCommandClient):
            async def init_driver(self, payload):
                raise RuntimeError("init failed")

        client = _BoomClient()
        monkeypatch.setattr(runtime_client, "build_command_client", lambda *a, **k: client)
        with pytest.raises(RuntimeError):
            await runtime_client.initialize_provider({"base_url": "http://x"}, {})
        assert client.closed is True

    def test_initialize_provider_sync_runs_event_loop(self, monkeypatch):
        client = _RecordingCommandClient()
        monkeypatch.setattr(runtime_client, "build_command_client", lambda *a, **k: client)
        runtime_client.initialize_provider_sync({"base_url": "http://x"}, {"aes_key": "00"})
        assert client.inited == [{"aes_key": "00"}]
        assert client.closed is True


# ---------------------------------------------------------------------------
# Protobuf request builders
# ---------------------------------------------------------------------------


class TestProtoRequestBuilders:
    def test_register_request_sets_optional_fields(self):
        req = RegisterNodeRequest(node_id=100, node_type="SM5R", mac=0xABCD, request_phased_readings=True)
        proto = runtime_client._register_request(req)
        assert proto.node_id == 100
        assert proto.mac.value == 0xABCD
        assert proto.request_phased_readings.value is True

    def test_register_request_without_optional_fields(self):
        req = RegisterNodeRequest(node_id=100, node_type="SM5R")
        proto = runtime_client._register_request(req)
        assert proto.node_id == 100
        # mac left unset when not provided.
        assert proto.mac.value == 0

    def test_configure_request_maps_command_and_configuration(self):
        proto = runtime_client._configure_request(_configure_request_model())
        assert proto.node_id == 42
        assert proto.configuration.power_limit == pytest.approx(1500.0)
        assert proto.configuration.throttle_count_limit == 5

    def test_set_balance_request_builds_decimal(self):
        proto = runtime_client._set_balance_request(7, _balance_request_model())
        assert proto.node_id == 7
        assert proto.low_balance_flag is True
        assert proto.balance.coef == 125
        assert proto.balance.exp == -1


# ---------------------------------------------------------------------------
# gRPC event translation
# ---------------------------------------------------------------------------


def _event(name, message):
    return SimpleNamespace(WhichOneof=lambda field: name, **{name: message})


def _reading_message():
    on_value = getattr(runtime_client.pb2.ElectricalMeterState, "ElectricalMeterStateOn", 1)
    return SimpleNamespace(
        node_id=100,
        period_start=1700000000,
        period_end=1700000900,
        state=on_value,
        frequency=50.0,
        current_avg=5.0,
        current_min=1.0,
        current_max=10.0,
        voltage_avg=230.0,
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


def _phased_message():
    on_value = getattr(runtime_client.pb2.ElectricalMeterState, "ElectricalMeterStateOn", 1)
    fields = {name: 1.0 for name in _AGG_PHASE_FIELDS}
    # A distinct value per phase so a phase swap in the translation shows.
    fields.update({"{}_a".format(name): 2.0 for name in _AGG_PHASE_FIELDS})
    fields.update({"{}_b".format(name): 3.0 for name in _AGG_PHASE_FIELDS})
    fields.update({"{}_c".format(name): 0.0 for name in _AGG_PHASE_FIELDS})
    fields.update(
        node_id=100,
        period_start=1,
        period_end=2,
        state=on_value,
        energy=10.0,
        uptime_secs=5,
        user_power_limit=1500.0,
        computed_fields_version=3,
        phases=SimpleNamespace(a=True, b=True, c=False),
    )
    return SimpleNamespace(**fields)


class TestGrpcEventToRawDict:
    """The translation yields only what an SSE frame carries: type, event_id, data."""

    def test_no_oneof_returns_none(self):
        event = SimpleNamespace(WhichOneof=lambda field: None)
        assert runtime_client._grpc_event_to_raw_dict(event, 1) is None

    def test_unsupported_event_returns_none(self, monkeypatch):
        monkeypatch.setattr(runtime_client, "MessageToDict", lambda message, **kwargs: {})
        event = _event("some_future_event", SimpleNamespace())
        assert runtime_client._grpc_event_to_raw_dict(event, 1) is None

    def test_reading_event_translated(self, monkeypatch):
        monkeypatch.setattr(runtime_client, "MessageToDict", lambda message, **kwargs: {})
        raw = runtime_client._grpc_event_to_raw_dict(
            _event("electrical_meter_reading", _reading_message()), 5
        )
        on_value = getattr(runtime_client.pb2.ElectricalMeterState, "ElectricalMeterStateOn", 1)
        # Exactly the envelope keys: no renamed convenience copies of the data.
        assert set(raw) == {"type", "event_id", "data"}
        assert raw["type"] == "electrical_meter_reading"
        assert raw["event_id"] == 5
        # The "data" block carries the spec field names and values in full; a
        # swap inside it (e.g. current_min/current_max) would change one of
        # these, and the exact-dict compare also catches drift.
        assert raw["data"] == pytest.approx(
            {
                "node_id": 100,
                "period_start": 1700000000,
                "period_end": 1700000900,
                "state": on_value,
                "frequency": 50.0,
                "current_avg": 5.0,
                "current_min": 1.0,
                "current_max": 10.0,
                "voltage_avg": 230.0,
                "voltage_min": 220.0,
                "voltage_max": 235.0,
                "true_power_avg": 1000.0,
                "true_power_inst": 1100.0,
                "apparent_power_avg": 1200.0,
                "power_factor_avg": 0.95,
                "energy": 1234.5,
                "uptime_secs": 12345,
                "user_power_limit": 1500.0,
            }
        )

    def test_reading_data_parses_as_the_spec_model(self):
        from meter_driver_spec.http.models import ElectricalMeterReading

        raw = runtime_client._grpc_event_to_raw_dict(
            _event("electrical_meter_reading", _reading_message()), 5
        )
        event = ElectricalMeterReading.model_validate(raw["data"])
        assert event.node_id == 100
        assert event.state.value == 1

    def test_phased_reading_event_translated(self):
        from meter_driver_spec.http.models import ElectricalMeterReadingPhased

        raw = runtime_client._grpc_event_to_raw_dict(
            _event("electrical_meter_reading_phased", _phased_message()), 6
        )
        assert set(raw) == {"type", "event_id", "data"}
        assert raw["type"] == "electrical_meter_reading_phased"
        data = raw["data"]
        assert data["phases"] == {"a": True, "b": True, "c": False}
        assert data["computed_fields_version"] == 3
        assert data["current_avg_a"] == pytest.approx(2.0)
        assert data["current_avg_b"] == pytest.approx(3.0)
        assert data["current_avg_c"] == pytest.approx(0.0)
        assert data["current_avg"] == pytest.approx(1.0)
        # Every aggregate and per-phase field the spec payload has is present.
        event = ElectricalMeterReadingPhased.model_validate(data)
        assert event.voltage_min_b == pytest.approx(3.0)
        assert event.phases.b is True

    def test_heartbeat_event_renders_a_real_message_as_the_spec_payload(self):
        stats = pb2.Statistics(count=3, last_value=1.5, max=2.0, min=1.0, avg=1.5)
        event = pb2.MeterDriverEvent(
            heartbeat_statistics=pb2.HeartbeatStatistics(
                timestamp=1700000000,
                total_registered_nodes=20,
                millisecond_read_reply_stats=stats,
                millisecond_set_config_reply_stats=stats,
            )
        )
        raw = runtime_client._grpc_event_to_raw_dict(event, 7)
        assert raw["type"] == "heartbeat_statistics"
        assert raw["event_id"] == 7
        # Spec field names, and zero-valued counters kept (the model requires them).
        heartbeat = HeartbeatStatistics.model_validate(raw["data"])
        assert heartbeat.total_registered_nodes == 20
        assert heartbeat.total_packets_sent == 0
        assert heartbeat.millisecond_read_reply_stats.count == 3
        assert heartbeat.millisecond_set_config_reply_stats.avg == pytest.approx(1.5)

    def test_heartbeat_event_renders_unset_stats_as_zeroed_statistics(self):
        # A driver that never sets the two stats submessages still produces a
        # payload the spec model accepts, so the reading flush marker is not lost.
        event = pb2.MeterDriverEvent(heartbeat_statistics=pb2.HeartbeatStatistics(timestamp=1700000000))
        data = runtime_client._grpc_event_to_raw_dict(event, 7)["data"]
        zeroed = {"count": 0, "last_value": 0.0, "max": 0.0, "min": 0.0, "avg": 0.0}
        assert data["millisecond_read_reply_stats"] == zeroed
        assert data["millisecond_set_config_reply_stats"] == zeroed
        HeartbeatStatistics.model_validate(data)

    def test_gateway_status_event_renders_an_unset_firmware_version(self):
        event = pb2.MeterDriverEvent(
            gateway_status=pb2.GatewayStatusEvent(connected=True, gateway_type="usb")
        )
        data = runtime_client._grpc_event_to_raw_dict(event, 9)["data"]
        assert data["firmware_version"] == {"major": 0, "minor": 0, "patch": 0}
        assert GatewayStatus.model_validate(data).connected is True

    def test_firmware_change_event_translated(self):
        message = SimpleNamespace(node_id=100, firmware_version=SimpleNamespace(major=1, minor=2, patch=3))
        raw = runtime_client._grpc_event_to_raw_dict(_event("node_firmware_version_changed", message), 8)
        assert raw == {
            "type": "node_firmware_version_changed",
            "event_id": 8,
            "data": {"node_id": 100, "firmware_version": {"major": 1, "minor": 2, "patch": 3}},
        }

    def test_side_channel_event_passes_through_message_dict(self):
        event = pb2.MeterDriverEvent(gateway_status=pb2.GatewayStatusEvent(connected=True))
        raw = runtime_client._grpc_event_to_raw_dict(event, 9)
        assert set(raw) == {"type", "event_id", "data"}
        assert raw["type"] == "gateway_status"
        assert raw["event_id"] == 9
        assert raw["data"]["connected"] is True

    def test_side_channel_node_id_is_restored_to_an_integer(self):
        # The protobuf JSON mapping renders uint64 as a string; the spec payload wants an integer.
        event = pb2.MeterDriverEvent(node_registered=pb2.NodeRegistered(node_id=63519))
        raw = runtime_client._grpc_event_to_raw_dict(event, 10)
        assert raw["data"]["node_id"] == 63519
