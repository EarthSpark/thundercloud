from __future__ import annotations

from dataclasses import dataclass

from .log_level import LogLevel
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["LogEvent"]

@dataclass
class LogEvent:
    """
    Provider log line.
    
    Args:
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        level (LogLevel)         : 
        message (str)            : 
    """
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    level: LogLevel
    message: str
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "event_id": "event_id",
            "event_type": "event_type",
            "level": "level",
            "message": "message",
        }
        key_transform_with_dump = {
            "event_id": "event_id",
            "event_type": "event_type",
            "level": "level",
            "message": "message",
        }