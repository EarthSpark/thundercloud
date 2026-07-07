from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, TypeAlias, Union

from .capabilities_event import CapabilitiesEvent
from .command_accepted_event import CommandAcceptedEvent
from .command_applied_event import CommandAppliedEvent
from .command_cached_event import CommandCachedEvent
from .command_failed_event import CommandFailedEvent
from .command_rejected_event import CommandRejectedEvent
from .command_timed_out_event import CommandTimedOutEvent
from .firmware_update_status_event import FirmwareUpdateStatusEvent
from .heartbeat_summary_event import HeartbeatSummaryEvent
from .log_event import LogEvent
from .meter_config_event import MeterConfigEvent
from .meter_errors_event import MeterErrorsEvent
from .meter_firmware_changed_event import MeterFirmwareChangedEvent
from .meter_instant_reading_event import MeterInstantReadingEvent
from .meter_memory_event import MeterMemoryEvent
from .meter_neighbors_event import MeterNeighborsEvent
from .meter_reading_event import MeterReadingEvent
from .meter_reading_phased_event import MeterReadingPhasedEvent
from .meter_register_event import MeterRegisterEvent
from .meter_version_event import MeterVersionEvent
from .network_health_event import NetworkHealthEvent
from .provider_status_event import ProviderStatusEvent
from .rf_test_result_event import RfTestResultEvent

from .capabilities_event import CapabilitiesEvent
from .command_accepted_event import CommandAcceptedEvent
from .command_applied_event import CommandAppliedEvent
from .command_cached_event import CommandCachedEvent
from .command_failed_event import CommandFailedEvent
from .command_rejected_event import CommandRejectedEvent
from .command_timed_out_event import CommandTimedOutEvent
from .firmware_update_status_event import FirmwareUpdateStatusEvent
from .heartbeat_summary_event import HeartbeatSummaryEvent
from .log_event import LogEvent
from .meter_config_event import MeterConfigEvent
from .meter_errors_event import MeterErrorsEvent
from .meter_firmware_changed_event import MeterFirmwareChangedEvent
from .meter_instant_reading_event import MeterInstantReadingEvent
from .meter_memory_event import MeterMemoryEvent
from .meter_neighbors_event import MeterNeighborsEvent
from .meter_reading_event import MeterReadingEvent
from .meter_reading_phased_event import MeterReadingPhasedEvent
from .meter_register_event import MeterRegisterEvent
from .meter_version_event import MeterVersionEvent
from .network_health_event import NetworkHealthEvent
from .provider_status_event import ProviderStatusEvent
from .rf_test_result_event import RfTestResultEvent

__all__ = ['StreamEventsV1EventsGet200Response', 'StreamEventsV1EventsGet200ResponseDiscriminator']

