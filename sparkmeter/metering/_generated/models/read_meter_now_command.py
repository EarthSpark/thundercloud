from __future__ import annotations

from dataclasses import dataclass

from .read_meter_now_command_vendor_options import ReadMeterNowCommandVendorOptions
from .read_meter_now_params import ReadMeterNowParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["ReadMeterNowCommand"]

@dataclass
class ReadMeterNowCommand:
    """
    Request a single-shot instantaneous reading.  Distinct from heartbeat-aligned
    `meter_reading` push events; this command synchronously asks for the current values.
    Reply contract: **query reply**. Terminal event: `meter_instant_reading`.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (ReadMeterNowParams)
                                 : 
        vendor_options (ReadMeterNowCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: ReadMeterNowParams
    vendor_options: ReadMeterNowCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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