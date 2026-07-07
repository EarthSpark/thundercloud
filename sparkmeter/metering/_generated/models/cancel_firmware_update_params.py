from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CancelFirmwareUpdateParams"]

@dataclass
class CancelFirmwareUpdateParams:
    """
    CancelFirmwareUpdateParams dataclass
    
    Args:
        session_id (str)         : 
    """
    session_id: str
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "session_id": "session_id",
        }
        key_transform_with_dump = {
            "session_id": "session_id",
        }