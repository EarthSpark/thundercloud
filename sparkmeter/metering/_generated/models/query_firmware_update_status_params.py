from __future__ import annotations

from dataclasses import dataclass

from .query_firmware_update_status_params_session_id import QueryFirmwareUpdateStatusParamsSessionId

__all__ = ["QueryFirmwareUpdateStatusParams"]

@dataclass
class QueryFirmwareUpdateStatusParams:
    """
    QueryFirmwareUpdateStatusParams dataclass
    
    Args:
        session_id (QueryFirmwareUpdateStatusParamsSessionId | None)
                                 : Specific session id; omit for the status of all active
                                   sessions.
    """
    session_id: QueryFirmwareUpdateStatusParamsSessionId | None = None  # Specific session id; omit for the status of all active sessions.
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "session_id": "session_id",
        }
        key_transform_with_dump = {
            "session_id": "session_id",
        }