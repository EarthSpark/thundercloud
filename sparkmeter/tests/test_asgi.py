# -*- coding: utf-8 -*-
"""Tests for the ASGI entrypoint composition helpers."""

import asyncio
import contextlib
from types import SimpleNamespace

import pytest

from sparkmeter import asgi
from sparkmeter.metering import runtime_registry


def test_create_internal_app_shares_metering_state_via_middleware():
    from fastapi.testclient import TestClient

    public = SimpleNamespace(state=SimpleNamespace(metering="client-A"))
    internal = asgi.create_internal_app(public)

    assert internal.title == "sparkmeter-internal"

    client = TestClient(internal)
    # The middleware runs on every request (a 404 still exercises it) and copies
    # the public app's live metering client onto the internal app's state.
    client.get("/anything")
    assert internal.state.metering == "client-A"

    # It re-reads per request, so a change on the public app propagates through.
    public.state.metering = "client-B"
    client.get("/anything")
    assert internal.state.metering == "client-B"


def test_create_public_app_publishes_itself_to_the_registry(monkeypatch):
    # Skip the heavy Flask DB bootstrap and the real WSGI wrapper so
    # construction is cheap; the seam under test is unrelated to either.
    monkeypatch.setattr(asgi, "create_flask_app", lambda: SimpleNamespace())
    monkeypatch.setattr(asgi, "WSGIMiddleware", lambda app: app)

    # Save/restore the process-global registry so this test leaks no state.
    saved = runtime_registry.get_running_app()
    try:
        app = asgi.create_public_app()
        # The production seam: create_public_app must publish the running app
        # to the registry. If `set_running_app(api)` were removed from the
        # factory, get_running_app() would still hold `saved` (a different
        # object), and this identity assertion would fail.
        assert runtime_registry.get_running_app() is app
        # The registry is the single source: the factory must NOT write a
        # `public_app` module global (the reflective self-mutation we removed).
        assert "public_app" not in asgi.__dict__
    finally:
        runtime_registry.set_running_app(saved)


def test_public_app_attribute_resolves_from_registry_and_caches(monkeypatch):
    # Cheap construction: skip the Flask DB bootstrap and the real WSGI wrapper.
    monkeypatch.setattr(asgi, "create_flask_app", lambda: SimpleNamespace())
    monkeypatch.setattr(asgi, "WSGIMiddleware", lambda app: app)

    saved = runtime_registry.get_running_app()
    saved_internal = asgi._internal_app
    try:
        runtime_registry.set_running_app(None)
        asgi._internal_app = None

        # First access builds via create_public_app (which publishes to the
        # registry); a second access reads the same object back — no rebuild.
        first = asgi.public_app
        assert runtime_registry.get_running_app() is first
        second = asgi.public_app
        assert second is first
    finally:
        runtime_registry.set_running_app(saved)
        asgi._internal_app = saved_internal


def test_internal_app_attribute_builds_once_and_caches(monkeypatch):
    monkeypatch.setattr(asgi, "create_flask_app", lambda: SimpleNamespace())
    monkeypatch.setattr(asgi, "WSGIMiddleware", lambda app: app)

    saved = runtime_registry.get_running_app()
    saved_internal = asgi._internal_app
    try:
        runtime_registry.set_running_app(None)
        asgi._internal_app = None

        # First access builds the internal app once and caches it in the
        # private module var; a second access returns the identical object.
        first = asgi.internal_app
        second = asgi.internal_app
        assert second is first
        assert asgi._internal_app is first
    finally:
        runtime_registry.set_running_app(saved)
        asgi._internal_app = saved_internal


def test_unknown_attribute_raises_attribute_error():
    saved = runtime_registry.get_running_app()
    saved_internal = asgi._internal_app
    try:
        with pytest.raises(AttributeError):
            asgi.does_not_exist
    finally:
        runtime_registry.set_running_app(saved)
        asgi._internal_app = saved_internal


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
