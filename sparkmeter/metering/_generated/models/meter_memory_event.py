from __future__ import annotations

from dataclasses import dataclass

from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["MeterMemoryEvent"]

@dataclass
class MeterMemoryEvent:
    """
    Reply to `read_meter_memory`.
    
    Args:
        address (int)            : 
        correlation_id (str)     : 
        data_ (str)              : Maps from 'data'
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        meter_id (str)           : 
    """
    address: int
    correlation_id: str
    data_: str  # Maps from 'data'
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    meter_id: str
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "address": "address",
            "correlation_id": "correlation_id",
            "data": "data_",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "address": "address",
            "correlation_id": "correlation_id",
            "data_": "data",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
        }