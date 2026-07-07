from __future__ import annotations

from dataclasses import dataclass

__all__ = ["PhaseReading"]

@dataclass
class PhaseReading:
    """
    Single-phase scalars within a `meter_reading_phased` event.
    
    Args:
        apparent_power_avg_va (float)
                                 : 
        current_avg_amps (float) : 
        current_max_amps (float) : 
        current_min_amps (float) : 
        frequency_hz (float)     : 
        power_factor_avg (float) : 
        true_power_avg_watts (float)
                                 : 
        true_power_inst_watts (float)
                                 : 
        voltage_avg (float)      : 
        voltage_max (float)      : 
        voltage_min (float)      : 
    """
    apparent_power_avg_va: float
    current_avg_amps: float
    current_max_amps: float
    current_min_amps: float
    frequency_hz: float
    power_factor_avg: float
    true_power_avg_watts: float
    true_power_inst_watts: float
    voltage_avg: float
    voltage_max: float
    voltage_min: float
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "apparent_power_avg_va": "apparent_power_avg_va",
            "current_avg_amps": "current_avg_amps",
            "current_max_amps": "current_max_amps",
            "current_min_amps": "current_min_amps",
            "frequency_hz": "frequency_hz",
            "power_factor_avg": "power_factor_avg",
            "true_power_avg_watts": "true_power_avg_watts",
            "true_power_inst_watts": "true_power_inst_watts",
            "voltage_avg": "voltage_avg",
            "voltage_max": "voltage_max",
            "voltage_min": "voltage_min",
        }
        key_transform_with_dump = {
            "apparent_power_avg_va": "apparent_power_avg_va",
            "current_avg_amps": "current_avg_amps",
            "current_max_amps": "current_max_amps",
            "current_min_amps": "current_min_amps",
            "frequency_hz": "frequency_hz",
            "power_factor_avg": "power_factor_avg",
            "true_power_avg_watts": "true_power_avg_watts",
            "true_power_inst_watts": "true_power_inst_watts",
            "voltage_avg": "voltage_avg",
            "voltage_max": "voltage_max",
            "voltage_min": "voltage_min",
        }