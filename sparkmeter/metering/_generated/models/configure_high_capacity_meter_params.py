from __future__ import annotations

from dataclasses import dataclass

from .high_capacity_meter_configuration import HighCapacityMeterConfiguration

__all__ = ["ConfigureHighCapacityMeterParams"]

@dataclass
class ConfigureHighCapacityMeterParams:
    """
    ConfigureHighCapacityMeterParams dataclass
    
    Args:
        configuration (HighCapacityMeterConfiguration)
                                 : Settings specific to instrument-transformer-fed (high-
                                   capacity) meters.
        meter_id (str)           : 
    """
    configuration: HighCapacityMeterConfiguration  # Settings specific to instrument-transformer-fed (high-capacity) meters.
    meter_id: str
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "configuration": "configuration",
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "configuration": "configuration",
            "meter_id": "meter_id",
        }