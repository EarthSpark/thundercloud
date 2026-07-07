from __future__ import annotations

from dataclasses import dataclass

from .command_accepted_event_result import CommandAcceptedEventResult
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["CommandAcceptedEvent"]

@dataclass
class CommandAcceptedEvent:
    """
    Provider has accepted the command for processing.  For single-reply commands this is the
    terminal event. For two-stage commands, expect a later
    `command_applied`/`command_failed`/ `command_timed_out` with the same `correlation_id`.
    
    Args:
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        result (CommandAcceptedEventResult | None)
                                 : 
    """
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    result: CommandAcceptedEventResult | None = None
    
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