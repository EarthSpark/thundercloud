from __future__ import annotations

from dataclasses import dataclass

from .configure_meter_command_vendor_options import ConfigureMeterCommandVendorOptions
from .configure_meter_params import ConfigureMeterParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["ConfigureMeterCommand"]

@dataclass
class ConfigureMeterCommand:
    """
    Apply a configuration and/or behaviour verb to a meter.  Reply contract: **two-stage**.
    Synchronous: `command_accepted` (queued for delivery) or `command_rejected` (validation
    failed at the provider). Eventual: `command_applied` (meter acknowledged),
    `command_failed` (provider gave up), or `command_timed_out`.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (ConfigureMeterParams)
                                 : Configure a meter's behaviour and optionally send a one-
                                   shot verb.  `behavior` is one of `MeterBehaviorCommand`;
                                   pass `none` to apply only the `configuration` without
                                   sending a verb. The `configuration` fields are required
                                   even when sending only a verb because most vendors round-
                                   trip the full config on every set-config message.
        vendor_options (ConfigureMeterCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: ConfigureMeterParams  # Configure a meter's behaviour and optionally send a one-shot verb.  `behavior` is one of `MeterBehaviorCommand`; pass `none` to apply only the `configuration` without sending a verb. The `configuration` fields are required even when sending only a verb because most vendors round-trip the full config on every set-config message.
    vendor_options: ConfigureMeterCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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