from __future__ import annotations

from dataclasses import dataclass

from .firmware_version import FirmwareVersion
from .start_firmware_update_params_target_meters import StartFirmwareUpdateParamsTargetMeters

__all__ = ["StartFirmwareUpdateParams"]

@dataclass
class StartFirmwareUpdateParams:
    """
    Begin a firmware-update session.  `target_meters` is the set of meters to upgrade; null
    means all registered meters. `target_firmware_version` is what the meters should report
    after upgrade. The image is identified by `image_id`, which the provider resolves to the
    actual binary (vendor-specific convention). For vendors that need the raw bytes inline,
    pass them as base64 in `vendor_options.image_bytes`.
    
    Args:
        image_id (str)           : 
        target_firmware_version (FirmwareVersion)
                                 : Semantic version of meter firmware.
        target_meters (StartFirmwareUpdateParamsTargetMeters | None)
                                 : 
    """
    image_id: str
    target_firmware_version: FirmwareVersion  # Semantic version of meter firmware.
    target_meters: StartFirmwareUpdateParamsTargetMeters | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "image_id": "image_id",
            "target_firmware_version": "target_firmware_version",
            "target_meters": "target_meters",
        }
        key_transform_with_dump = {
            "image_id": "image_id",
            "target_firmware_version": "target_firmware_version",
            "target_meters": "target_meters",
        }