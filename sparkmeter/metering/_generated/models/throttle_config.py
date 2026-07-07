from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ThrottleConfig"]

@dataclass
class ThrottleConfig:
    """
    Throttle behaviour applied when current/power exceeds limits.  `on_seconds` and
    `off_seconds` describe the duty cycle while throttling; `count_limit` is the number of
    full cycles after which the meter transitions to a protective shutoff.
    
    Args:
        count_limit (int)        : 
        off_seconds (int)        : 
        on_seconds (int)         : 
    """
    count_limit: int
    off_seconds: int
    on_seconds: int
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "count_limit": "count_limit",
            "off_seconds": "off_seconds",
            "on_seconds": "on_seconds",
        }
        key_transform_with_dump = {
            "count_limit": "count_limit",
            "off_seconds": "off_seconds",
            "on_seconds": "on_seconds",
        }