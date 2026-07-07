from __future__ import annotations

from dataclasses import dataclass

from .meter_state import MeterState
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["MeterReadingEvent"]

@dataclass
class MeterReadingEvent:
    """
    Period-aggregated reading from a meter.  Emitted at the end of each provider heartbeat
    for each meter that successfully responded. Unique on `(meter_id, period_start,
    period_end)`. Single-phase or aggregated-three-phase shape; see `meter_reading_phased`
    for per-phase data.
    
    Args:
        apparent_power_avg_va (float)
                                 : 
        current_avg_amps (float) : 
        current_max_amps (float) : 
        current_min_amps (float) : 
        energy_wh (float)        : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        frequency_hz (float)     : 
        meter_id (str)           : 
        period_end (int)         : 
        period_start (int)       : 
        power_factor_avg (float) : 
        state (MeterState)       : Operational state of an electrical meter.  Vendors may
                                   not implement every state; subscribers should treat
                                   unrecognised values as `unknown`.
        true_power_avg_watts (float)
                                 : 
        true_power_inst_watts (float)
                                 : 
        uptime_seconds (int)     : 
        user_power_limit_watts (float)
                                 : 
        voltage_avg (float)      : 
        voltage_max (float)      : 
        voltage_min (float)      : 
    """
    apparent_power_avg_va: float
    current_avg_amps: float
    current_max_amps: float
    current_min_amps: float
    energy_wh: float
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    frequency_hz: float
    meter_id: str
    period_end: int
    period_start: int
    power_factor_avg: float
    state: MeterState  # Operational state of an electrical meter.  Vendors may not implement every state; subscribers should treat unrecognised values as `unknown`.
    true_power_avg_watts: float
    true_power_inst_watts: float
    uptime_seconds: int
    user_power_limit_watts: float
    voltage_avg: float
    voltage_max: float
    voltage_min: float
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "apparent_power_avg_va": "apparent_power_avg_va",
            "current_avg_amps": "current_avg_amps",
            "current_max_amps": "current_max_amps",
            "current_min_amps": "current_min_amps",
            "energy_wh": "energy_wh",
            "event_id": "event_id",
            "event_type": "event_type",
            "frequency_hz": "frequency_hz",
            "meter_id": "meter_id",
            "period_end": "period_end",
            "period_start": "period_start",
            "power_factor_avg": "power_factor_avg",
            "state": "state",
            "true_power_avg_watts": "true_power_avg_watts",
            "true_power_inst_watts": "true_power_inst_watts",
            "uptime_seconds": "uptime_seconds",
            "user_power_limit_watts": "user_power_limit_watts",
            "voltage_avg": "voltage_avg",
            "voltage_max": "voltage_max",
            "voltage_min": "voltage_min",
        }
        key_transform_with_dump = {
            "apparent_power_avg_va": "apparent_power_avg_va",
            "current_avg_amps": "current_avg_amps",
            "current_max_amps": "current_max_amps",
            "current_min_amps": "current_min_amps",
            "energy_wh": "energy_wh",
            "event_id": "event_id",
            "event_type": "event_type",
            "frequency_hz": "frequency_hz",
            "meter_id": "meter_id",
            "period_end": "period_end",
            "period_start": "period_start",
            "power_factor_avg": "power_factor_avg",
            "state": "state",
            "true_power_avg_watts": "true_power_avg_watts",
            "true_power_inst_watts": "true_power_inst_watts",
            "uptime_seconds": "uptime_seconds",
            "user_power_limit_watts": "user_power_limit_watts",
            "voltage_avg": "voltage_avg",
            "voltage_max": "voltage_max",
            "voltage_min": "voltage_min",
        }