from __future__ import annotations

from typing import TypeAlias

__all__ = ['MeterErrorEntryLocation']

MeterErrorEntryLocation: TypeAlias = str | None
"""Alias for Vendor-specific source location (e.g. file:line)."""