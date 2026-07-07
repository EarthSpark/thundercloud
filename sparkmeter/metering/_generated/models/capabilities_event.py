from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .capabilities_event_vendor_capabilities import CapabilitiesEventVendorCapabilities
from .capability_flag import CapabilityFlag
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["CapabilitiesEvent"]

@dataclass
class CapabilitiesEvent:
    """
    Reply to `query_capabilities`.  `commands` lists which `command_type` values the
    provider supports; `features` lists optional feature flags. Vendor-specific capabilities
    are returned as opaque strings under `vendor_capabilities`.
    
    Args:
        commands (List[str])     : 
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        features (List[CapabilityFlag])
                                 : 
        meter_types (List[str] | None)
                                 : Vendor-recognised `meter_type` values for
                                   `register_meter`.
        vendor_capabilities (CapabilitiesEventVendorCapabilities | None)
                                 : 
    """
    commands: List[str]
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    features: List[CapabilityFlag]
    meter_types: List[str] | None = field(default_factory=list)  # Vendor-recognised `meter_type` values for `register_meter`.
    vendor_capabilities: CapabilitiesEventVendorCapabilities | None = None
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "commands": "commands",
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "features": "features",
            "meter_types": "meter_types",
            "vendor_capabilities": "vendor_capabilities",
        }
        key_transform_with_dump = {
            "commands": "commands",
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "features": "features",
            "meter_types": "meter_types",
            "vendor_capabilities": "vendor_capabilities",
        }