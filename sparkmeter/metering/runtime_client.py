"""Transport adapters for metering command and event traffic.

Generic HTTP+SSE and gRPC clients built directly against the Thunder-Cloud
2.0 Open Source Meter Driver Specification — not against any vendor's
package. Any driver that implements the spec's required HTTP+SSE contract
works here with zero vendor-specific code. A driver that additionally
implements the optional gRPC profile works over gRPC too, through the
stubs the `meter-driver-spec` wheel compiles from the spec's own
meter_driver.proto (`meter_driver_spec.grpc`).

No driver gets special treatment here: SparkNet-Http is one compliant
driver instance among however many a deployment configures. Nothing in
this module imports a vendor-published client package.
"""

from __future__ import annotations

import asyncio
import binascii
import logging
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

import grpc
import httpx
from google.protobuf.json_format import MessageToDict
from google.protobuf.wrappers_pb2 import BoolValue, UInt32Value
from meter_driver_spec.grpc import meter_driver_pb2 as pb2
from meter_driver_spec.grpc import meter_driver_pb2_grpc as pb2_grpc
from meter_driver_spec.http.models import (
    ConfigureElectricalMeterCompatRequest,
    ElectricalMeterCommandName,
    RegisterNodeRequest,
    SetBalanceAndFlagsRequest,
)
from meter_driver_spec.http.models import (
    Decimal as SpecDecimal,
)

from sparkmeter.metering.http_sse import stream_json_events

logger = logging.getLogger(__name__)

# The gRPC profile's ConfigureDriver message has fixed fields (spec section 7,
# meter_driver.proto), so the gRPC init path needs these two whatever the
# driver advertised on /v1/requirements. The HTTP path has no such list: it
# posts exactly the discovered fields.
_GRPC_INIT_REQUIRED_FIELDS = ("heartbeat_period_duration", "aes_key")


class GrpcTargetUnavailable(ValueError):
    """gRPC was selected for a driver whose contract advertises no grpc target."""


# Lowercase behavior verb -> the spec's ElectricalMeterCommandName. Verbs with
# no spec command ("none", "enter_unprovisioned") return None; callers skip
# building a configure command for those rather than guess a wire value.
_BEHAVIOR_TO_COMMAND = {
    "enable": ElectricalMeterCommandName.ELECTRICALMETERCOMMANDENABLE,
    "disable": ElectricalMeterCommandName.ELECTRICALMETERCOMMANDDISABLE,
    "reboot": ElectricalMeterCommandName.ELECTRICALMETERCOMMANDREBOOT,
    "calibrate_start": ElectricalMeterCommandName.ELECTRICALMETERCOMMANDCALIBRATESTART,
    "calibrate_finish": ElectricalMeterCommandName.ELECTRICALMETERCOMMANDCALIBRATEFINISH,
}


def behavior_to_command(behavior: str | None) -> ElectricalMeterCommandName | None:
    """Map a lowercase behavior verb to a spec ElectricalMeterCommandName (or None)."""
    return _BEHAVIOR_TO_COMMAND.get((behavior or "").lower().strip())


def to_spec_decimal(value: Any) -> SpecDecimal:
    """Decompose a numeric/str value into the spec's {sign, coef, exp} Decimal."""
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        decimal_value = Decimal("0")
    sign, digits, exponent = decimal_value.as_tuple()
    coef = 0
    for digit in digits:
        coef = (coef * 10) + digit
    return SpecDecimal(sign=-1 if sign else 1, coef=int(coef), exp=int(exponent))


class MeteringCommandClient:
    """Command-only transport abstraction."""

    transport_name = "unknown"

    async def init_driver(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError

    async def register_node(self, req: RegisterNodeRequest) -> None:
        raise NotImplementedError

    async def configure_meter(self, req: ConfigureElectricalMeterCompatRequest) -> None:
        raise NotImplementedError

    async def set_balance(self, node_id: int, req: SetBalanceAndFlagsRequest) -> None:
        raise NotImplementedError

    async def unregister_node(self, node_id: int) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class HttpCommandClient(MeteringCommandClient):
    """Generic HTTP command client, built directly against the TC 2.0
    Open Source Meter Driver Specification's required endpoints.

    Every request uses plain dicts with the spec's documented field names —
    no vendor-generated model classes. Any driver implementing the
    required HTTP contract works here unmodified.
    """

    transport_name = "http"

    def __init__(self, base_url: str, client_id: str):
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=30.0,
            headers={"X-Client-Id": client_id},
        )

    async def init_driver(self, payload: dict[str, Any]) -> None:
        response = await self._client.post("/v1/init", json=payload)
        response.raise_for_status()

    async def register_node(self, req: RegisterNodeRequest) -> None:
        response = await self._client.post(
            "/v1/nodes/register", json=req.model_dump(mode="json", exclude_none=True)
        )
        response.raise_for_status()

    async def configure_meter(self, req: ConfigureElectricalMeterCompatRequest) -> None:
        # Body-node_id compatibility form (POST /v1/meters/configure): node_id
        # travels in the body, so this single model carries the whole request.
        response = await self._client.post("/v1/meters/configure", json=req.model_dump(mode="json"))
        response.raise_for_status()

    async def set_balance(self, node_id: int, req: SetBalanceAndFlagsRequest) -> None:
        response = await self._client.post(
            "/v1/nodes/{}/balance-and-flags".format(int(node_id)), json=req.model_dump(mode="json")
        )
        response.raise_for_status()

    async def unregister_node(self, node_id: int) -> None:
        response = await self._client.delete("/v1/nodes/{}".format(int(node_id)))
        response.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()


