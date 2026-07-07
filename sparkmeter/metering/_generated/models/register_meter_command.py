from __future__ import annotations

from dataclasses import dataclass

from .register_meter_command_vendor_options import RegisterMeterCommandVendorOptions
from .register_meter_params import RegisterMeterParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["RegisterMeterCommand"]

@dataclass
class RegisterMeterCommand:
    """
    Add a meter.  Reply contract: **single reply**. Possible terminal events:
    `command_accepted`, `command_rejected`.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (RegisterMeterParams)
                                 : Add a meter to the provider's roster.  `meter_type` is a
                                   vendor-defined model code (e.g. `SM5R`, `SMHCE`). Set it
                                   to whatever the vendor's capabilities report supports.
                                   `firmware_version` is optional and seeds capability
                                   detection on vendors that gate features by version.
                                   `initial_balance` and `initial_low_balance` set the
                                   meter's display credit at registration. They have the
                                   same semantics as a subsequent `set_balance` call: cached
                                   at the provider, delivered opportunistically.
                                   `request_phased_readings`, when true on a multi-phase-
                                   capable meter, causes the provider to emit
                                   `meter_reading_phased` events instead of `meter_reading`.
                                   Cannot be flipped after registration: unregister and re-
                                   register to switch.
        vendor_options (RegisterMeterCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: RegisterMeterParams  # Add a meter to the provider's roster.  `meter_type` is a vendor-defined model code (e.g. `SM5R`, `SMHCE`). Set it to whatever the vendor's capabilities report supports. `firmware_version` is optional and seeds capability detection on vendors that gate features by version.  `initial_balance` and `initial_low_balance` set the meter's display credit at registration. They have the same semantics as a subsequent `set_balance` call: cached at the provider, delivered opportunistically.  `request_phased_readings`, when true on a multi-phase-capable meter, causes the provider to emit `meter_reading_phased` events instead of `meter_reading`. Cannot be flipped after registration: unregister and re-register to switch.
    vendor_options: RegisterMeterCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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