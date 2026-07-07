from __future__ import annotations

from dataclasses import dataclass

from .firmware_version import FirmwareVersion
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["MeterFirmwareChangedEvent"]

@dataclass
class MeterFirmwareChangedEvent:
    """
    Provider observed a meter's firmware version, first time or changed.
    
    Args:
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        firmware_version (FirmwareVersion)
                                 : Semantic version of meter firmware.
        meter_id (str)           : 
    """
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    firmware_version: FirmwareVersion  # Semantic version of meter firmware.
    meter_id: str
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "event_id": "event_id",
            "event_type": "event_type",
            "firmware_version": "firmware_version",
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "event_id": "event_id",
            "event_type": "event_type",
            "firmware_version": "firmware_version",
            "meter_id": "meter_id",
        }