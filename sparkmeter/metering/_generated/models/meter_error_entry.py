from __future__ import annotations

from dataclasses import dataclass

from .meter_error_entry_description import MeterErrorEntryDescription
from .meter_error_entry_location import MeterErrorEntryLocation
from .meter_error_entry_timestamp_unix_seconds import MeterErrorEntryTimestampUnixSeconds

__all__ = ["MeterErrorEntry"]

@dataclass
class MeterErrorEntry:
    """
    MeterErrorEntry dataclass
    
    Args:
        code (str)               : Vendor-specific error code, stringified.
        description (MeterErrorEntryDescription | None)
                                 : 
        location (MeterErrorEntryLocation | None)
                                 : Vendor-specific source location (e.g. file:line).
        timestamp_unix_seconds (MeterErrorEntryTimestampUnixSeconds | None)
                                 : 
    """
    code: str  # Vendor-specific error code, stringified.
    description: MeterErrorEntryDescription | None = None
    location: MeterErrorEntryLocation | None = None  # Vendor-specific source location (e.g. file:line).
    timestamp_unix_seconds: MeterErrorEntryTimestampUnixSeconds | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "code": "code",
            "description": "description",
            "location": "location",
            "timestamp_unix_seconds": "timestamp_unix_seconds",
        }
        key_transform_with_dump = {
            "code": "code",
            "description": "description",
            "location": "location",
            "timestamp_unix_seconds": "timestamp_unix_seconds",
        }