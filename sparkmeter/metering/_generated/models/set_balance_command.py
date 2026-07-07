from __future__ import annotations

from dataclasses import dataclass

from .set_balance_command_vendor_options import SetBalanceCommandVendorOptions
from .set_balance_params import SetBalanceParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["SetBalanceCommand"]

@dataclass
class SetBalanceCommand:
    """
    Update the credit value displayed at the meter.  Reply contract: **cache reply**. The
    provider caches the value and pushes it to the meter opportunistically (typically piggy-
    backed on the next radio round-trip). Delivery is NOT confirmed by this command. To
    verify a meter actually received an update, query the meter via `query_meter_config` and
    inspect the echoed balance.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (SetBalanceParams): Push display credit to be shown to the customer at the
                                   meter.  The `balance` is a currency value with arbitrary
                                   precision. The `low_balance` flag is an out-of-band
                                   signal independent of the balance value (vendors that
                                   can't render arbitrary balances may still use this flag
                                   to drive a low-credit indicator).
        vendor_options (SetBalanceCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: SetBalanceParams  # Push display credit to be shown to the customer at the meter.  The `balance` is a currency value with arbitrary precision. The `low_balance` flag is an out-of-band signal independent of the balance value (vendors that can't render arbitrary balances may still use this flag to drive a low-credit indicator).
    vendor_options: SetBalanceCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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