from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .meter_error_entry import MeterErrorEntry
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["MeterErrorsEvent"]

@dataclass
class MeterErrorsEvent:
    """
    Reply to `query_meter_errors`.
    
    Args:
        correlation_id (str)     : 
        errors (List[MeterErrorEntry])
                                 : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        meter_id (str)           : 
    """
    correlation_id: str
    errors: List[MeterErrorEntry]
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    meter_id: str
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "correlation_id": "correlation_id",
            "errors": "errors",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "correlation_id": "correlation_id",
            "errors": "errors",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
        }