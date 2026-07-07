from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ReadMeterMemoryParams"]

@dataclass
class ReadMeterMemoryParams:
    """
    ReadMeterMemoryParams dataclass
    
    Args:
        address (int)            : 
        length (int)             : 
        meter_id (str)           : 
    """
    address: int
    length: int
    meter_id: str
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "address": "address",
            "length": "length",
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "address": "address",
            "length": "length",
            "meter_id": "meter_id",
        }