from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, TypeAlias, Union

from .associate_meter_command import AssociateMeterCommand
from .cancel_firmware_update_command import CancelFirmwareUpdateCommand
from .configure_high_capacity_meter_command import ConfigureHighCapacityMeterCommand
from .configure_meter_command import ConfigureMeterCommand
from .configure_provider_command import ConfigureProviderCommand
from .enter_configuration_mode_command import EnterConfigurationModeCommand
from .ping_meter_command import PingMeterCommand
from .query_capabilities_command import QueryCapabilitiesCommand
from .query_firmware_update_status_command import QueryFirmwareUpdateStatusCommand
from .query_meter_config_command import QueryMeterConfigCommand
from .query_meter_errors_command import QueryMeterErrorsCommand
from .query_meter_neighbors_command import QueryMeterNeighborsCommand
from .query_meter_version_command import QueryMeterVersionCommand
from .query_network_health_command import QueryNetworkHealthCommand
from .query_provider_status_command import QueryProviderStatusCommand
from .read_meter_memory_command import ReadMeterMemoryCommand
from .read_meter_now_command import ReadMeterNowCommand
from .read_meter_register_command import ReadMeterRegisterCommand
from .register_meter_command import RegisterMeterCommand
from .reset_meter_errors_command import ResetMeterErrorsCommand
from .rf_test_command import RfTestCommand
from .set_balance_command import SetBalanceCommand
from .start_firmware_update_command import StartFirmwareUpdateCommand
from .unregister_meter_command import UnregisterMeterCommand
from .write_meter_register_command import WriteMeterRegisterCommand

from .associate_meter_command import AssociateMeterCommand
from .cancel_firmware_update_command import CancelFirmwareUpdateCommand
from .configure_high_capacity_meter_command import ConfigureHighCapacityMeterCommand
from .configure_meter_command import ConfigureMeterCommand
from .configure_provider_command import ConfigureProviderCommand
from .enter_configuration_mode_command import EnterConfigurationModeCommand
from .ping_meter_command import PingMeterCommand
from .query_capabilities_command import QueryCapabilitiesCommand
from .query_firmware_update_status_command import QueryFirmwareUpdateStatusCommand
from .query_meter_config_command import QueryMeterConfigCommand
from .query_meter_errors_command import QueryMeterErrorsCommand
from .query_meter_neighbors_command import QueryMeterNeighborsCommand
from .query_meter_version_command import QueryMeterVersionCommand
from .query_network_health_command import QueryNetworkHealthCommand
from .query_provider_status_command import QueryProviderStatusCommand
from .read_meter_memory_command import ReadMeterMemoryCommand
from .read_meter_now_command import ReadMeterNowCommand
from .read_meter_register_command import ReadMeterRegisterCommand
from .register_meter_command import RegisterMeterCommand
from .reset_meter_errors_command import ResetMeterErrorsCommand
from .rf_test_command import RfTestCommand
from .set_balance_command import SetBalanceCommand
from .start_firmware_update_command import StartFirmwareUpdateCommand
from .unregister_meter_command import UnregisterMeterCommand
from .write_meter_register_command import WriteMeterRegisterCommand

__all__ = ['SubmitCommandV1CommandsPostRequestBody', 'SubmitCommandV1CommandsPostRequestBodyDiscriminator']

