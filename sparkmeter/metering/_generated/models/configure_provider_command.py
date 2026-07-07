from __future__ import annotations

from dataclasses import dataclass

from .configure_provider_command_vendor_options import ConfigureProviderCommandVendorOptions
from .configure_provider_params import ConfigureProviderParams
from .submit_command_v_1_commands_post_request_body_command_type_enum import SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum

__all__ = ["ConfigureProviderCommand"]

@dataclass
class ConfigureProviderCommand:
    """
    Reconfigure the provider's heartbeat and network parameters.  Reply contract: **fire-
    and-forget**. The provider applies the change as soon as it can; no event is emitted to
    confirm. To verify, follow up with `query_provider_status` and inspect the reported
    configuration.
    
    Args:
        command_type (SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum)
                                 : 
        correlation_id (str)     : Client-supplied id used to correlate every event the
                                   command produces. Must be unique within the client's
                                   outstanding work.
        params (ConfigureProviderParams)
                                 : Provider-level configuration.  `heartbeat_seconds` is the
                                   interval at which the provider polls its meters and emits
                                   aggregated `heartbeat_summary` events. The valid range
                                   and any divisibility constraints are vendor-specific (see
                                   the vendor's capability documentation).  Network
                                   credentials (e.g., AES key, radio channel) are vendor-
                                   specific and pass through `vendor_options`.
        vendor_options (ConfigureProviderCommandVendorOptions | None)
                                 : Vendor-specific extension data. The generic wire ignores
                                   this; the vendor's translator may consume it. See the
                                   vendor's capability documentation for accepted keys.
    """
    command_type: SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum
    correlation_id: str  # Client-supplied id used to correlate every event the command produces. Must be unique within the client's outstanding work.
    params: ConfigureProviderParams  # Provider-level configuration.  `heartbeat_seconds` is the interval at which the provider polls its meters and emits aggregated `heartbeat_summary` events. The valid range and any divisibility constraints are vendor-specific (see the vendor's capability documentation).  Network credentials (e.g., AES key, radio channel) are vendor-specific and pass through `vendor_options`.
    vendor_options: ConfigureProviderCommandVendorOptions | None = None  # Vendor-specific extension data. The generic wire ignores this; the vendor's translator may consume it. See the vendor's capability documentation for accepted keys.
    
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