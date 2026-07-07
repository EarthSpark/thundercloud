from __future__ import annotations

from enum import Enum, unique

__all__ = ["SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum"]

@unique
class SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum(str, Enum):
    """
    Discriminator enum for SubmitCommandV1CommandsPostRequestBody union types.
    
    Args:
        register_meter (str)     : Value for REGISTER_METER
        unregister_meter (str)   : Value for UNREGISTER_METER
        configure_meter (str)    : Value for CONFIGURE_METER
        set_balance (str)        : Value for SET_BALANCE
        configure_provider (str) : Value for CONFIGURE_PROVIDER
        query_provider_status (str)
                                 : Value for QUERY_PROVIDER_STATUS
        query_network_health (str): Value for QUERY_NETWORK_HEALTH
        query_capabilities (str) : Value for QUERY_CAPABILITIES
        ping_meter (str)         : Value for PING_METER
        query_meter_neighbors (str)
                                 : Value for QUERY_METER_NEIGHBORS
        query_meter_config (str) : Value for QUERY_METER_CONFIG
        query_meter_version (str): Value for QUERY_METER_VERSION
        read_meter_now (str)     : Value for READ_METER_NOW
        query_meter_errors (str) : Value for QUERY_METER_ERRORS
        reset_meter_errors (str) : Value for RESET_METER_ERRORS
        associate_meter (str)    : Value for ASSOCIATE_METER
        configure_high_capacity_meter (str)
                                 : Value for CONFIGURE_HIGH_CAPACITY_METER
        start_firmware_update (str)
                                 : Value for START_FIRMWARE_UPDATE
        query_firmware_update_status (str)
                                 : Value for QUERY_FIRMWARE_UPDATE_STATUS
        cancel_firmware_update (str)
                                 : Value for CANCEL_FIRMWARE_UPDATE
        enter_configuration_mode (str)
                                 : Value for ENTER_CONFIGURATION_MODE
        rf_test (str)            : Value for RF_TEST
        read_meter_memory (str)  : Value for READ_METER_MEMORY
        read_meter_register (str): Value for READ_METER_REGISTER
        write_meter_register (str): Value for WRITE_METER_REGISTER
    """
    REGISTER_METER = "register_meter"
    UNREGISTER_METER = "unregister_meter"
    CONFIGURE_METER = "configure_meter"
    SET_BALANCE = "set_balance"
    CONFIGURE_PROVIDER = "configure_provider"
    QUERY_PROVIDER_STATUS = "query_provider_status"
    QUERY_NETWORK_HEALTH = "query_network_health"
    QUERY_CAPABILITIES = "query_capabilities"
    PING_METER = "ping_meter"
    QUERY_METER_NEIGHBORS = "query_meter_neighbors"
    QUERY_METER_CONFIG = "query_meter_config"
    QUERY_METER_VERSION = "query_meter_version"
    READ_METER_NOW = "read_meter_now"
    QUERY_METER_ERRORS = "query_meter_errors"
    RESET_METER_ERRORS = "reset_meter_errors"
    ASSOCIATE_METER = "associate_meter"
    CONFIGURE_HIGH_CAPACITY_METER = "configure_high_capacity_meter"
    START_FIRMWARE_UPDATE = "start_firmware_update"
    QUERY_FIRMWARE_UPDATE_STATUS = "query_firmware_update_status"
    CANCEL_FIRMWARE_UPDATE = "cancel_firmware_update"
    ENTER_CONFIGURATION_MODE = "enter_configuration_mode"
    RF_TEST = "rf_test"
    READ_METER_MEMORY = "read_meter_memory"
    READ_METER_REGISTER = "read_meter_register"
    WRITE_METER_REGISTER = "write_meter_register"