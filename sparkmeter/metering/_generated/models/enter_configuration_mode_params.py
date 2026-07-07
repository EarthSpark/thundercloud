from __future__ import annotations

from dataclasses import dataclass

__all__ = ["EnterConfigurationModeParams"]

@dataclass
class EnterConfigurationModeParams:
    """
    Schedule a future window during which meters will accept the new `new_aes_key` on
    `new_channel`. Outside the window, meters keep using their previous key/channel.  Used
    to rotate AES keys or channels across a fleet without losing contact with any meter.
    
    Args:
        end_unix_seconds (int)   : 
        new_aes_key (str)        : Raw 16-byte network key.
        new_channel (int)        : 
        start_unix_seconds (int) : 
    """
    end_unix_seconds: int
    new_aes_key: str  # Raw 16-byte network key.
    new_channel: int
    start_unix_seconds: int
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "end_unix_seconds": "end_unix_seconds",
            "new_aes_key": "new_aes_key",
            "new_channel": "new_channel",
            "start_unix_seconds": "start_unix_seconds",
        }
        key_transform_with_dump = {
            "end_unix_seconds": "end_unix_seconds",
            "new_aes_key": "new_aes_key",
            "new_channel": "new_channel",
            "start_unix_seconds": "start_unix_seconds",
        }