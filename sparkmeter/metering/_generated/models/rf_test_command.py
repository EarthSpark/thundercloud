from __future__ import annotations

from dataclasses import dataclass

from .rf_test_command_vendor_options import RfTestCommandVendorOptions
from .rf_test_params import RfTestParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["RfTestCommand"]

@dataclass
class RfTestCommand:
    """
    Run an RF test against a meter.  Reply contract: **query reply**. Terminal event:
    `rf_test_result`.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (RfTestParams)    : 
        vendor_options (RfTestCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: RfTestParams
    vendor_options: RfTestCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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