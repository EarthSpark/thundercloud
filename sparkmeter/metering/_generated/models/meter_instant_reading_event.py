from __future__ import annotations

from dataclasses import dataclass

from .meter_state import MeterState
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["MeterInstantReadingEvent"]

@dataclass
class MeterInstantReadingEvent:
    """
    Reply to `read_meter_now`. Single-shot, not period-aggregated.
    
    Args:
        active_power_watts (float): 
        apparent_power_va (float): 
        correlation_id (str)     : 
        current_amps (float)     : 
        energy_wh (float)        : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        frequency_hz (float)     : 
        meter_id (str)           : 
        power_factor (float)     : 
        state (MeterState)       : Operational state of an electrical meter.  Vendors may
                                   not implement every state; subscribers should treat
                                   unrecognised values as `unknown`.
        uptime_seconds (int)     : 
        voltage (float)          : 
    """
    active_power_watts: float
    apparent_power_va: float
    correlation_id: str
    current_amps: float
    energy_wh: float
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    frequency_hz: float
    meter_id: str
    power_factor: float
    state: MeterState  # Operational state of an electrical meter.  Vendors may not implement every state; subscribers should treat unrecognised values as `unknown`.
    uptime_seconds: int
    voltage: float
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "active_power_watts": "active_power_watts",
            "apparent_power_va": "apparent_power_va",
            "correlation_id": "correlation_id",
            "current_amps": "current_amps",
            "energy_wh": "energy_wh",
            "event_id": "event_id",
            "event_type": "event_type",
            "frequency_hz": "frequency_hz",
            "meter_id": "meter_id",
            "power_factor": "power_factor",
            "state": "state",
            "uptime_seconds": "uptime_seconds",
            "voltage": "voltage",
        }
        key_transform_with_dump = {
            "active_power_watts": "active_power_watts",
            "apparent_power_va": "apparent_power_va",
            "correlation_id": "correlation_id",
            "current_amps": "current_amps",
            "energy_wh": "energy_wh",
            "event_id": "event_id",
            "event_type": "event_type",
            "frequency_hz": "frequency_hz",
            "meter_id": "meter_id",
            "power_factor": "power_factor",
            "state": "state",
            "uptime_seconds": "uptime_seconds",
            "voltage": "voltage",
        }