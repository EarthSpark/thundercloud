from __future__ import annotations

from dataclasses import dataclass

from .associate_meter_command_vendor_options import AssociateMeterCommandVendorOptions
from .associate_meter_params import AssociateMeterParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["AssociateMeterCommand"]

@dataclass
class AssociateMeterCommand:
    """
    Onboard a physical meter onto the network.  Reply contract: **two-stage**.
    Acknowledgement comes back via `command_applied` once the meter has accepted the new
    identity.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (AssociateMeterParams)
                                 : Onboard a physical meter onto the network.  Distinct from
                                   `register_meter`, which adds a meter to the provider's
                                   roster. `associate_meter` is the over-the-air operation
                                   that gives a previously-unprovisioned meter its network
                                   identity (MAC, channel, AES key).  All three optional
                                   fields target the meter's persistent network
                                   configuration. Provide whichever the operator wants to
                                   set.
        vendor_options (AssociateMeterCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: AssociateMeterParams  # Onboard a physical meter onto the network.  Distinct from `register_meter`, which adds a meter to the provider's roster. `associate_meter` is the over-the-air operation that gives a previously-unprovisioned meter its network identity (MAC, channel, AES key).  All three optional fields target the meter's persistent network configuration. Provide whichever the operator wants to set.
    vendor_options: AssociateMeterCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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