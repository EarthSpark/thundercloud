# -*- coding: utf-8 -*-
"""Regression tests for the periodic-jobs runner.

The job functions reach `current_app` for DB access, but the periodic
loop runs them in `asyncio.to_thread` worker threads that never enter
a Flask request context. `_run_blocking` is the layer that pushes an
explicit app context on the worker thread; these tests guard that
contract so it doesn't silently regress.
"""
import asyncio
import threading

import pytest
from flask import current_app

from sparkmeter import periodic


class TestRunBlocking:

    def test_pushes_flask_context_on_worker_thread(self, app):
        """The worker thread should see `current_app` resolve to the
        passed Flask app — without this, the pre-fix periodic jobs
        crashed with `RuntimeError: Working outside of application
        context` on every tick.
        """
        observed = {}

        def _job():
            observed["thread_id"] = threading.get_ident()
            observed["app_name"] = current_app.name
            # Touch current_app.config to confirm the proxy resolves
            # to a real app (not just a smuggled-through reference).
            observed["has_config"] = current_app.config is not None

        asyncio.run(periodic._run_blocking(_job, app))

        # Confirm the job actually ran (so absence-of-exception alone
        # isn't a green test).
        assert "thread_id" in observed
        assert observed["thread_id"] != threading.get_ident()
        assert observed["app_name"] == app.name
        assert observed["has_config"] is True

    def test_swallows_job_exceptions(self, app, caplog):
        """`_run_blocking` is supposed to log-and-continue on job
        exceptions, not propagate (the periodic loops would die
        otherwise).
        """
        def _broken_job():
            raise RuntimeError("boom from inside the job")

        # No exception should escape.
        asyncio.run(periodic._run_blocking(_broken_job, app))

        # The logger.exception inside _run_blocking should have captured
        # the failure.
        assert any(
            "boom from inside the job" in record.message or
            "boom from inside the job" in (record.exc_text or "")
            for record in caplog.records
        )

    def test_signature_requires_flask_app(self):
        """The pre-fix signature accepted only `fn`. Calling without
        the Flask app must fail loudly — accepting it again would
        reintroduce the original bug.
        """
        # `getattr` keeps the call dynamic so static type checkers
        # don't flag the intentionally-missing `flask_app` arg.
        run_blocking = getattr(periodic, "_run_blocking")
        with pytest.raises(TypeError):
            asyncio.run(run_blocking(lambda: None))


class TestPeriodicLifespan:

    def test_raises_when_flask_app_missing(self):
        """`periodic_lifespan` must refuse to run if the ASGI
        entrypoint forgot to stash the Flask app on `app.state`.
        Otherwise the periodic jobs would silently no-op or crash
        deep inside `asyncio.to_thread`.
        """
        class _FakeApp:
            class state:
                pass

        async def _enter():
            async with periodic.periodic_lifespan(_FakeApp()):
                pass

        with pytest.raises(RuntimeError, match="flask_app is not set"):
            asyncio.run(_enter())
