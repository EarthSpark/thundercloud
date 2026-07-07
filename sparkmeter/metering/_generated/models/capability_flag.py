from __future__ import annotations

from enum import Enum, unique

__all__ = ["CapabilityFlag"]

@unique
class CapabilityFlag(str, Enum):
    """
    Optional feature flags providers may declare.
    
    Args:
        phased_readings (str)    : Value for PHASED_READINGS
        balance_push (str)       : Value for BALANCE_PUSH
        network_health (str)     : Value for NETWORK_HEALTH
        behavior_reboot (str)    : Value for BEHAVIOR_REBOOT
        behavior_calibrate (str) : Value for BEHAVIOR_CALIBRATE
        behavior_unprovisioned (str)
                                 : Value for BEHAVIOR_UNPROVISIONED
        ping_meter (str)         : Value for PING_METER
        meter_neighbors (str)    : Value for METER_NEIGHBORS
        meter_config_query (str) : Value for METER_CONFIG_QUERY
        meter_version_query (str): Value for METER_VERSION_QUERY
        instant_reading (str)    : Value for INSTANT_READING
        meter_errors (str)       : Value for METER_ERRORS
        associate (str)          : Value for ASSOCIATE
        high_capacity_meter_config (str)
                                 : Value for HIGH_CAPACITY_METER_CONFIG
        firmware_update (str)    : Value for FIRMWARE_UPDATE
        configuration_mode (str) : Value for CONFIGURATION_MODE
        rf_test (str)            : Value for RF_TEST
        meter_memory (str)       : Value for METER_MEMORY
        meter_registers (str)    : Value for METER_REGISTERS
    """
    PHASED_READINGS = "phased_readings"
    BALANCE_PUSH = "balance_push"
    NETWORK_HEALTH = "network_health"
    BEHAVIOR_REBOOT = "behavior_reboot"
    BEHAVIOR_CALIBRATE = "behavior_calibrate"
    BEHAVIOR_UNPROVISIONED = "behavior_unprovisioned"
    PING_METER = "ping_meter"
    METER_NEIGHBORS = "meter_neighbors"
    METER_CONFIG_QUERY = "meter_config_query"
    METER_VERSION_QUERY = "meter_version_query"
    INSTANT_READING = "instant_reading"
    METER_ERRORS = "meter_errors"
    ASSOCIATE = "associate"
    HIGH_CAPACITY_METER_CONFIG = "high_capacity_meter_config"
    FIRMWARE_UPDATE = "firmware_update"
    CONFIGURATION_MODE = "configuration_mode"
    RF_TEST = "rf_test"
    METER_MEMORY = "meter_memory"
    METER_REGISTERS = "meter_registers"