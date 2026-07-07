from __future__ import annotations

from dataclasses import dataclass

from .start_firmware_update_command_vendor_options import StartFirmwareUpdateCommandVendorOptions
from .start_firmware_update_params import StartFirmwareUpdateParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["StartFirmwareUpdateCommand"]

@dataclass
class StartFirmwareUpdateCommand:
    """
    Begin a broadcast firmware-update session.  Reply contract: **two-stage**. Sync
    `command_accepted` returns a `session_id` in `result`. Long-running progress is
    observable via `query_firmware_update_status`. Terminal `command_applied` once all
    targeted meters complete; `command_failed` if the session aborts.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (StartFirmwareUpdateParams)
                                 : Begin a firmware-update session.  `target_meters` is the
                                   set of meters to upgrade; null means all registered
                                   meters. `target_firmware_version` is what the meters
                                   should report after upgrade. The image is identified by
                                   `image_id`, which the provider resolves to the actual
                                   binary (vendor-specific convention). For vendors that
                                   need the raw bytes inline, pass them as base64 in
                                   `vendor_options.image_bytes`.
        vendor_options (StartFirmwareUpdateCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: StartFirmwareUpdateParams  # Begin a firmware-update session.  `target_meters` is the set of meters to upgrade; null means all registered meters. `target_firmware_version` is what the meters should report after upgrade. The image is identified by `image_id`, which the provider resolves to the actual binary (vendor-specific convention). For vendors that need the raw bytes inline, pass them as base64 in `vendor_options.image_bytes`.
    vendor_options: StartFirmwareUpdateCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "command_type": "command_type",
            "correlation_id": "correlation_id",
            "params": "params",
            "vendor_options": "vendor_options",
        }
        key_transform_with_dump = {
            "command_type": "command_type",
            "correlation_id": "correlation_id",
            "params": "params",
            "vendor_options": "vendor_options",
        }