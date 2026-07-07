from __future__ import annotations

from dataclasses import dataclass

from .read_meter_memory_command_vendor_options import ReadMeterMemoryCommandVendorOptions
from .read_meter_memory_params import ReadMeterMemoryParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["ReadMeterMemoryCommand"]

@dataclass
class ReadMeterMemoryCommand:
    """
    Read a span of meter memory (debug primitive).  Address layout is vendor-specific.
    Length bounded by the underlying radio packet size; large reads are issued as multiple
    commands.  Reply contract: **query reply**. Terminal event: `meter_memory`.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (ReadMeterMemoryParams)
                                 : 
        vendor_options (ReadMeterMemoryCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: ReadMeterMemoryParams
    vendor_options: ReadMeterMemoryCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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