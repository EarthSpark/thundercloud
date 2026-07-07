from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ReadMeterNowParams"]

@dataclass
class ReadMeterNowParams:
    """
    ReadMeterNowParams dataclass
    
    Args:
        meter_id (str)           : 
    """
    meter_id: str
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "meter_id": "meter_id",
        }