class GrpcCommandClient(MeteringCommandClient):
    """Command client backed by the standard TC 2.0 meter driver gRPC
    profile, using the `meter_driver_spec.grpc` stubs the `meter-driver-spec`
    wheel compiles from the spec's meter_driver.proto — not imported from
    any driver vendor's package.
    """

    transport_name = "grpc"

    def __init__(self, target: str):
        self._channel = grpc.aio.insecure_channel(target)
        self._stub = pb2_grpc.MeterDriverControlStub(self._channel)

    async def init_driver(self, payload: dict[str, Any]) -> None:
        missing = [name for name in _GRPC_INIT_REQUIRED_FIELDS if payload.get(name) in (None, "")]
        if missing:
            raise ValueError(
                "gRPC ConfigureDriver requires the init fields {}; the stored driver "
                "config is missing: {}".format(", ".join(_GRPC_INIT_REQUIRED_FIELDS), ", ".join(missing))
            )
        request = pb2.ConfigureDriver(
            heartbeat_period_duration=int(payload["heartbeat_period_duration"]),
            aes_key=_aes_key_bytes(payload["aes_key"]),
        )
        channel = payload.get("channel")
        if channel is not None:
            request.channel.CopyFrom(UInt32Value(value=int(channel)))
        await self._stub.InitDriver(request)

    async def register_node(self, req: RegisterNodeRequest) -> None:
        await self._stub.RegisterNode(_register_request(req))

    async def configure_meter(self, req: ConfigureElectricalMeterCompatRequest) -> None:
        await self._stub.ConfigureElectricalMeter(_configure_request(req))

    async def set_balance(self, node_id: int, req: SetBalanceAndFlagsRequest) -> None:
        await self._stub.SetElectricalMeterBalanceAndFlags(_set_balance_request(node_id, req))

    async def unregister_node(self, node_id: int) -> None:
        await self._stub.UnregisterNode(pb2.UnregisterNode(node_id=int(node_id)))

    async def close(self) -> None:
        await self._channel.close()


class HttpEventClient:
    """Event streaming client backed by the required HTTP SSE interface."""

    transport_name = "http-sse"

    def __init__(self, base_url: str, client_id: str):
        self._base_url = base_url.rstrip("/")
        self._client_id = client_id

    async def stream_events(self, client_id: str):
        async for event in stream_json_events(self._base_url, client_id or self._client_id):
            yield event

    async def close(self) -> None:
        return None


class GrpcEventClient:
    """Event streaming client backed by the standard TC 2.0 gRPC profile's
    SubscribeEvents stream, through the `meter_driver_spec.grpc` stubs.
    """

    transport_name = "grpc-stream"

    def __init__(self, target: str):
        self._channel = grpc.aio.insecure_channel(target)
        self._stub = pb2_grpc.MeterDriverControlStub(self._channel)
        self._event_id = 0

    async def stream_events(self, client_id: str):
        del client_id
        request = pb2.SubscribeEventsRequest()
        async for event in self._stub.SubscribeEvents(request):
            self._event_id += 1
            raw = _grpc_event_to_raw_dict(event, self._event_id)
            if raw is None:
                continue
            yield raw

    async def close(self) -> None:
        await self._channel.close()


def _selected_interface_details(provider, provider_details):
    if provider_details and provider_details.get("selected_interface_details"):
        return provider_details["selected_interface_details"]
    return {}


