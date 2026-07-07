from __future__ import annotations

from dataclasses import dataclass

__all__ = ["StatisticsHistogram"]

@dataclass
class StatisticsHistogram:
    """
    Five-number summary used by network-health events.  Generic shape; what's being measured
    (latency, RSSI, packet count, etc.) depends on the containing event.
    
    Args:
        avg (float)              : 
        count (int)              : 
        last_value (float)       : 
        max_ (float)             : Maps from 'max'
        min_ (float)             : Maps from 'min'
    """
    avg: float
    count: int
    last_value: float
    max_: float  # Maps from 'max'
    min_: float  # Maps from 'min'
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "avg": "avg",
            "count": "count",
            "last_value": "last_value",
            "max": "max_",
            "min": "min_",
        }
        key_transform_with_dump = {
            "avg": "avg",
            "count": "count",
            "last_value": "last_value",
            "max_": "max",
            "min_": "min",
        }