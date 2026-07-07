from __future__ import annotations

from dataclasses import dataclass

from .rf_test_result_event_rssi_dbm import RfTestResultEventRssiDbm
from .stream_events_v_1_events_get_200_response_event_type_enum import StreamEventsV1EventsGet200ResponseEventTypeEnum

__all__ = ["RfTestResultEvent"]

@dataclass
class RfTestResultEvent:
    """
    Reply to `rf_test`.
    
    Args:
        correlation_id (str)     : 
        event_id (int)           : Monotonically increasing per-server event id. Use as the
                                   SSE `Last-Event-ID` for resuming after a disconnect.
        event_type (StreamEventsV1EventsGet200ResponseEventTypeEnum)
                                 : 
        meter_id (str)           : 
        test_mode (str)          : 
        rssi_dbm (RfTestResultEventRssiDbm | None)
                                 : 
        samples_expected (int | None)
                                 : 
        samples_received (int | None)
                                 : 
    """
    correlation_id: str
    event_id: int  # Monotonically increasing per-server event id. Use as the SSE `Last-Event-ID` for resuming after a disconnect.
    event_type: StreamEventsV1EventsGet200ResponseEventTypeEnum
    meter_id: str
    test_mode: str
    rssi_dbm: RfTestResultEventRssiDbm | None = None
    samples_expected: int | None = 0
    samples_received: int | None = 0
    
    class Meta:
        """Configure field name mapping for JSON conversion."""
        key_transform_with_load = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
            "rssi_dbm": "rssi_dbm",
            "samples_expected": "samples_expected",
            "samples_received": "samples_received",
            "test_mode": "test_mode",
        }
        key_transform_with_dump = {
            "correlation_id": "correlation_id",
            "event_id": "event_id",
            "event_type": "event_type",
            "meter_id": "meter_id",
            "rssi_dbm": "rssi_dbm",
            "samples_expected": "samples_expected",
            "samples_received": "samples_received",
            "test_mode": "test_mode",
        }