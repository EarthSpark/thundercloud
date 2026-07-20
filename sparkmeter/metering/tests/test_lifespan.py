"""Tests for the metering FastAPI lifespan."""

from types import SimpleNamespace

import pytest

from sparkmeter.metering import lifespan


@pytest.mark.asyncio
async def test_metering_lifespan_is_noop_on_cloud(monkeypatch):
    """On cloud, the lifespan sets app.state.metering to None and starts nothing."""
    monkeypatch.setattr("sparkmeter.config.configdict.config.is_cloud", lambda: True)

    app = SimpleNamespace(state=SimpleNamespace())

    async with lifespan.metering_lifespan(app):
        assert app.state.metering is None

    # No metering runtime was started: only the no-op no-metering state exists.
    assert app.state.metering is None
    assert not hasattr(app.state, "metering_command_queue")
