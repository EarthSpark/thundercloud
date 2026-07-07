from __future__ import annotations

from dataclasses import dataclass

__all__ = ["WriteMeterRegisterParams"]

@dataclass
class WriteMeterRegisterParams:
    """
    WriteMeterRegisterParams dataclass
    
    Args:
        meter_id (str)           : 
        register_address (int)   : 
        value (int)              : 
    """
    meter_id: str
    register_address: int
    value: int
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "meter_id": "meter_id",
            "register_address": "register_address",
            "value": "value",
        }
        key_transform_with_dump = {
            "meter_id": "meter_id",
            "register_address": "register_address",
            "value": "value",
        }