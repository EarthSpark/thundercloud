from __future__ import annotations

from typing import TypeAlias

__all__ = ['StreamEventsV1EventsGetParamClientId']

StreamEventsV1EventsGetParamClientId: TypeAlias = str | None
"""Alias for Stable client identifier for command-reply routing. If omitted, the server assigns a fresh UUID."""