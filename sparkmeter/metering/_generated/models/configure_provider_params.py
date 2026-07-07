from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ConfigureProviderParams"]

@dataclass
class ConfigureProviderParams:
    """
    Provider-level configuration.  `heartbeat_seconds` is the interval at which the provider
    polls its meters and emits aggregated `heartbeat_summary` events. The valid range and
    any divisibility constraints are vendor-specific (see the vendor's capability
    documentation).  Network credentials (e.g., AES key, radio channel) are vendor-specific
    and pass through `vendor_options`.
    
    Args:
        heartbeat_seconds (int)  : 
    """
    heartbeat_seconds: int
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "heartbeat_seconds": "heartbeat_seconds",
        }
        key_transform_with_dump = {
            "heartbeat_seconds": "heartbeat_seconds",
        }