"""Tests for the shared HTTP SSE event stream helper."""

import pytest

from sparkmeter.metering import http_sse


class _FakeResponse:
    def __init__(self, lines):
        self._lines = lines

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeAsyncClient:
    calls = []
    init_kwargs = []

    def __init__(self, *, base_url, timeout):
        self.base_url = base_url
        self.timeout = timeout
        type(self).init_kwargs.append({"base_url": base_url, "timeout": timeout})

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False

    def stream(self, method, path, params=None, headers=None):
        type(self).calls.append(
            {
                "method": method,
                "path": path,
                "params": params,
                "headers": headers,
            }
        )
        return _FakeResponse(
            [
                'data: {"type":"gateway_status"}',
                "",
                'data: {"event_type":"meter_reading","meter_id":"42"}',
                "",
            ]
        )


@pytest.mark.asyncio
async def test_stream_json_events_uses_streaming_sse_request(monkeypatch):
    monkeypatch.setattr(http_sse.httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.calls.clear()
    _FakeAsyncClient.init_kwargs.clear()

    events = []
    async for event in http_sse.stream_json_events("http://127.0.0.1:18080/", "test-client"):
        events.append(event)

    # The trailing slash is stripped and the stream uses an unbounded timeout.
    assert _FakeAsyncClient.init_kwargs == [{"base_url": "http://127.0.0.1:18080", "timeout": None}]

    assert events == [
        {"type": "gateway_status"},
        {"event_type": "meter_reading", "meter_id": "42"},
    ]
    assert _FakeAsyncClient.calls == [
        {
            "method": "GET",
            "path": "/v1/events",
            "params": {"client_id": "test-client"},
            "headers": {
                "Accept": "text/event-stream",
                "X-Client-Id": "test-client",
            },
        }
    ]


@pytest.mark.asyncio
async def test_iter_sse_payloads_skips_comments_and_flushes_trailing_data():
    # A comment line (leading ":"), a multi-line data event terminated by a
    # blank line, then a final data event with no trailing blank line.
    response = _FakeResponse(
        [
            ": keep-alive heartbeat",
            "event: meter_reading",
            "data: line-one",
            "data: line-two",
            "",
            "data: trailing-without-blank",
        ]
    )

    payloads = [payload async for payload in http_sse._iter_sse_data_payloads(response)]

    assert payloads == ["line-one\nline-two", "trailing-without-blank"]


@pytest.mark.asyncio
async def test_iter_sse_payloads_handles_data_field_without_space():
    # `data:x` (no space after the colon) is valid SSE and must parse the same
    # as `data: x`. A leading blank line with an empty buffer is also ignored.
    response = _FakeResponse(["", "data:no-space-value", ""])

    payloads = [payload async for payload in http_sse._iter_sse_data_payloads(response)]

    assert payloads == ["no-space-value"]
