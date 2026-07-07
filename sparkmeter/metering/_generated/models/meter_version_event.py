from __future__ import annotations

from dataclasses import dataclass

from .firmware_version import FirmwareVersion
from .meter_version_event_bootloader_version import MeterVersionEventBootloaderVersion
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["MeterVersionEvent"]

@dataclass
class MeterVersionEvent:
    """
    Reply to `query_meter_version`.
    
    Args:
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        firmware_version (FirmwareVersion)
                                 : Semantic version of meter firmware.
        meter_id (str)           : 
        bootloader_version (MeterVersionEventBootloaderVersion | None)
                                 : 
    """
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    firmware_version: FirmwareVersion  # Semantic version of meter firmware.
    meter_id: str
    bootloader_version: MeterVersionEventBootloaderVersion | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "bootloader_version": "bootloader_version",
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "firmware_version": "firmware_version",
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "bootloader_version": "bootloader_version",
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "firmware_version": "firmware_version",
            "meter_id": "meter_id",
        }