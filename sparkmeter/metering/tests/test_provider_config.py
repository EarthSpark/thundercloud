"""Tests for runtime provider URL resolution."""

import contextlib

from sparkmeter.config import provider_settings
from sparkmeter.metering.provider_config import configured_provider_url


class _FakeApp:
    """Minimal stand-in exposing an app_context() context manager."""

    def app_context(self):
        return contextlib.nullcontext()


def test_configured_provider_url_uses_flask_app_context(monkeypatch):
    monkeypatch.setattr(
        provider_settings, "get_enabled_provider", lambda: {"base_url": "http://driver:18080"}
    )
    assert configured_provider_url(default="unused", flask_app=_FakeApp()) == "http://driver:18080"


def test_configured_provider_url_returns_default_without_saved_provider(monkeypatch):
    monkeypatch.setattr(provider_settings, "get_enabled_provider", lambda: None)
    assert configured_provider_url(default="http://fallback") == "http://fallback"


def test_configured_provider_url_swallows_lookup_errors(monkeypatch):
    def boom():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(provider_settings, "get_enabled_provider", boom)
    assert configured_provider_url(default="http://fallback") == "http://fallback"
