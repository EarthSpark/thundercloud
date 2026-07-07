from __future__ import annotations

from collections.abc import ItemsView, KeysView, ValuesView
from dataclasses import dataclass, field
from typing import Any, ClassVar, Iterator

from .phase_reading import PhaseReading

__all__ = ["MeterReadingPhasedEventPerPhase"]

@dataclass
class MeterReadingPhasedEventPerPhase:
    """
    Generic JSON value object that preserves arbitrary data.

    This class wraps a dictionary with typed values, providing dict-like access
    while ensuring values are properly deserialized into PhaseReading instances.

    Example:
        from sparkmeter.metering._generated.core.cattrs_converter import structure_from_dict, unstructure_to_dict

        # Deserialize from API response - values become PhaseReading instances
        obj = structure_from_dict({"key": {"field": "value"}}, MeterReadingPhasedEventPerPhase)

        # Access returns typed PhaseReading instance
        item = obj["key"]
        print(item.field)  # "value" - direct attribute access

        # Serialize for API request
        data = unstructure_to_dict(obj)
    """

    _data: dict[str, PhaseReading] = field(default_factory=dict, repr=False)

    # Runtime type information for cattrs deserialization
    _value_type: ClassVar[str] = "PhaseReading"

    def get(self, key: str, default: PhaseReading | None = None) -> PhaseReading | None:
        """Get value for key, returning default if key not present."""
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> PhaseReading:
        """Get value for key."""
        return self._data[key]

    def __setitem__(self, key: str, value: PhaseReading) -> None:
        """Set value for key."""
        self._data[key] = value

    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._data

    def __bool__(self) -> bool:
        """Return True if wrapper contains any data."""
        return bool(self._data)

    def keys(self) -> KeysView[str]:
        """Return dictionary keys."""
        return self._data.keys()

    def values(self) -> ValuesView[PhaseReading]:
        """Return dictionary values."""
        return self._data.values()

    def items(self) -> ItemsView[str, PhaseReading]:
        """Return dictionary items."""
        return self._data.items()

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys."""
        return iter(self._data)

    def __len__(self) -> int:
        """Return number of items."""
        return len(self._data)


# Register cattrs hooks for MeterReadingPhasedEventPerPhase
def _structure_meterreadingphasedeventperphase(data: dict[str, Any], _: type[MeterReadingPhasedEventPerPhase]) -> MeterReadingPhasedEventPerPhase:
    """Structure hook for cattrs to handle MeterReadingPhasedEventPerPhase deserialization with typed values."""
    if data is None:
        return MeterReadingPhasedEventPerPhase()
    if isinstance(data, MeterReadingPhasedEventPerPhase):
        return data

    # Import converter lazily to avoid circular imports
    from sparkmeter.metering._generated.core.cattrs_converter import converter, _register_structure_hooks_recursively

    # Register hooks for dataclass value types (once, outside loop)
    if hasattr(PhaseReading, '__dataclass_fields__'):
        _register_structure_hooks_recursively(PhaseReading)

    # Deserialize each value into PhaseReading
    # Using converter.structure() for all values - cattrs handles primitives, datetime, bytes, etc.
    structured_data: dict[str, PhaseReading] = {}
    for key, value in data.items():
        structured_data[key] = converter.structure(value, PhaseReading)

    return MeterReadingPhasedEventPerPhase(_data=structured_data)


def _unstructure_meterreadingphasedeventperphase(instance: MeterReadingPhasedEventPerPhase) -> dict[str, Any]:
    """Unstructure hook for cattrs to handle MeterReadingPhasedEventPerPhase serialization."""
    from sparkmeter.metering._generated.core.cattrs_converter import converter

    # Unstructure each value
    return {
        key: converter.unstructure(value)
        for key, value in instance._data.items()
    }


# Register hooks with cattrs converter at module import time
from sparkmeter.metering._generated.core.cattrs_converter import converter
converter.register_structure_hook(MeterReadingPhasedEventPerPhase, _structure_meterreadingphasedeventperphase)
converter.register_unstructure_hook(MeterReadingPhasedEventPerPhase, _unstructure_meterreadingphasedeventperphase)
