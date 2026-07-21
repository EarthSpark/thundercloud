"""Transport adapters for metering command and event traffic.

Generic HTTP+SSE and gRPC clients built directly against the Thunder-Cloud
2.0 Open Source Meter Driver Specification — not against any vendor's
package. Any driver that implements the spec's required HTTP+SSE contract
works here with zero vendor-specific code. A driver that additionally
implements the optional gRPC profile (see sparkmeter/metering/proto/)
works over gRPC too, using the client Thundercloud compiles from its own
spec-owned .proto files.

SparkNet-Http gets no special treatment here: it's one compliant driver
instance among however many a deployment configures. Nothing in this
module imports a vendor-published client package.
"""

from __future__ import annotations

import asyncio
import binascii
import logging
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

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
        # The spec's own worked examples show POST /v1/init; the reference
        # driver (SparkNet-Http-New) actually serves this at
        # /v1/sparknet/init. Targeting the endpoint that's actually live.
        response = await self._client.post("/v1/sparknet/init", json=payload)
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
    profile, compiled from Thundercloud's own proto (sparkmeter/metering/proto/)
    — not imported from any driver vendor's package.
    """

    transport_name = "grpc"

    def __init__(self, target: str):
        self._channel = grpc.aio.insecure_channel(target)
        self._stub = pb2_grpc.MeterDriverControlStub(self._channel)

    async def init_driver(self, payload: dict[str, Any]) -> None:
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
    SubscribeEvents stream, compiled from Thundercloud's own proto.
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
    selected_details = _selected_interface_details(provider, provider_details)
    target = selected_details.get("target") or selected_details.get("address")
    target = str(target or "").strip()
    if not target:
        target = str((provider or {}).get("selected_interface_target") or "").strip()
    if not target:
        base_url = str((provider or {}).get("base_url") or "").strip()
        parsed = urlparse(base_url)
        hostname = parsed.hostname or ""
        if hostname:
            target = "{}:50051".format(hostname)
            logger.warning(
                "provider %s selected gRPC but no target metadata is available; "
                "falling back to derived target %s",
                base_url,
                target,
            )
    return target or None


def build_command_client(provider, client_id: str, provider_details=None) -> MeteringCommandClient:
    """Create the command transport for the selected provider interface."""
    selected_interface = str((provider or {}).get("selected_interface") or "http").strip().lower()
    if selected_interface == "grpc":
        target = _grpc_target(provider, provider_details)
        if target:
            return GrpcCommandClient(target)
        logger.warning(
            "provider %s selected gRPC but no grpc target is available; falling back to HTTP commands",
            (provider or {}).get("base_url"),
        )
    return HttpCommandClient(str((provider or {}).get("base_url") or ""), client_id)


def build_event_client(provider, client_id: str, provider_details=None):
    """Create the event transport for the selected provider interface."""
    selected_interface = str((provider or {}).get("selected_interface") or "http").strip().lower()
    if selected_interface == "grpc":
        target = _grpc_target(provider, provider_details)
        if target:
            return GrpcEventClient(target)
        logger.warning(
            "provider %s selected gRPC but no grpc target is available; falling back to HTTP SSE events",
            (provider or {}).get("base_url"),
        )
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


def _grpc_event_to_raw_dict(event: "pb2.MeterDriverEvent", event_id: int):
    """Translate a protobuf stream event into the raw event dict shape."""
    event_name = event.WhichOneof("event")
    if not event_name:
        return None

    message = getattr(event, event_name)
    message_dict = MessageToDict(message, preserving_proto_field_name=True)

    if event_name == "electrical_meter_reading":
        data = {
            "node_id": int(message.node_id),
            "period_start": int(message.period_start),
            "period_end": int(message.period_end),
            "state": int(message.state),
            "frequency": float(message.frequency),
            "current_avg": float(message.current_avg),
            "current_min": float(message.current_min),
            "current_max": float(message.current_max),
            "voltage_avg": float(message.voltage_avg),
            "voltage_min": float(message.voltage_min),
            "voltage_max": float(message.voltage_max),
            "true_power_avg": float(message.true_power_avg),
            "true_power_inst": float(message.true_power_inst),
            "apparent_power_avg": float(message.apparent_power_avg),
            "power_factor_avg": float(message.power_factor_avg),
            "energy": float(message.energy),
            "uptime_secs": int(message.uptime_secs),
            "user_power_limit": float(message.user_power_limit),
        }
        return {
            "type": "electrical_meter_reading",
            "event_id": event_id,
            "event_type": "meter_reading",
            "meter_id": str(message.node_id),
            "period_start": int(message.period_start),
            "period_end": int(message.period_end),
            "state": _meter_state_name(message.state),
            "frequency_hz": float(message.frequency),
            "current_avg_amps": float(message.current_avg),
            "current_max_amps": float(message.current_max),
            "current_min_amps": float(message.current_min),
            "voltage_avg": float(message.voltage_avg),
            "voltage_max": float(message.voltage_max),
            "voltage_min": float(message.voltage_min),
            "true_power_avg_watts": float(message.true_power_avg),
            "true_power_inst_watts": float(message.true_power_inst),
            "apparent_power_avg_va": float(message.apparent_power_avg),
            "power_factor_avg": float(message.power_factor_avg),
            "energy_wh": float(message.energy),
            "uptime_seconds": int(message.uptime_secs),
            "user_power_limit_watts": float(message.user_power_limit),
            "data": data,
        }

    if event_name == "electrical_meter_reading_phased":
        data = {
            "node_id": int(message.node_id),
            "period_start": int(message.period_start),
            "period_end": int(message.period_end),
            "state": int(message.state),
            "energy": float(message.energy),
            "uptime_secs": int(message.uptime_secs),
            "user_power_limit": float(message.user_power_limit),
        }
        return {
            "type": "electrical_meter_reading_phased",
            "event_id": event_id,
            "event_type": "meter_reading_phased",
            "meter_id": str(message.node_id),
            "period_start": int(message.period_start),
            "period_end": int(message.period_end),
            "state": _meter_state_name(message.state),
            "energy_wh": float(message.energy),
            "uptime_seconds": int(message.uptime_secs),
            "user_power_limit_watts": float(message.user_power_limit),
            "aggregate": _phase_reading_dict(message),
            "per_phase": _phased_per_phase_dict(message),
            "phases": _phases_list(message),
            "computed_fields_version": int(message.computed_fields_version),
            "data": data,
        }

    if event_name == "heartbeat_statistics":
        return {
            "type": "heartbeat_statistics",
            "event_id": event_id,
            "event_type": "heartbeat_summary",
            "timestamp": int(message.timestamp),
            "total_registered_meters": int(message.total_registered_nodes),
            "meters_attempted": int(message.nodes_reached_out_to_in_current_heartbeat),
            "meters_responded": int(message.nodes_heard_from_in_current_heartbeat),
            "packets_sent": int(message.packets_sent_in_current_heartbeat),
            "packets_received": int(message.packets_received_in_current_heartbeat),
            "read_reply_latency_ms": _stats_dict(message_dict.get("millisecond_read_reply_stats")),
            "set_config_reply_latency_ms": _stats_dict(
                message_dict.get("millisecond_set_config_reply_stats")
            ),
            "data": message_dict,
        }

    if event_name == "node_firmware_version_changed":
        return {
            "type": "node_firmware_version_changed",
            "event_id": event_id,
            "event_type": "meter_firmware_changed",
            "meter_id": str(message.node_id),
            "firmware_version": _version_dict(message.firmware_version),
            "data": {
                "node_id": int(message.node_id),
                "firmware_version": _version_dict(message.firmware_version),
            },
        }

    if event_name in {
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
    }:
        return {
            "type": event_name,
            "event_id": event_id,
            "data": message_dict,
        }

    logger.debug("ignoring unsupported gRPC provider event %s", event_name)
    return None


def _meter_state_name(state_value: int) -> str:
    mapping = {
        getattr(pb2.ElectricalMeterState, "ElectricalMeterStateOff", 0): "off",
        getattr(pb2.ElectricalMeterState, "ElectricalMeterStateOn", 1): "on",
        getattr(pb2.ElectricalMeterState, "ElectricalMeterStateUnknown", -1): "unknown",
    }
    return mapping.get(state_value, "unknown")


def _version_dict(version_message: Any) -> dict[str, int]:
    """Return a complete semantic version dict from a protobuf Version message."""
    return {
        "major": int(getattr(version_message, "major", 0) or 0),
        "minor": int(getattr(version_message, "minor", 0) or 0),
        "patch": int(getattr(version_message, "patch", 0) or 0),
    }


def _phase_reading_dict(message) -> dict[str, float]:
    return {
        "apparent_power_avg_va": float(message.apparent_power_avg),
        "current_avg_amps": float(message.current_avg),
        "current_max_amps": float(message.current_max),
        "current_min_amps": float(message.current_min),
        "frequency_hz": float(message.frequency),
        "power_factor_avg": float(message.power_factor_avg),
        "true_power_avg_watts": float(message.true_power_avg),
        "true_power_inst_watts": float(message.true_power_inst),
        "voltage_avg": float(message.voltage_avg),
        "voltage_max": float(message.voltage_max),
        "voltage_min": float(message.voltage_min),
    }


def _phased_per_phase_dict(message) -> dict[str, dict[str, float]]:
    per_phase = {}
    for phase in _phases_list(message):
        suffix = phase
        per_phase[phase] = {
            "apparent_power_avg_va": float(getattr(message, f"apparent_power_avg_{suffix}")),
            "current_avg_amps": float(getattr(message, f"current_avg_{suffix}")),
            "current_max_amps": float(getattr(message, f"current_max_{suffix}")),
            "current_min_amps": float(getattr(message, f"current_min_{suffix}")),
            "frequency_hz": float(getattr(message, f"frequency_{suffix}")),
            "power_factor_avg": float(getattr(message, f"power_factor_avg_{suffix}")),
            "true_power_avg_watts": float(getattr(message, f"true_power_avg_{suffix}")),
            "true_power_inst_watts": float(getattr(message, f"true_power_inst_{suffix}")),
            "voltage_avg": float(getattr(message, f"voltage_avg_{suffix}")),
            "voltage_max": float(getattr(message, f"voltage_max_{suffix}")),
            "voltage_min": float(getattr(message, f"voltage_min_{suffix}")),
        }
    return per_phase


def _phases_list(message) -> list[str]:
    phases = []
    if getattr(message.phases, "a", False):
        phases.append("a")
    if getattr(message.phases, "b", False):
        phases.append("b")
    if getattr(message.phases, "c", False):
        phases.append("c")
    return phases


def _stats_dict(data: dict[str, Any] | None):
    if not data:
        return None
    return {
        "count": int(data.get("count", 0)),
        "last_value": float(data.get("last_value", 0.0)),
        "max": float(data.get("max", 0.0)),
        "min": float(data.get("min", 0.0)),
        "avg": float(data.get("avg", 0.0)),
    }
