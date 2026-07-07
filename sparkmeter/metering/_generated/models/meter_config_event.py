from __future__ import annotations

from dataclasses import dataclass

from .meter_config_event_balance import MeterConfigEventBalance
from .meter_config_event_firmware_version import MeterConfigEventFirmwareVersion
from .meter_configuration import MeterConfiguration
from .meter_state import MeterState
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["MeterConfigEvent"]

@dataclass
class MeterConfigEvent:
    """
    Reply to `query_meter_config`.
    
    Args:
        configuration (MeterConfiguration)
                                 : Limits and behaviour applied to a single meter.
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        meter_id (str)           : 
        state (MeterState)       : Operational state of an electrical meter.  Vendors may
                                   not implement every state; subscribers should treat
                                   unrecognised values as `unknown`.
        balance (MeterConfigEventBalance | None)
                                 : 
        firmware_version (MeterConfigEventFirmwareVersion | None)
                                 : 
        low_balance (bool | None): 
    """
    configuration: MeterConfiguration  # Limits and behaviour applied to a single meter.
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    meter_id: str
    state: MeterState  # Operational state of an electrical meter.  Vendors may not implement every state; subscribers should treat unrecognised values as `unknown`.
    balance: MeterConfigEventBalance | None = None
    firmware_version: MeterConfigEventFirmwareVersion | None = None
    low_balance: bool | None = False
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "balance": "balance",
            "configuration": "configuration",
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "firmware_version": "firmware_version",
            "low_balance": "low_balance",
            "meter_id": "meter_id",
            "state": "state",
        }
        key_transform_with_dump = {
            "balance": "balance",
            "configuration": "configuration",
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "firmware_version": "firmware_version",
            "low_balance": "low_balance",
            "meter_id": "meter_id",
            "state": "state",
        }