from __future__ import annotations

from dataclasses import dataclass

from .throttle_config import ThrottleConfig

__all__ = ["MeterConfiguration"]

@dataclass
class MeterConfiguration:
    """
    Limits and behaviour applied to a single meter.
    
    Args:
        current_limit_amps (float): 
        power_limit_watts (float): 
        throttle (ThrottleConfig): Throttle behaviour applied when current/power exceeds
                                   limits.  `on_seconds` and `off_seconds` describe the duty
                                   cycle while throttling; `count_limit` is the number of
                                   full cycles after which the meter transitions to a
                                   protective shutoff.
        startup_delay_seconds (int | None)
                                 : 
    """
    current_limit_amps: float
    power_limit_watts: float
    throttle: ThrottleConfig  # Throttle behaviour applied when current/power exceeds limits.  `on_seconds` and `off_seconds` describe the duty cycle while throttling; `count_limit` is the number of full cycles after which the meter transitions to a protective shutoff.
    startup_delay_seconds: int | None = 0
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "current_limit_amps": "current_limit_amps",
            "power_limit_watts": "power_limit_watts",
            "startup_delay_seconds": "startup_delay_seconds",
            "throttle": "throttle",
        }
        key_transform_with_dump = {
            "current_limit_amps": "current_limit_amps",
            "power_limit_watts": "power_limit_watts",
            "startup_delay_seconds": "startup_delay_seconds",
            "throttle": "throttle",
        }