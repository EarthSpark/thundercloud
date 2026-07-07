from __future__ import annotations

from dataclasses import dataclass

__all__ = ["HighCapacityMeterConfiguration"]

@dataclass
class HighCapacityMeterConfiguration:
    """
    Settings specific to instrument-transformer-fed (high-capacity) meters.
    
    Args:
        ct_ratio (int)           : 
        echo (int | None)        : Opaque token round-tripped to the meter and echoed back
                                   on `command_applied` so the host can correlate config
                                   rotations.
        reverse_current (bool | None)
                                 : 
    """
    ct_ratio: int
    echo: int | None = 0  # Opaque token round-tripped to the meter and echoed back on `command_applied` so the host can correlate config rotations.
    reverse_current: bool | None = False
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "ct_ratio": "ct_ratio",
            "echo": "echo",
            "reverse_current": "reverse_current",
        }
        key_transform_with_dump = {
            "ct_ratio": "ct_ratio",
            "echo": "echo",
            "reverse_current": "reverse_current",
        }