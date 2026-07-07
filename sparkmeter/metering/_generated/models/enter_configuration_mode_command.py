from __future__ import annotations

from dataclasses import dataclass

from .enter_configuration_mode_command_vendor_options import EnterConfigurationModeCommandVendorOptions
from .enter_configuration_mode_params import EnterConfigurationModeParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["EnterConfigurationModeCommand"]

@dataclass
class EnterConfigurationModeCommand:
    """
    Schedule a fleet-wide configuration-mode window.  Reply contract: **two-stage**.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (EnterConfigurationModeParams)
                                 : Schedule a future window during which meters will accept
                                   the new `new_aes_key` on `new_channel`. Outside the
                                   window, meters keep using their previous key/channel.
                                   Used to rotate AES keys or channels across a fleet
                                   without losing contact with any meter.
        vendor_options (EnterConfigurationModeCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: EnterConfigurationModeParams  # Schedule a future window during which meters will accept the new `new_aes_key` on `new_channel`. Outside the window, meters keep using their previous key/channel.  Used to rotate AES keys or channels across a fleet without losing contact with any meter.
    vendor_options: EnterConfigurationModeCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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