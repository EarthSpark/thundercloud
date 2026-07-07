from __future__ import annotations

from dataclasses import dataclass

from .meter_network_statistics_read_reply_latency_ms import MeterNetworkStatisticsReadReplyLatencyMs
from .meter_network_statistics_set_config_reply_latency_ms import MeterNetworkStatisticsSetConfigReplyLatencyMs

__all__ = ["MeterNetworkStatistics"]

@dataclass
class MeterNetworkStatistics:
    """
    MeterNetworkStatistics dataclass
    
    Args:
        meter_id (str)           : 
        packets_received_in_current_heartbeat (int)
                                 : 
        packets_received_in_recent_heartbeats (int)
                                 : 
        packets_sent_in_current_heartbeat (int)
                                 : 
        packets_sent_in_recent_heartbeats (int)
                                 : 
        total_packets_received (int)
                                 : 
        total_packets_sent (int) : 
        read_reply_latency_ms (MeterNetworkStatisticsReadReplyLatencyMs | None)
                                 : 
        set_config_reply_latency_ms (MeterNetworkStatisticsSetConfigReplyLatencyMs | None)
                                 : 
    """
    meter_id: str
    packets_received_in_current_heartbeat: int
    packets_received_in_recent_heartbeats: int
    packets_sent_in_current_heartbeat: int
    packets_sent_in_recent_heartbeats: int
    total_packets_received: int
    total_packets_sent: int
    read_reply_latency_ms: MeterNetworkStatisticsReadReplyLatencyMs | None = None
    set_config_reply_latency_ms: MeterNetworkStatisticsSetConfigReplyLatencyMs | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "meter_id": "meter_id",
            "packets_received_in_current_heartbeat": "packets_received_in_current_heartbeat",
            "packets_received_in_recent_heartbeats": "packets_received_in_recent_heartbeats",
            "packets_sent_in_current_heartbeat": "packets_sent_in_current_heartbeat",
            "packets_sent_in_recent_heartbeats": "packets_sent_in_recent_heartbeats",
            "read_reply_latency_ms": "read_reply_latency_ms",
            "set_config_reply_latency_ms": "set_config_reply_latency_ms",
            "total_packets_received": "total_packets_received",
            "total_packets_sent": "total_packets_sent",
        }
        key_transform_with_dump = {
            "meter_id": "meter_id",
            "packets_received_in_current_heartbeat": "packets_received_in_current_heartbeat",
            "packets_received_in_recent_heartbeats": "packets_received_in_recent_heartbeats",
            "packets_sent_in_current_heartbeat": "packets_sent_in_current_heartbeat",
            "packets_sent_in_recent_heartbeats": "packets_sent_in_recent_heartbeats",
            "read_reply_latency_ms": "read_reply_latency_ms",
            "set_config_reply_latency_ms": "set_config_reply_latency_ms",
            "total_packets_received": "total_packets_received",
            "total_packets_sent": "total_packets_sent",
        }