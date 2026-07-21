"""Shared helpers for consuming a driver's HTTP SSE event stream.

Plain SSE parsing (RFC 8895 §9.2 "event stream" framing) — no vendor
package involved. Works against any driver implementing the Thunder-Cloud
2.0 Open Source Meter Driver Specification's required GET /v1/events
endpoint.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx


async def _iter_sse_data_payloads(response: httpx.Response) -> AsyncIterator[str]:
    """Yield each SSE event's joined `data:` payload as one string.

    A minimal, dependency-free SSE parser: accumulates consecutive
    `data:` lines for one event, and yields the joined payload when a
    blank line (the event terminator) is seen. `event:`/`id:`/`retry:`
    lines and comment lines (starting with `:`) are ignored — this
    codebase only cares about the JSON payload in `data:`.
    """
    data_lines: list[str] = []
    async for line in response.aiter_lines():
        if line == "":
            if data_lines:
                yield "\n".join(data_lines)
                data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[len("data:") :].lstrip(" "))
        # Other SSE fields (event:, id:, retry:) aren't needed here.
    if data_lines:
        yield "\n".join(data_lines)


async def stream_json_events(
    base_url: str,
    client_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Yield JSON event payloads from the driver's HTTP SSE endpoint."""
    headers = {"X-Client-Id": client_id, "Accept": "text/event-stream"}
    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=None) as client:
        async with client.stream(
            "GET",
            "/v1/events",
            params={"client_id": client_id},
            headers=headers,
        ) as response:
            response.raise_for_status()
            async for payload in _iter_sse_data_payloads(response):
                yield json.loads(payload)
