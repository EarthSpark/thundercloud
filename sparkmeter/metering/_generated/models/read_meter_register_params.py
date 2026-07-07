from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ReadMeterRegisterParams"]

@dataclass
class ReadMeterRegisterParams:
    """
    ReadMeterRegisterParams dataclass
    
    Args:
        meter_id (str)           : 
        register_address (int)   : 
    """
    meter_id: str
    register_address: int
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "meter_id": "meter_id",
            "register_address": "register_address",
        }
        key_transform_with_dump = {
            "meter_id": "meter_id",
            "register_address": "register_address",
        }