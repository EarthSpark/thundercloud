from __future__ import annotations

from dataclasses import dataclass

from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["MeterRegisterEvent"]

@dataclass
class MeterRegisterEvent:
    """
    Reply to `read_meter_register`.
    
    Args:
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        meter_id (str)           : 
        register_address (int)   : 
        register_value (int)     : 
    """
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    meter_id: str
    register_address: int
    register_value: int
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
            "register_address": "register_address",
            "register_value": "register_value",
        }
        key_transform_with_dump = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
            "register_address": "register_address",
            "register_value": "register_value",
        }