from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RfTestParams"]

@dataclass
class RfTestParams:
    """
    RfTestParams dataclass
    
    Args:
        meter_id (str)           : 
        duration_seconds (int | None)
                                 : 
        test_mode (str | None)   : Vendor-defined test mode (e.g. 'carrier', 'prbs').
    """
    meter_id: str
    duration_seconds: int | None = 30
    test_mode: str | None = "carrier"  # Vendor-defined test mode (e.g. 'carrier', 'prbs').
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "duration_seconds": "duration_seconds",
            "meter_id": "meter_id",
            "test_mode": "test_mode",
        }
        key_transform_with_dump = {
            "duration_seconds": "duration_seconds",
            "meter_id": "meter_id",
            "test_mode": "test_mode",
        }