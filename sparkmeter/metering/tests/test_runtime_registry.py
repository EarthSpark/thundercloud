"""Tests for the running-public-app registry."""

from types import SimpleNamespace

import pytest

from sparkmeter.metering import runtime_registry


@pytest.fixture
def clean_registry():
    """Save and restore the process-global registry via the public API."""
    saved = runtime_registry.get_running_app()
    try:
        yield
    finally:
        runtime_registry.set_running_app(saved)


def test_set_none_clears_the_registry(clean_registry):
    runtime_registry.set_running_app(None)
    assert runtime_registry.get_running_app() is None


def test_publish_then_get_returns_same_object(clean_registry):
    app = SimpleNamespace(name="public")
    runtime_registry.set_running_app(app)
    assert runtime_registry.get_running_app() is app


def test_republish_latest_wins(clean_registry):
    first = SimpleNamespace(name="first")
    second = SimpleNamespace(name="second")
    runtime_registry.set_running_app(first)
    runtime_registry.set_running_app(second)
    assert runtime_registry.get_running_app() is second
