from __future__ import annotations

from dataclasses import dataclass

from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["CommandCachedEvent"]

@dataclass
class CommandCachedEvent:
    """
    Cache-reply commands only: provider stored the value.  Delivery to the underlying meter
    is deferred and unobservable through this event. To verify, query the meter directly.
    
    Args:
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
    """
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
        }
        key_transform_with_dump = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
        }