def _grpc_target(provider, provider_details) -> str | None:
    """Return the grpc `target` the driver advertised in x-meter-driver, or None.

    The live contract's selected-interface details win; the target saved at
    registration is the fallback. Nothing is derived from the HTTP base URL:
    the spec has no default gRPC port, so a driver that advertises no grpc
    interface has no target.
    """
    selected_details = _selected_interface_details(provider, provider_details)
    target = selected_details.get("target") or selected_details.get("address")
    target = str(target or "").strip()
    if not target:
        target = str((provider or {}).get("selected_interface_target") or "").strip()
    return target or None


def _require_grpc_target(provider, provider_details) -> str:
    target = _grpc_target(provider, provider_details)
    if not target:
        raise GrpcTargetUnavailable(
            "provider {} selected gRPC but its contract advertises no grpc interface target".format(
                (provider or {}).get("base_url")
            )
        )
    return target


def build_command_client(provider, client_id: str, provider_details=None) -> MeteringCommandClient:
    """Create the command transport for the selected provider interface."""
    selected_interface = str((provider or {}).get("selected_interface") or "http").strip().lower()
    if selected_interface == "grpc":
        return GrpcCommandClient(_require_grpc_target(provider, provider_details))
    return HttpCommandClient(str((provider or {}).get("base_url") or ""), client_id)


def build_event_client(provider, client_id: str, provider_details=None):
    """Create the event transport for the selected provider interface."""
    selected_interface = str((provider or {}).get("selected_interface") or "http").strip().lower()
    if selected_interface == "grpc":
        return GrpcEventClient(_require_grpc_target(provider, provider_details))
    return HttpEventClient(str((provider or {}).get("base_url") or ""), client_id)


async def initialize_provider(provider, payload: dict[str, Any], provider_details=None) -> None:
    """Initialize a driver over its selected interface."""
    client_id = "init-" + uuid.uuid4().hex[:8]
    client = build_command_client(provider, client_id, provider_details=provider_details)
    try:
        await client.init_driver(payload)
    finally:
        await client.close()


def initialize_provider_sync(provider, payload: dict[str, Any], provider_details=None) -> None:
    """Sync wrapper for initializing a driver over its selected interface."""
    asyncio.run(initialize_provider(provider, payload, provider_details=provider_details))


def _aes_key_bytes(value: Any) -> bytes:
    if isinstance(value, str):
        return binascii.unhexlify(value)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return bytes(int(item) for item in value)


def _register_request(req: RegisterNodeRequest) -> pb2.RegisterNode:
    request = pb2.RegisterNode(
        node_id=int(req.node_id),
        node_type=getattr(pb2, str(req.node_type)),
    )
    if req.mac is not None:
        request.mac.CopyFrom(UInt32Value(value=int(req.mac)))
    if req.request_phased_readings:
        request.request_phased_readings.CopyFrom(BoolValue(value=bool(req.request_phased_readings)))
    return request


def _configure_request(req: ConfigureElectricalMeterCompatRequest) -> pb2.ConfigureElectricalMeter:
    c = req.configuration
    configuration = pb2.ElectricalMeterConfiguration(
        node_id=int(req.node_id),
        power_limit=float(c.power_limit),
        current_limit=float(c.current_limit),
        startup_delay=int(c.startup_delay),
        throttle_on_time=int(c.throttle_on_time),
        throttle_off_time=int(c.throttle_off_time),
        throttle_count_limit=int(c.throttle_count_limit),
    )
    # The spec ElectricalMeterCommandName values match the pb2 enum member
    # names one-to-one (e.g. "ElectricalMeterCommandEnable").
    return pb2.ConfigureElectricalMeter(
        node_id=int(req.node_id),
        command=getattr(pb2.ElectricalMeterCommand, req.command.value),
        configuration=configuration,
    )


def _set_balance_request(
    node_id: int, req: SetBalanceAndFlagsRequest
) -> pb2.SetElectricalMeterBalanceAndFlags:
    return pb2.SetElectricalMeterBalanceAndFlags(
        node_id=int(node_id),
        balance=_decimal_proto(req.balance),
        low_balance_flag=bool(req.low_balance_flag),
    )


def _decimal_proto(value: SpecDecimal) -> pb2.Decimal:
    return pb2.Decimal(sign=int(value.sign), coef=int(value.coef), exp=int(value.exp))


# Event names whose protobuf message maps field-for-field onto the spec's
# SSE payload, so a JSON rendering of the message is the envelope's data.
_PASSTHROUGH_GRPC_EVENTS = {
    "heartbeat_statistics",
    "gateway_status",
    "heartbeat_read_hops",
    "driver_configuration_applied",
    "node_registered",
    "node_already_registered",
    "node_unregistered",
    "node_to_unregister_unknown",
    "invalid_electrical_meter_configuration",
    "electrical_meter_configuration_accepted",
    "electrical_meter_configuration_applied",
    "electrical_meter_balance_and_flags_accepted",
}

