from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .meter_network_statistics import MeterNetworkStatistics
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["NetworkHealthEvent"]

@dataclass
class NetworkHealthEvent:
    """
    Reply to `query_network_health`.  `stats` is per-meter; if the request specified a
    single `meter_id`, the list contains that one; if not, the list is the full registered
    roster (possibly empty if no meters are registered).
    
    Args:
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        stats (List[MeterNetworkStatistics])
                                 : 
        timestamp (int)          : 
    """
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    stats: List[MeterNetworkStatistics]
    timestamp: int
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "stats": "stats",
            "timestamp": "timestamp",
        }
        key_transform_with_dump = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "stats": "stats",
            "timestamp": "timestamp",
        }