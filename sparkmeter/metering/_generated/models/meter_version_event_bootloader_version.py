from __future__ import annotations

from typing import TypeAlias

from .firmware_version import FirmwareVersion

from .firmware_version import FirmwareVersion

__all__ = ['MeterVersionEventBootloaderVersion']

MeterVersionEventBootloaderVersion: TypeAlias = FirmwareVersion | None