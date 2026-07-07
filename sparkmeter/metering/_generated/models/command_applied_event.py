from __future__ import annotations

from dataclasses import dataclass

from .command_applied_event_result import CommandAppliedEventResult
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["CommandAppliedEvent"]

@dataclass
class CommandAppliedEvent:
    """
    Two-stage commands only: the meter has acknowledged the change.
    
    Args:
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        result (CommandAppliedEventResult | None)
                                 : 
    """
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    result: CommandAppliedEventResult | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "result": "result",
        }
        key_transform_with_dump = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "result": "result",
        }