@dataclass(frozen=True)
class SubmitCommandV1CommandsPostRequestBodyDiscriminator:
    """Discriminator metadata for SubmitCommandV1CommandsPostRequestBody union."""

    property_name: str = "command_type"
    """The discriminator property name"""

    # Mapping stored as tuple for frozen dataclass compatibility
    _mapping_data: tuple[tuple[str, str], ...] = (
        ("register_meter", "RegisterMeterCommand"),
        ("unregister_meter", "UnregisterMeterCommand"),
        ("configure_meter", "ConfigureMeterCommand"),
        ("set_balance", "SetBalanceCommand"),
        ("configure_provider", "ConfigureProviderCommand"),
        ("query_provider_status", "QueryProviderStatusCommand"),
        ("query_network_health", "QueryNetworkHealthCommand"),
        ("query_capabilities", "QueryCapabilitiesCommand"),
        ("ping_meter", "PingMeterCommand"),
        ("query_meter_neighbors", "QueryMeterNeighborsCommand"),
        ("query_meter_config", "QueryMeterConfigCommand"),
        ("query_meter_version", "QueryMeterVersionCommand"),
        ("read_meter_now", "ReadMeterNowCommand"),
        ("query_meter_errors", "QueryMeterErrorsCommand"),
        ("reset_meter_errors", "ResetMeterErrorsCommand"),
        ("associate_meter", "AssociateMeterCommand"),
        ("configure_high_capacity_meter", "ConfigureHighCapacityMeterCommand"),
        ("start_firmware_update", "StartFirmwareUpdateCommand"),
        ("query_firmware_update_status", "QueryFirmwareUpdateStatusCommand"),
        ("cancel_firmware_update", "CancelFirmwareUpdateCommand"),
        ("enter_configuration_mode", "EnterConfigurationModeCommand"),
        ("rf_test", "RfTestCommand"),
        ("read_meter_memory", "ReadMeterMemoryCommand"),
        ("read_meter_register", "ReadMeterRegisterCommand"),
        ("write_meter_register", "WriteMeterRegisterCommand"),
    )

    def get_mapping(self) -> dict[str, type]:
        """Get discriminator mapping with actual type references."""
        from .register_meter_command import RegisterMeterCommand
        from .unregister_meter_command import UnregisterMeterCommand
        from .configure_meter_command import ConfigureMeterCommand
        from .set_balance_command import SetBalanceCommand
        from .configure_provider_command import ConfigureProviderCommand
        from .query_provider_status_command import QueryProviderStatusCommand
        from .query_network_health_command import QueryNetworkHealthCommand
        from .query_capabilities_command import QueryCapabilitiesCommand
        from .ping_meter_command import PingMeterCommand
        from .query_meter_neighbors_command import QueryMeterNeighborsCommand
        from .query_meter_config_command import QueryMeterConfigCommand
        from .query_meter_version_command import QueryMeterVersionCommand
        from .read_meter_now_command import ReadMeterNowCommand
        from .query_meter_errors_command import QueryMeterErrorsCommand
        from .reset_meter_errors_command import ResetMeterErrorsCommand
        from .associate_meter_command import AssociateMeterCommand
        from .configure_high_capacity_meter_command import ConfigureHighCapacityMeterCommand
        from .start_firmware_update_command import StartFirmwareUpdateCommand
        from .query_firmware_update_status_command import QueryFirmwareUpdateStatusCommand
        from .cancel_firmware_update_command import CancelFirmwareUpdateCommand
        from .enter_configuration_mode_command import EnterConfigurationModeCommand
        from .rf_test_command import RfTestCommand
        from .read_meter_memory_command import ReadMeterMemoryCommand
        from .read_meter_register_command import ReadMeterRegisterCommand
        from .write_meter_register_command import WriteMeterRegisterCommand
        return {
            "register_meter": RegisterMeterCommand,
            "unregister_meter": UnregisterMeterCommand,
            "configure_meter": ConfigureMeterCommand,
            "set_balance": SetBalanceCommand,
            "configure_provider": ConfigureProviderCommand,
            "query_provider_status": QueryProviderStatusCommand,
            "query_network_health": QueryNetworkHealthCommand,
            "query_capabilities": QueryCapabilitiesCommand,
            "ping_meter": PingMeterCommand,
            "query_meter_neighbors": QueryMeterNeighborsCommand,
            "query_meter_config": QueryMeterConfigCommand,
            "query_meter_version": QueryMeterVersionCommand,
            "read_meter_now": ReadMeterNowCommand,
            "query_meter_errors": QueryMeterErrorsCommand,
            "reset_meter_errors": ResetMeterErrorsCommand,
            "associate_meter": AssociateMeterCommand,
            "configure_high_capacity_meter": ConfigureHighCapacityMeterCommand,
            "start_firmware_update": StartFirmwareUpdateCommand,
            "query_firmware_update_status": QueryFirmwareUpdateStatusCommand,
            "cancel_firmware_update": CancelFirmwareUpdateCommand,
            "enter_configuration_mode": EnterConfigurationModeCommand,
            "rf_test": RfTestCommand,
            "read_meter_memory": ReadMeterMemoryCommand,
            "read_meter_register": ReadMeterRegisterCommand,
            "write_meter_register": WriteMeterRegisterCommand,
        }


SubmitCommandV1CommandsPostRequestBody: TypeAlias = Annotated[
    Union[RegisterMeterCommand, UnregisterMeterCommand, ConfigureMeterCommand, SetBalanceCommand, ConfigureProviderCommand, QueryProviderStatusCommand, QueryNetworkHealthCommand, QueryCapabilitiesCommand, PingMeterCommand, QueryMeterNeighborsCommand, QueryMeterConfigCommand, QueryMeterVersionCommand, ReadMeterNowCommand, QueryMeterErrorsCommand, ResetMeterErrorsCommand, AssociateMeterCommand, ConfigureHighCapacityMeterCommand, StartFirmwareUpdateCommand, QueryFirmwareUpdateStatusCommand, CancelFirmwareUpdateCommand, EnterConfigurationModeCommand, RfTestCommand, ReadMeterMemoryCommand, ReadMeterRegisterCommand, WriteMeterRegisterCommand],
    SubmitCommandV1CommandsPostRequestBodyDiscriminator()
]