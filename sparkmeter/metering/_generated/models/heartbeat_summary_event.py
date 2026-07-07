from __future__ import annotations

from dataclasses import dataclass

from .heartbeat_summary_event_read_reply_latency_ms import HeartbeatSummaryEventReadReplyLatencyMs
from .heartbeat_summary_event_set_config_reply_latency_ms import HeartbeatSummaryEventSetConfigReplyLatencyMs
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["HeartbeatSummaryEvent"]

@dataclass
class HeartbeatSummaryEvent:
    """
    End-of-heartbeat aggregate across the whole network.
    
    Args:
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        meters_attempted (int)   : 
        meters_responded (int)   : 
        packets_received (int)   : 
        packets_sent (int)       : 
        timestamp (int)          : 
        total_registered_meters (int)
                                 : 
        read_reply_latency_ms (HeartbeatSummaryEventReadReplyLatencyMs | None)
                                 : 
        set_config_reply_latency_ms (HeartbeatSummaryEventSetConfigReplyLatencyMs | None)
                                 : 
    """
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    meters_attempted: int
    meters_responded: int
    packets_received: int
    packets_sent: int
    timestamp: int
    total_registered_meters: int
    read_reply_latency_ms: HeartbeatSummaryEventReadReplyLatencyMs | None = None
    set_config_reply_latency_ms: HeartbeatSummaryEventSetConfigReplyLatencyMs | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "event_id": "event_id",
            "event_type": "event_type",
            "meters_attempted": "meters_attempted",
            "meters_responded": "meters_responded",
            "packets_received": "packets_received",
            "packets_sent": "packets_sent",
            "read_reply_latency_ms": "read_reply_latency_ms",
            "set_config_reply_latency_ms": "set_config_reply_latency_ms",
            "timestamp": "timestamp",
            "total_registered_meters": "total_registered_meters",
        }
        key_transform_with_dump = {
            "event_id": "event_id",
            "event_type": "event_type",
            "meters_attempted": "meters_attempted",
            "meters_responded": "meters_responded",
            "packets_received": "packets_received",
            "packets_sent": "packets_sent",
            "read_reply_latency_ms": "read_reply_latency_ms",
            "set_config_reply_latency_ms": "set_config_reply_latency_ms",
            "timestamp": "timestamp",
            "total_registered_meters": "total_registered_meters",
        }