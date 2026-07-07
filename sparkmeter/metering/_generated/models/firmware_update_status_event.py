from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .firmware_update_session_status import FirmwareUpdateSessionStatus
from .firmware_update_status_event_failed_meters import FirmwareUpdateStatusEventFailedMeters
from .firmware_update_status_event_progress_percent import FirmwareUpdateStatusEventProgressPercent
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["FirmwareUpdateStatusEvent"]

@dataclass
class FirmwareUpdateStatusEvent:
    """
    Reply to `query_firmware_update_status`. One per active session.
    
    Args:
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        session_id (str)         : 
        status (FirmwareUpdateSessionStatus)
                                 : 
        completed_meters (List[str] | None)
                                 : 
        failed_meters (FirmwareUpdateStatusEventFailedMeters | None)
                                 : Mapping of meter_id → reason for meters that failed mid-
                                   session.
        pending_meters (List[str] | None)
                                 : 
        progress_percent (FirmwareUpdateStatusEventProgressPercent | None)
                                 : 
    """
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    session_id: str
    status: FirmwareUpdateSessionStatus
    completed_meters: List[str] | None = field(default_factory=list)
    failed_meters: FirmwareUpdateStatusEventFailedMeters | None = None  # Mapping of meter_id → reason for meters that failed mid-session.
    pending_meters: List[str] | None = field(default_factory=list)
    progress_percent: FirmwareUpdateStatusEventProgressPercent | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "completed_meters": "completed_meters",
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "failed_meters": "failed_meters",
            "pending_meters": "pending_meters",
            "progress_percent": "progress_percent",
            "session_id": "session_id",
            "status": "status",
        }
        key_transform_with_dump = {
            "completed_meters": "completed_meters",
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "failed_meters": "failed_meters",
            "pending_meters": "pending_meters",
            "progress_percent": "progress_percent",
            "session_id": "session_id",
            "status": "status",
        }