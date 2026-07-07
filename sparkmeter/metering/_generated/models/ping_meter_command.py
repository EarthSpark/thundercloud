from __future__ import annotations

from dataclasses import dataclass

from .ping_meter_command_vendor_options import PingMeterCommandVendorOptions
from .ping_meter_params import PingMeterParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["PingMeterCommand"]

@dataclass
class PingMeterCommand:
    """
    Send a per-meter ping over the radio.  Reply contract: **two-stage**. `command_accepted`
    once queued; `command_applied` carries vendor-supplied timing and signal info in
    `result` (typically `rssi_dbm`, `round_trip_ms`). `command_failed` if the meter doesn't
    respond.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (PingMeterParams) : 
        vendor_options (PingMeterCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: PingMeterParams
    vendor_options: PingMeterCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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