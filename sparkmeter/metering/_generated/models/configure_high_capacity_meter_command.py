from __future__ import annotations

from dataclasses import dataclass

from .configure_high_capacity_meter_command_vendor_options import ConfigureHighCapacityMeterCommandVendorOptions
from .configure_high_capacity_meter_params import ConfigureHighCapacityMeterParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["ConfigureHighCapacityMeterCommand"]

@dataclass
class ConfigureHighCapacityMeterCommand:
    """
    Configure CT ratio and related parameters on a high-capacity meter.  Reply contract:
    **two-stage** (sync `command_accepted`/`command_rejected`, eventual `command_applied`).
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (ConfigureHighCapacityMeterParams)
                                 : 
        vendor_options (ConfigureHighCapacityMeterCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: ConfigureHighCapacityMeterParams
    vendor_options: ConfigureHighCapacityMeterCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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