from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .meter_reading_phased_event_per_phase import MeterReadingPhasedEventPerPhase
from .meter_state import MeterState
from .phase import Phase
from .phase_reading import PhaseReading
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["MeterReadingPhasedEvent"]

@dataclass
class MeterReadingPhasedEvent:
    """
    Per-phase reading from a multi-phase meter.  `phases` lists which phases are present;
    `per_phase` holds the scalars for each. Aggregates across present phases are also
    provided as the top-level fields.
    
    Args:
        aggregate (PhaseReading) : Single-phase scalars within a `meter_reading_phased`
                                   event.
        energy_wh (float)        : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        meter_id (str)           : 
        per_phase (MeterReadingPhasedEventPerPhase)
                                 : 
        period_end (int)         : 
        period_start (int)       : 
        phases (List[Phase])     : 
        state (MeterState)       : Operational state of an electrical meter.  Vendors may
                                   not implement every state; subscribers should treat
                                   unrecognised values as `unknown`.
        uptime_seconds (int)     : 
        user_power_limit_watts (float)
                                 : 
        computed_fields_version (int | None)
                                 : Version of the aggregate-computation algorithm. Bump on
                                   any change to how aggregate fields are derived from per-
                                   phase data.
    """
    aggregate: PhaseReading  # Single-phase scalars within a `meter_reading_phased` event.
    energy_wh: float
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    meter_id: str
    per_phase: MeterReadingPhasedEventPerPhase
    period_end: int
    period_start: int
    phases: List[Phase]
    state: MeterState  # Operational state of an electrical meter.  Vendors may not implement every state; subscribers should treat unrecognised values as `unknown`.
    uptime_seconds: int
    user_power_limit_watts: float
    computed_fields_version: int | None = 0  # Version of the aggregate-computation algorithm. Bump on any change to how aggregate fields are derived from per-phase data.
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "aggregate": "aggregate",
            "computed_fields_version": "computed_fields_version",
            "energy_wh": "energy_wh",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
            "per_phase": "per_phase",
            "period_end": "period_end",
            "period_start": "period_start",
            "phases": "phases",
            "state": "state",
            "uptime_seconds": "uptime_seconds",
            "user_power_limit_watts": "user_power_limit_watts",
        }
        key_transform_with_dump = {
            "aggregate": "aggregate",
            "computed_fields_version": "computed_fields_version",
            "energy_wh": "energy_wh",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
            "per_phase": "per_phase",
            "period_end": "period_end",
            "period_start": "period_start",
            "phases": "phases",
            "state": "state",
            "uptime_seconds": "uptime_seconds",
            "user_power_limit_watts": "user_power_limit_watts",
        }