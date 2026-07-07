from __future__ import annotations

from dataclasses import dataclass

from .firmware_version import FirmwareVersion
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["ProviderStatusEvent"]

@dataclass
class ProviderStatusEvent:
    """
    Reply to `query_provider_status`.
    
    Args:
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        messages_received (int)  : 
        messages_sent (int)      : 
        network_connected (bool) : 
        provider_firmware_version (FirmwareVersion)
                                 : Semantic version of meter firmware.
        uptime_ms (int)          : 
    """
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    messages_received: int
    messages_sent: int
    network_connected: bool
    provider_firmware_version: FirmwareVersion  # Semantic version of meter firmware.
    uptime_ms: int
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "messages_received": "messages_received",
            "messages_sent": "messages_sent",
            "network_connected": "network_connected",
            "provider_firmware_version": "provider_firmware_version",
            "uptime_ms": "uptime_ms",
        }
        key_transform_with_dump = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "messages_received": "messages_received",
            "messages_sent": "messages_sent",
            "network_connected": "network_connected",
            "provider_firmware_version": "provider_firmware_version",
            "uptime_ms": "uptime_ms",
        }