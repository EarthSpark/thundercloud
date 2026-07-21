# -*- coding: utf-8 -*-
"""Tests for the ASGI entrypoint composition helpers."""

import asyncio
import contextlib
from types import SimpleNamespace

import pytest

from sparkmeter import asgi


def test_create_internal_app_shares_metering_state_via_middleware():
    from fastapi.testclient import TestClient

    public = SimpleNamespace(state=SimpleNamespace(metering="client-A"))
    internal = asgi.create_internal_app(public)

    assert internal.title == "sparkmeter-internal"
    # The factory publishes the app on the module so ASGI servers can reach it.
    assert asgi.internal_app is internal

    client = TestClient(internal)
    # The middleware runs on every request (a 404 still exercises it) and copies
    # the public app's live metering client onto the internal app's state.
    client.get("/anything")
    assert internal.state.metering == "client-A"

    # It re-reads per request, so a change on the public app propagates through.
    public.state.metering = "client-B"
    client.get("/anything")
    assert internal.state.metering == "client-B"


@pytest.mark.asyncio
async def test_app_lifespan_composes_inner_lifespans(monkeypatch):
    entered = []

    @contextlib.asynccontextmanager
    async def fake_periodic(app):
        entered.append("periodic")
        yield

    @contextlib.asynccontextmanager
    async def fake_metering(app):
        entered.append("metering")
        yield

    monkeypatch.setattr(asgi, "periodic_lifespan", fake_periodic)
    monkeypatch.setattr(asgi, "metering_lifespan", fake_metering)

    app = SimpleNamespace(state=SimpleNamespace())
    async with asgi.app_lifespan(app):
        # The running loop is stashed for in-process metering activation.
        assert app.state.main_loop is asyncio.get_running_loop()

    # periodic wraps metering on the outside.
    assert entered == ["periodic", "metering"]
