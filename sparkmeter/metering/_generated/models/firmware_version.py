from __future__ import annotations

from dataclasses import dataclass

__all__ = ["FirmwareVersion"]

@dataclass
class FirmwareVersion:
    """
    Semantic version of meter firmware.
    
    Args:
        major (int)              : 
        minor (int)              : 
        patch (int)              : 
    """
    major: int
    minor: int
    patch: int
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "major": "major",
            "minor": "minor",
            "patch": "patch",
        }
        key_transform_with_dump = {
            "major": "major",
            "minor": "minor",
            "patch": "patch",
        }