@dataclass(frozen=True)
class StreamEventsV1EventsGet200ResponseDiscriminator:
    """Discriminator metadata for StreamEventsV1EventsGet200Response union."""

    property_name: str = "event_type"
    """The discriminator property name"""

    # Mapping stored as tuple for frozen dataclass compatibility
    _mapping_data: tuple[tuple[str, str], ...] = (
        ("command_accepted", "CommandAcceptedEvent"),
        ("command_rejected", "CommandRejectedEvent"),
        ("command_applied", "CommandAppliedEvent"),
        ("command_failed", "CommandFailedEvent"),
        ("command_timed_out", "CommandTimedOutEvent"),
        ("command_cached", "CommandCachedEvent"),
        ("meter_reading", "MeterReadingEvent"),
        ("meter_reading_phased", "MeterReadingPhasedEvent"),
        ("meter_firmware_changed", "MeterFirmwareChangedEvent"),
        ("heartbeat_summary", "HeartbeatSummaryEvent"),
        ("log", "LogEvent"),
        ("provider_status", "ProviderStatusEvent"),
        ("network_health", "NetworkHealthEvent"),
        ("capabilities", "CapabilitiesEvent"),
        ("meter_neighbors", "MeterNeighborsEvent"),
        ("meter_config", "MeterConfigEvent"),
        ("meter_version", "MeterVersionEvent"),
        ("meter_instant_reading", "MeterInstantReadingEvent"),
        ("meter_errors", "MeterErrorsEvent"),
        ("firmware_update_status", "FirmwareUpdateStatusEvent"),
        ("rf_test_result", "RfTestResultEvent"),
        ("meter_memory", "MeterMemoryEvent"),
        ("meter_register", "MeterRegisterEvent"),
    )

    def get_mapping(self) -> dict[str, type]:
        """Get discriminator mapping with actual type references."""
        from .command_accepted_event import CommandAcceptedEvent
        from .command_rejected_event import CommandRejectedEvent
        from .command_applied_event import CommandAppliedEvent
        from .command_failed_event import CommandFailedEvent
        from .command_timed_out_event import CommandTimedOutEvent
        from .command_cached_event import CommandCachedEvent
        from .meter_reading_event import MeterReadingEvent
        from .meter_reading_phased_event import MeterReadingPhasedEvent
        from .meter_firmware_changed_event import MeterFirmwareChangedEvent
        from .heartbeat_summary_event import HeartbeatSummaryEvent
        from .log_event import LogEvent
        from .provider_status_event import ProviderStatusEvent
        from .network_health_event import NetworkHealthEvent
        from .capabilities_event import CapabilitiesEvent
        from .meter_neighbors_event import MeterNeighborsEvent
        from .meter_config_event import MeterConfigEvent
        from .meter_version_event import MeterVersionEvent
        from .meter_instant_reading_event import MeterInstantReadingEvent
        from .meter_errors_event import MeterErrorsEvent
        from .firmware_update_status_event import FirmwareUpdateStatusEvent
        from .rf_test_result_event import RfTestResultEvent
        from .meter_memory_event import MeterMemoryEvent
        from .meter_register_event import MeterRegisterEvent
        return {
            "command_accepted": CommandAcceptedEvent,
            "command_rejected": CommandRejectedEvent,
            "command_applied": CommandAppliedEvent,
            "command_failed": CommandFailedEvent,
            "command_timed_out": CommandTimedOutEvent,
            "command_cached": CommandCachedEvent,
            "meter_reading": MeterReadingEvent,
            "meter_reading_phased": MeterReadingPhasedEvent,
            "meter_firmware_changed": MeterFirmwareChangedEvent,
            "heartbeat_summary": HeartbeatSummaryEvent,
            "log": LogEvent,
            "provider_status": ProviderStatusEvent,
            "network_health": NetworkHealthEvent,
            "capabilities": CapabilitiesEvent,
            "meter_neighbors": MeterNeighborsEvent,
            "meter_config": MeterConfigEvent,
            "meter_version": MeterVersionEvent,
            "meter_instant_reading": MeterInstantReadingEvent,
            "meter_errors": MeterErrorsEvent,
            "firmware_update_status": FirmwareUpdateStatusEvent,
            "rf_test_result": RfTestResultEvent,
            "meter_memory": MeterMemoryEvent,
            "meter_register": MeterRegisterEvent,
        }


StreamEventsV1EventsGet200Response: TypeAlias = Annotated[
    Union[CommandAcceptedEvent, CommandRejectedEvent, CommandAppliedEvent, CommandFailedEvent, CommandTimedOutEvent, CommandCachedEvent, MeterReadingEvent, MeterReadingPhasedEvent, MeterFirmwareChangedEvent, HeartbeatSummaryEvent, LogEvent, ProviderStatusEvent, NetworkHealthEvent, CapabilitiesEvent, MeterNeighborsEvent, MeterConfigEvent, MeterVersionEvent, MeterInstantReadingEvent, MeterErrorsEvent, FirmwareUpdateStatusEvent, RfTestResultEvent, MeterMemoryEvent, MeterRegisterEvent],
    StreamEventsV1EventsGet200ResponseDiscriminator()
]