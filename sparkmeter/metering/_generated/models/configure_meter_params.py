from __future__ import annotations

from dataclasses import dataclass

from .meter_behavior_command import MeterBehaviorCommand
from .meter_configuration import MeterConfiguration

__all__ = ["ConfigureMeterParams"]

@dataclass
class ConfigureMeterParams:
    """
    Configure a meter's behaviour and optionally send a one-shot verb.  `behavior` is one of
    `MeterBehaviorCommand`; pass `none` to apply only the `configuration` without sending a
    verb. The `configuration` fields are required even when sending only a verb because most
    vendors round-trip the full config on every set-config message.
    
    Args:
        configuration (MeterConfiguration)
                                 : Limits and behaviour applied to a single meter.
        meter_id (str)           : 
        behavior (MeterBehaviorCommand | None)
                                 : One-shot verb to send to a meter as part of
                                   `configure_meter`.  Not every vendor supports every verb;
                                   check capabilities first. Calibrate verbs in particular
                                   are uncommon outside metering ICs that expose live
                                   calibration.
    """
    configuration: MeterConfiguration  # Limits and behaviour applied to a single meter.
    meter_id: str
    behavior: MeterBehaviorCommand | None = None  # One-shot verb to send to a meter as part of `configure_meter`.  Not every vendor supports every verb; check capabilities first. Calibrate verbs in particular are uncommon outside metering ICs that expose live calibration.
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "behavior": "behavior",
            "configuration": "configuration",
            "meter_id": "meter_id",
        }
        key_transform_with_dump = {
            "behavior": "behavior",
            "configuration": "configuration",
            "meter_id": "meter_id",
        }