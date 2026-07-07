from __future__ import annotations

from enum import Enum, unique

__all__ = ["StreamEventsV1EventsGet200ResponseEventTypeEnum"]

@unique
class StreamEventsV1EventsGet200ResponseEventTypeEnum(str, Enum):
    """
    Discriminator enum for StreamEventsV1EventsGet200Response union types.
    
    Args:
        command_accepted (str)   : Value for COMMAND_ACCEPTED
        command_rejected (str)   : Value for COMMAND_REJECTED
        command_applied (str)    : Value for COMMAND_APPLIED
        command_failed (str)     : Value for COMMAND_FAILED
        command_timed_out (str)  : Value for COMMAND_TIMED_OUT
        command_cached (str)     : Value for COMMAND_CACHED
        meter_reading (str)      : Value for METER_READING
        meter_reading_phased (str): Value for METER_READING_PHASED
        meter_firmware_changed (str)
                                 : Value for METER_FIRMWARE_CHANGED
        heartbeat_summary (str)  : Value for HEARTBEAT_SUMMARY
        log (str)                : Value for LOG
        provider_status (str)    : Value for PROVIDER_STATUS
        network_health (str)     : Value for NETWORK_HEALTH
        capabilities (str)       : Value for CAPABILITIES
        meter_neighbors (str)    : Value for METER_NEIGHBORS
        meter_config (str)       : Value for METER_CONFIG
        meter_version (str)      : Value for METER_VERSION
        meter_instant_reading (str)
                                 : Value for METER_INSTANT_READING
        meter_errors (str)       : Value for METER_ERRORS
        firmware_update_status (str)
                                 : Value for FIRMWARE_UPDATE_STATUS
        rf_test_result (str)     : Value for RF_TEST_RESULT
        meter_memory (str)       : Value for METER_MEMORY
        meter_register (str)     : Value for METER_REGISTER
    """
    COMMAND_ACCEPTED = "command_accepted"
    COMMAND_REJECTED = "command_rejected"
    COMMAND_APPLIED = "command_applied"
    COMMAND_FAILED = "command_failed"
    COMMAND_TIMED_OUT = "command_timed_out"
    COMMAND_CACHED = "command_cached"
    METER_READING = "meter_reading"
    METER_READING_PHASED = "meter_reading_phased"
    METER_FIRMWARE_CHANGED = "meter_firmware_changed"
    HEARTBEAT_SUMMARY = "heartbeat_summary"
    LOG = "log"
    PROVIDER_STATUS = "provider_status"
    NETWORK_HEALTH = "network_health"
    CAPABILITIES = "capabilities"
    METER_NEIGHBORS = "meter_neighbors"
    METER_CONFIG = "meter_config"
    METER_VERSION = "meter_version"
    METER_INSTANT_READING = "meter_instant_reading"
    METER_ERRORS = "meter_errors"
    FIRMWARE_UPDATE_STATUS = "firmware_update_status"
    RF_TEST_RESULT = "rf_test_result"
    METER_MEMORY = "meter_memory"
    METER_REGISTER = "meter_register"