# ElectricalMeterReading fields (spec section 6) by wire type.
_READING_INT_FIELDS = ("period_start", "period_end", "uptime_secs")
_READING_FLOAT_FIELDS = (
    "frequency",
    "current_avg",
    "current_min",
    "current_max",
    "voltage_avg",
    "voltage_min",
    "voltage_max",
    "true_power_avg",
    "true_power_inst",
    "apparent_power_avg",
    "power_factor_avg",
    "energy",
    "user_power_limit",
)
# The per-phase measurements ElectricalMeterReadingPhased adds, suffixed _a/_b/_c.
_PHASED_FLOAT_FIELDS = (
    "frequency",
    "current_avg",
    "current_min",
    "current_max",
    "voltage_avg",
    "voltage_min",
    "voltage_max",
    "true_power_avg",
    "true_power_inst",
    "apparent_power_avg",
    "power_factor_avg",
)
_PHASES = ("a", "b", "c")


def _grpc_event_to_raw_dict(event: "pb2.MeterDriverEvent", event_id: int):
    """Translate a protobuf stream event into the `{type, event_id, data}` envelope.

    `type` and `data` are what the dispatcher reads, exactly as an SSE frame
    carries them; `data` uses the spec's field names and JSON types.
    """
    event_name = event.WhichOneof("event")
    if not event_name:
        return None

    message = getattr(event, event_name)

    if event_name == "electrical_meter_reading":
        data = _reading_data(message)
    elif event_name == "electrical_meter_reading_phased":
        data = _phased_reading_data(message)
    elif event_name == "node_firmware_version_changed":
        data = {
            "node_id": int(message.node_id),
            "firmware_version": _version_dict(message.firmware_version),
        }
    elif event_name in _PASSTHROUGH_GRPC_EVENTS:
        data = _message_data(message)
    else:
        logger.debug("ignoring unsupported gRPC provider event %s", event_name)
        return None

    return {"type": event_name, "event_id": event_id, "data": data}


def _message_data(message) -> dict[str, Any]:
    """Render a protobuf message as the spec's JSON payload.

    Fields at their default value are kept (the spec payloads require
    them) and a 64-bit node_id, which the protobuf JSON mapping renders as
    a string, is restored to an integer.
    """
    data = _message_dict(message)
    if "node_id" in data:
        data["node_id"] = int(message.node_id)
    return data


def _message_dict(message) -> dict[str, Any]:
    """Render a protobuf message with unset singular submessages rendered as their defaults.

    `always_print_fields_with_no_presence` keeps default scalars, but a
    submessage field has presence, so an unset one (e.g. a heartbeat's
    `millisecond_read_reply_stats`) is omitted and the spec payload that
    requires it fails validation. Each singular submessage outside a
    oneof is rendered from its value, which reads as the default instance
    when unset. Oneof members and google.protobuf wrappers keep their
    absent-means-absent meaning.
    """
    data = MessageToDict(message, preserving_proto_field_name=True, always_print_fields_with_no_presence=True)
    for field in message.DESCRIPTOR.fields:
        submessage_type = field.message_type
        if (
            submessage_type is None
            or field.is_repeated
            or field.containing_oneof is not None
            or submessage_type.full_name.startswith("google.protobuf.")
        ):
            continue
        data[field.name] = _message_dict(getattr(message, field.name))
    return data


def _reading_data(message) -> dict[str, Any]:
    data: dict[str, Any] = {"node_id": int(message.node_id), "state": int(message.state)}
    for name in _READING_INT_FIELDS:
        data[name] = int(getattr(message, name))
    for name in _READING_FLOAT_FIELDS:
        data[name] = float(getattr(message, name))
    return data


def _phased_reading_data(message) -> dict[str, Any]:
    data = _reading_data(message)
    for name in _PHASED_FLOAT_FIELDS:
        for phase in _PHASES:
            field = "{}_{}".format(name, phase)
            data[field] = float(getattr(message, field))
    data["phases"] = {phase: bool(getattr(message.phases, phase)) for phase in _PHASES}
    data["computed_fields_version"] = int(message.computed_fields_version)
    return data


def _version_dict(version_message: Any) -> dict[str, int]:
    """Return a complete semantic version dict from a protobuf Version message."""
    return {
        "major": int(getattr(version_message, "major", 0) or 0),
        "minor": int(getattr(version_message, "minor", 0) or 0),
        "patch": int(getattr(version_message, "patch", 0) or 0),
    }
