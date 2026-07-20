"""Tests for gateway disconnect/reconnect handling in the metering lifespan."""

import asyncio
import contextlib
import logging
from concurrent.futures import TimeoutError as FutureTimeoutError
from types import SimpleNamespace

import pytest

from sparkmeter.metering import lifespan, runtime_registry


class _FakeFlaskApp:
    """A flask-app stand-in exposing an app_context() context manager."""

    def app_context(self):
        return contextlib.nullcontext()


def _build_app(**overrides):
    commands_allowed = overrides.pop("commands_allowed", asyncio.Event())
    gateway_state = {
        "gateway_connected": None,
        "gateway_paused": False,
        "gateway_recovery_task": None,
        "needs_full_restart": False,
        "commands_allowed": commands_allowed,
    }
    gateway_state.update(overrides)
    app = SimpleNamespace(
        state=SimpleNamespace(
            metering_gateway_state=gateway_state,
            metering=None,
            flask_app=object(),
        )
    )
    return app, gateway_state


class TestObserveGatewayStatus:
    @pytest.mark.asyncio
    async def test_connected_event_stops_recovery_poll_and_requests_restart(self):
        started = asyncio.Event()

        async def waiting_recovery_task():
            started.set()
            await asyncio.sleep(3600)

        recovery_task = asyncio.create_task(waiting_recovery_task())
        await started.wait()

        commands_allowed = asyncio.Event()
        app, gateway_state = _build_app(
            gateway_connected=False,
            gateway_paused=True,
            gateway_recovery_task=recovery_task,
            commands_allowed=commands_allowed,
        )

        await lifespan._observe_gateway_status(
            app,
            {"type": "gateway_status", "data": {"connected": True}},
        )

        assert gateway_state["gateway_connected"] is True
        assert gateway_state["gateway_paused"] is False
        assert gateway_state["needs_full_restart"] is True
        assert gateway_state["commands_allowed"].is_set() is True
        assert gateway_state["gateway_recovery_task"] is None
        assert recovery_task.cancelled() is True

    @pytest.mark.asyncio
    async def test_connected_event_while_healthy_does_not_request_restart(self, monkeypatch):
        reconcile_calls = 0

        async def fake_reconcile(app):
            del app
            nonlocal reconcile_calls
            reconcile_calls += 1

        monkeypatch.setattr(lifespan, "_run_provider_reconcile", fake_reconcile)

        commands_allowed = asyncio.Event()
        commands_allowed.set()
        app, gateway_state = _build_app(
            gateway_connected=True,
            gateway_paused=False,
            commands_allowed=commands_allowed,
        )

        await lifespan._observe_gateway_status(
            app,
            {"type": "gateway_status", "data": {"connected": True}},
        )
        await lifespan._run_pending_provider_restart(app)

        assert reconcile_calls == 0
        assert gateway_state["needs_full_restart"] is False

    @pytest.mark.asyncio
    async def test_restart_runs_once_after_connected_event_stops_poll(self, monkeypatch):
        reconcile_calls = 0
        started = asyncio.Event()

        async def waiting_recovery_task():
            started.set()
            await asyncio.sleep(3600)

        async def fake_reconcile(app):
            del app
            nonlocal reconcile_calls
            reconcile_calls += 1

        monkeypatch.setattr(lifespan, "_run_provider_reconcile", fake_reconcile)

        recovery_task = asyncio.create_task(waiting_recovery_task())
        await started.wait()

        commands_allowed = asyncio.Event()
        app, gateway_state = _build_app(
            gateway_connected=False,
            gateway_paused=True,
            gateway_recovery_task=recovery_task,
            commands_allowed=commands_allowed,
        )

        await lifespan._observe_gateway_status(
            app,
            {"type": "gateway_status", "data": {"connected": True}},
        )
        await lifespan._run_pending_provider_restart(app)

        assert reconcile_calls == 1
        assert gateway_state["needs_full_restart"] is False

    @pytest.mark.asyncio
    async def test_removed_driver_stops_gateway_recovery_poll(self, monkeypatch):
        shutdown_calls = 0

        async def fake_shutdown(app):
            del app
            nonlocal shutdown_calls
            shutdown_calls += 1

        monkeypatch.setattr(lifespan, "shutdown_metering_runtime", fake_shutdown)

        app, gateway_state = _build_app(
            gateway_connected=False,
            gateway_paused=True,
        )

        def removed_provider(*, default="", flask_app=None):
            del default, flask_app
            return ""

        monkeypatch.setattr(lifespan, "configured_provider_url", removed_provider)

        await lifespan._recover_provider_after_gateway_loss(app)

        assert shutdown_calls == 1


class TestInProcessActivation:
    def test_activate_metering_runtime_uses_existing_running_app(self, monkeypatch):
        loop = object()
        app = SimpleNamespace(state=SimpleNamespace(main_loop=loop))
        seen = {}

        async def fake_ensure(public_app, skip_provider_init=False):
            seen["app"] = public_app
            seen["skip_provider_init"] = skip_provider_init
            return True

        def fake_run_coroutine_threadsafe(coro, running_loop):
            seen["loop"] = running_loop
            result = asyncio.run(coro)

            class _ImmediateFuture:
                def result(self, timeout=None):
                    seen["timeout"] = timeout
                    return result

            return _ImmediateFuture()

        monkeypatch.setattr(lifespan, "ensure_metering_runtime", fake_ensure)
        monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", fake_run_coroutine_threadsafe)

        saved = runtime_registry.get_running_app()
        try:
            runtime_registry.set_running_app(app)
            activated, error = lifespan.activate_metering_runtime_in_process(timeout=3.0)
        finally:
            runtime_registry.set_running_app(saved)

        assert activated is True
        assert error is None
        assert seen["app"] is app
        assert seen["loop"] is loop
        assert seen["timeout"] == 3.0

    def test_activate_reports_missing_public_app(self, monkeypatch):
        monkeypatch.setattr(lifespan, "get_running_app", lambda: None)
        activated, error = lifespan.activate_metering_runtime_in_process()
        assert activated is False
        assert error == "public app is not available"

    def test_activate_reports_missing_main_loop(self, monkeypatch):
        app = SimpleNamespace(state=SimpleNamespace(main_loop=None))
        monkeypatch.setattr(lifespan, "get_running_app", lambda: app)
        activated, error = lifespan.activate_metering_runtime_in_process()
        assert activated is False
        assert error == "main event loop is not available"


class TestProviderSignature:
    def test_builds_tuple(self):
        provider = {
            "id": "a",
            "base_url": "http://x",
            "selected_interface": "grpc",
            "enabled": True,
        }
        assert lifespan._provider_signature(provider) == ("a", "http://x", "grpc", True)

    def test_none_provider(self):
        assert lifespan._provider_signature(None) is None


class TestEnabledProviderSignature:
    def test_no_flask_app_returns_none(self):
        assert lifespan._enabled_provider_signature(None) is None

    def test_no_enabled_provider_returns_none(self, monkeypatch):
        monkeypatch.setattr("sparkmeter.config.provider_settings.get_enabled_provider", lambda: None)
        assert lifespan._enabled_provider_signature(_FakeFlaskApp()) is None

    def test_lookup_error_returns_none(self, monkeypatch):
        def boom():
            raise RuntimeError("db down")

        monkeypatch.setattr("sparkmeter.config.provider_settings.get_enabled_provider", boom)
        assert lifespan._enabled_provider_signature(_FakeFlaskApp()) is None

    def test_success_returns_signature(self, monkeypatch):
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.get_enabled_provider",
            lambda: {
                "id": "a",
                "base_url": "http://x",
                "selected_interface": "http",
                "enabled": True,
            },
        )
        assert lifespan._enabled_provider_signature(_FakeFlaskApp()) == (
            "a",
            "http://x",
            "http",
            True,
        )


class TestInitializeConfiguredProviders:
    def test_requires_flask_app(self):
        with pytest.raises(RuntimeError):
            lifespan._initialize_configured_providers_with_app_context(None, 10.0)

    def test_runs_within_app_context(self, monkeypatch):
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.initialize_configured_providers_on_startup",
            lambda timeout: [{"success": True, "timeout": timeout}],
        )
        result = lifespan._initialize_configured_providers_with_app_context(_FakeFlaskApp(), 5.0)
        assert result == [{"success": True, "timeout": 5.0}]


class TestShutdownMeteringRuntime:
    @pytest.mark.asyncio
    async def test_cancels_tasks_and_closes_clients(self):
        async def _long():
            await asyncio.sleep(3600)

        dispatcher = asyncio.create_task(_long())
        sse = asyncio.create_task(_long())
        await asyncio.sleep(0)

        closed = []

        class _Client:
            def __init__(self, name):
                self.name = name

            async def close(self):
                closed.append(self.name)

        app = SimpleNamespace(
            state=SimpleNamespace(
                metering_dispatcher_task=dispatcher,
                metering_sse_task=sse,
                metering_event_client=_Client("event"),
                metering=_Client("command"),
            )
        )

        await lifespan.shutdown_metering_runtime(app)

        assert dispatcher.cancelled()
        assert sse.cancelled()
        assert sorted(closed) == ["command", "event"]
        assert app.state.metering is None
        assert app.state.metering_provider_signature is None


class TestRunProviderReconcile:
    @pytest.mark.asyncio
    async def test_requires_client_and_flask_app(self):
        app = SimpleNamespace(state=SimpleNamespace(metering=None, flask_app=None))
        with pytest.raises(RuntimeError):
            await lifespan._run_provider_reconcile(app)

    @pytest.mark.asyncio
    async def test_delegates_to_reconcile_all(self, monkeypatch):
        seen = {}

        async def fake_reconcile(client, flask_app, skip_provider_init=False):
            seen["client"] = client
            seen["flask_app"] = flask_app
            seen["skip"] = skip_provider_init

        monkeypatch.setattr("sparkmeter.metering.reconcile.reconcile_all", fake_reconcile)
        client_obj = object()
        flask_obj = object()
        app = SimpleNamespace(state=SimpleNamespace(metering=client_obj, flask_app=flask_obj))

        await lifespan._run_provider_reconcile(app, skip_provider_init=True)

        # The active client and Flask app are forwarded, not just the flag.
        assert seen["client"] is client_obj
        assert seen["flask_app"] is flask_obj
        assert seen["skip"] is True


class TestRunPendingProviderRestart:
    @pytest.mark.asyncio
    async def test_noop_when_not_needed(self, monkeypatch):
        calls = []
        monkeypatch.setattr(lifespan, "_run_provider_reconcile", lambda app: calls.append(1) or _async_none())
        app, _ = _build_app(needs_full_restart=False)
        await lifespan._run_pending_provider_restart(app)
        assert calls == []

    @pytest.mark.asyncio
    async def test_defers_while_paused(self, monkeypatch):
        calls = []

        async def fake_reconcile(app):
            calls.append(1)

        monkeypatch.setattr(lifespan, "_run_provider_reconcile", fake_reconcile)
        app, _ = _build_app(needs_full_restart=True, gateway_paused=True)
        await lifespan._run_pending_provider_restart(app)
        assert calls == []

    @pytest.mark.asyncio
    async def test_reconciles_and_clears_flag(self, monkeypatch):
        calls = []

        async def fake_reconcile(app):
            calls.append(1)

        monkeypatch.setattr(lifespan, "_run_provider_reconcile", fake_reconcile)
        app, gateway_state = _build_app(needs_full_restart=True, gateway_paused=False)
        await lifespan._run_pending_provider_restart(app)
        assert calls == [1]
        assert gateway_state["needs_full_restart"] is False


class TestObserveGatewayDisconnect:
    @pytest.mark.asyncio
    async def test_non_gateway_event_ignored(self):
        app, gateway_state = _build_app()
        await lifespan._observe_gateway_status(app, {"type": "meter_reading"})
        assert gateway_state["gateway_paused"] is False

    @pytest.mark.asyncio
    async def test_disconnect_pauses_and_starts_recovery(self, monkeypatch):
        async def fake_recover(app):
            await asyncio.sleep(3600)

        monkeypatch.setattr(lifespan, "_recover_provider_after_gateway_loss", fake_recover)
        commands_allowed = asyncio.Event()
        commands_allowed.set()
        app, gateway_state = _build_app(gateway_connected=True, commands_allowed=commands_allowed)

        await lifespan._observe_gateway_status(app, {"type": "gateway_status", "data": {"connected": False}})

        assert gateway_state["gateway_paused"] is True
        assert gateway_state["commands_allowed"].is_set() is False
        recovery_task = gateway_state["gateway_recovery_task"]
        assert recovery_task is not None

        recovery_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await recovery_task


class TestCancelGatewayRecoveryPoll:
    @pytest.mark.asyncio
    async def test_noop_without_task(self):
        gateway_state = {"gateway_recovery_task": None}
        await lifespan._cancel_gateway_recovery_poll(gateway_state)
        assert gateway_state["gateway_recovery_task"] is None

    @pytest.mark.asyncio
    async def test_cancels_running_task(self):
        async def _long():
            await asyncio.sleep(3600)

        task = asyncio.create_task(_long())
        await asyncio.sleep(0)
        gateway_state = {"gateway_recovery_task": task}

        await lifespan._cancel_gateway_recovery_poll(gateway_state)

        assert task.cancelled()
        assert gateway_state["gateway_recovery_task"] is None


class TestWaitForGatewayOnline:
    @pytest.mark.asyncio
    async def test_removed_provider_raises(self, monkeypatch):
        monkeypatch.setattr(lifespan, "configured_provider_url", lambda *, default="", flask_app=None: "")
        app = SimpleNamespace(state=SimpleNamespace(flask_app=object()))
        with pytest.raises(lifespan._ProviderRemovedDuringRecovery):
            await lifespan._wait_for_gateway_online(app)

    @pytest.mark.asyncio
    async def test_returns_when_gateway_connected(self, monkeypatch):
        monkeypatch.setattr(
            lifespan, "configured_provider_url", lambda *, default="", flask_app=None: "http://drv"
        )
        # If it slept, that would mean it wrongly treated "connected" as not-ready.
        sleeps = []

        async def fake_sleep(seconds):
            sleeps.append(seconds)

        monkeypatch.setattr(lifespan.asyncio, "sleep", fake_sleep)

        gets = []

        class _Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"connected": True}

        class _AsyncClient:
            def __init__(self, timeout=None):
                self.timeout = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url):
                gets.append(url)
                return _Resp()

        monkeypatch.setattr(lifespan.httpx, "AsyncClient", _AsyncClient)
        app = SimpleNamespace(state=SimpleNamespace(flask_app=object()))

        await lifespan._wait_for_gateway_online(app)

        # A connected gateway is detected on the first probe of the status
        # endpoint, and the poll returns immediately without sleeping/retrying.
        assert gets == ["http://drv/v1/status"]
        assert sleeps == []


class TestMeteringLifespan:
    @pytest.mark.asyncio
    async def test_cloud_mode_is_noop(self, monkeypatch):
        monkeypatch.setattr(lifespan, "_is_ground", lambda: False)
        app = SimpleNamespace(state=SimpleNamespace())
        async with lifespan.metering_lifespan(app):
            pass
        assert app.state.metering is None

    @pytest.mark.asyncio
    async def test_offline_mode_is_noop(self, monkeypatch):
        monkeypatch.setattr(lifespan, "_is_ground", lambda: True)
        monkeypatch.setattr(lifespan, "_metering_enabled", lambda: False)
        app = SimpleNamespace(state=SimpleNamespace())
        async with lifespan.metering_lifespan(app):
            pass
        assert app.state.metering is None

    @pytest.mark.asyncio
    async def test_not_started_skips_shutdown(self, monkeypatch):
        monkeypatch.setattr(lifespan, "_is_ground", lambda: True)
        monkeypatch.setattr(lifespan, "_metering_enabled", lambda: True)

        async def fake_ensure(app):
            return False

        shutdowns = []

        async def fake_shutdown(app):
            shutdowns.append(1)

        monkeypatch.setattr(lifespan, "ensure_metering_runtime", fake_ensure)
        monkeypatch.setattr(lifespan, "shutdown_metering_runtime", fake_shutdown)

        app = SimpleNamespace(state=SimpleNamespace())
        async with lifespan.metering_lifespan(app):
            pass
        assert shutdowns == []

    @pytest.mark.asyncio
    async def test_started_runs_shutdown(self, monkeypatch):
        monkeypatch.setattr(lifespan, "_is_ground", lambda: True)
        monkeypatch.setattr(lifespan, "_metering_enabled", lambda: True)

        async def fake_ensure(app):
            return True

        shutdowns = []

        async def fake_shutdown(app):
            shutdowns.append(1)

        monkeypatch.setattr(lifespan, "ensure_metering_runtime", fake_ensure)
        monkeypatch.setattr(lifespan, "shutdown_metering_runtime", fake_shutdown)

        app = SimpleNamespace(state=SimpleNamespace())
        async with lifespan.metering_lifespan(app):
            pass
        assert shutdowns == [1]


class TestEnsureMeteringRuntimeEarlyReturns:
    @pytest.mark.asyncio
    async def test_not_ground_returns_false(self, monkeypatch):
        monkeypatch.setattr(lifespan, "_is_ground", lambda: False)
        app = SimpleNamespace(state=SimpleNamespace())
        assert await lifespan.ensure_metering_runtime(app) is False
        assert app.state.metering is None

    @pytest.mark.asyncio
    async def test_offline_returns_false(self, monkeypatch):
        monkeypatch.setattr(lifespan, "_is_ground", lambda: True)
        monkeypatch.setattr(lifespan, "_metering_enabled", lambda: False)
        app = SimpleNamespace(state=SimpleNamespace())
        assert await lifespan.ensure_metering_runtime(app) is False

    @pytest.mark.asyncio
    async def test_already_active_reruns_reconcile(self, monkeypatch):
        monkeypatch.setattr(lifespan, "_is_ground", lambda: True)
        monkeypatch.setattr(lifespan, "_metering_enabled", lambda: True)
        signature = ("a", "http://x", "http", True)
        monkeypatch.setattr(lifespan, "_enabled_provider_signature", lambda flask_app: signature)

        reconciles = []

        async def fake_reconcile(app, skip_provider_init=False):
            reconciles.append(skip_provider_init)

        monkeypatch.setattr(lifespan, "_run_provider_reconcile", fake_reconcile)

        app = SimpleNamespace(
            state=SimpleNamespace(
                flask_app=object(),
                metering=object(),
                metering_provider_signature=signature,
            )
        )

        assert await lifespan.ensure_metering_runtime(app, skip_provider_init=True) is True
        assert reconciles == [True]


def _async_none():
    async def _noop():
        return None

    return _noop()


class _SleepController:
    """Stand-in for asyncio.sleep that records durations and can break a loop.

    Records every requested delay and, once `stop_after` calls have been made,
    raises CancelledError so an otherwise-infinite retry loop terminates
    deterministically without any real waiting.
    """

    def __init__(self, stop_after=None):
        self.stop_after = stop_after
        self.calls = 0
        self.durations = []

    async def __call__(self, seconds):
        self.calls += 1
        self.durations.append(seconds)
        if self.stop_after is not None and self.calls >= self.stop_after:
            raise asyncio.CancelledError


class TestMeteringEnabled:
    def test_reads_offline_config_flag(self, config):
        # Metering is enabled when OFFLINE is false, and disabled when true —
        # proving the happy path actually reads the OFFLINE config value.
        config["OFFLINE"] = False
        assert lifespan._metering_enabled() is True
        config["OFFLINE"] = True
        assert lifespan._metering_enabled() is False

    def test_falls_back_to_env_when_config_errors(self, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("config unavailable")

        monkeypatch.setattr("sparkmeter.config.configdict.config", SimpleNamespace(get=boom))

        # SM_OFFLINE truthy -> metering disabled.
        monkeypatch.setenv("SM_OFFLINE", "1")
        assert lifespan._metering_enabled() is False

        # SM_OFFLINE unset/empty -> metering enabled.
        monkeypatch.setenv("SM_OFFLINE", "")
        assert lifespan._metering_enabled() is True


class TestRunSseConsumer:
    @pytest.mark.asyncio
    async def test_stream_ended_and_broken_request_full_restart_with_backoff(self, monkeypatch):
        app, gateway_state = _build_app()

        class _FakeEventClient:
            def __init__(self):
                self.calls = 0

            async def stream_events(self, client_id):
                index = self.calls
                self.calls += 1
                if index == 0:
                    # Connect successfully, deliver one event, then the
                    # stream ends -> "treating provider as restarted".
                    yield {"type": "meter_reading", "data": {}}
                    return
                # Second connection attempt breaks mid-stream.
                raise RuntimeError("stream broke")
                yield  # pragma: no cover - makes this an async generator

        async def noop_pending(app):
            del app

        async def noop_observe(app, raw_event):
            del app, raw_event

        async def noop_dispatch(raw, handlers):
            del raw, handlers

        monkeypatch.setattr(lifespan, "_run_pending_provider_restart", noop_pending)
        monkeypatch.setattr(lifespan, "_observe_gateway_status", noop_observe)
        monkeypatch.setattr("sparkmeter.metering.events.build_handlers", lambda app: [])
        monkeypatch.setattr("sparkmeter.metering.events.dispatch_dict_event", noop_dispatch)

        sleeper = _SleepController(stop_after=2)
        monkeypatch.setattr(asyncio, "sleep", sleeper)

        with pytest.raises(asyncio.CancelledError):
            await lifespan._run_sse_consumer(app, _FakeEventClient(), "cid")

        # Stream-ended branch (first iteration) and broken-stream branch
        # (second iteration) both flag a full restart.
        assert gateway_state["needs_full_restart"] is True
        # Backoff doubled between the first and second reconnect delays.
        assert sleeper.durations == [1.0, 2.0]

    @pytest.mark.asyncio
    async def test_initial_connection_failure_does_not_request_restart(self, monkeypatch):
        app, gateway_state = _build_app()

        class _FailingEventClient:
            async def stream_events(self, client_id):
                raise RuntimeError("never connected")
                yield  # pragma: no cover - makes this an async generator

        async def noop_pending(app):
            del app

        monkeypatch.setattr(lifespan, "_run_pending_provider_restart", noop_pending)
        monkeypatch.setattr("sparkmeter.metering.events.build_handlers", lambda app: [])

        sleeper = _SleepController(stop_after=1)
        monkeypatch.setattr(asyncio, "sleep", sleeper)

        with pytest.raises(asyncio.CancelledError):
            await lifespan._run_sse_consumer(app, _FailingEventClient(), "cid")

        # Never connected once, so a broken stream must not flag a restart.
        assert gateway_state["needs_full_restart"] is False
        assert sleeper.durations == [1.0]


class TestWaitForGatewayOnlineRetries:
    @pytest.mark.asyncio
    async def test_retries_while_disconnected_then_returns(self, monkeypatch):
        monkeypatch.setattr(
            lifespan, "configured_provider_url", lambda *, default="", flask_app=None: "http://drv/"
        )

        class _Resp:
            def __init__(self, connected):
                self._connected = connected

            def raise_for_status(self):
                return None

            def json(self):
                return {"connected": self._connected}

        # First poll reports disconnected, second reports connected.
        responses = [_Resp(False), _Resp(True)]

        class _AsyncClient:
            def __init__(self, timeout=None):
                del timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url):
                del url
                return responses.pop(0)

        monkeypatch.setattr(lifespan.httpx, "AsyncClient", _AsyncClient)
        sleeper = _SleepController()
        monkeypatch.setattr(asyncio, "sleep", sleeper)

        app = SimpleNamespace(state=SimpleNamespace(flask_app=object()))
        await lifespan._wait_for_gateway_online(app)

        # One disconnected poll -> one retry sleep -> connected poll returns.
        assert responses == []
        assert sleeper.calls == 1

    @pytest.mark.asyncio
    async def test_retries_when_status_endpoint_errors_then_returns(self, monkeypatch):
        monkeypatch.setattr(
            lifespan, "configured_provider_url", lambda *, default="", flask_app=None: "http://drv"
        )

        class _Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"connected": True}

        # First GET raises, second GET succeeds.
        outcomes = [RuntimeError("status unavailable"), _Resp()]

        class _AsyncClient:
            def __init__(self, timeout=None):
                del timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url):
                del url
                item = outcomes.pop(0)
                if isinstance(item, Exception):
                    raise item
                return item

        monkeypatch.setattr(lifespan.httpx, "AsyncClient", _AsyncClient)
        sleeper = _SleepController()
        monkeypatch.setattr(asyncio, "sleep", sleeper)

        app = SimpleNamespace(state=SimpleNamespace(flask_app=object()))
        await lifespan._wait_for_gateway_online(app)

        # One errored poll -> one retry sleep -> successful poll returns.
        assert outcomes == []
        assert sleeper.calls == 1


class TestRecoverProviderAfterGatewayLoss:
    @pytest.mark.asyncio
    async def test_resumes_after_gateway_online(self, monkeypatch):
        reconcile_calls = 0

        async def fake_wait(app):
            del app

        async def fake_reconcile(app):
            del app
            nonlocal reconcile_calls
            reconcile_calls += 1

        monkeypatch.setattr(lifespan, "_wait_for_gateway_online", fake_wait)
        monkeypatch.setattr(lifespan, "_run_provider_reconcile", fake_reconcile)

        commands_allowed = asyncio.Event()
        commands_allowed.clear()
        app, gateway_state = _build_app(
            gateway_connected=False,
            gateway_paused=True,
            needs_full_restart=True,
            commands_allowed=commands_allowed,
        )
        gateway_state["gateway_recovery_task"] = object()

        await lifespan._recover_provider_after_gateway_loss(app)

        assert reconcile_calls == 1
        assert gateway_state["gateway_connected"] is True
        assert gateway_state["gateway_paused"] is False
        assert gateway_state["needs_full_restart"] is False
        assert gateway_state["commands_allowed"].is_set() is True
        # finally-block clears the recovery-task handle.
        assert gateway_state["gateway_recovery_task"] is None

    @pytest.mark.asyncio
    async def test_retries_reconcile_on_failure_then_resumes(self, monkeypatch):
        reconcile_calls = 0

        async def fake_wait(app):
            del app

        async def fake_reconcile(app):
            del app
            nonlocal reconcile_calls
            reconcile_calls += 1
            if reconcile_calls == 1:
                raise RuntimeError("reconcile failed")

        sleeper = _SleepController()
        monkeypatch.setattr(lifespan, "_wait_for_gateway_online", fake_wait)
        monkeypatch.setattr(lifespan, "_run_provider_reconcile", fake_reconcile)
        monkeypatch.setattr(asyncio, "sleep", sleeper)

        commands_allowed = asyncio.Event()
        commands_allowed.clear()
        app, gateway_state = _build_app(
            gateway_connected=False,
            gateway_paused=True,
            commands_allowed=commands_allowed,
        )

        await lifespan._recover_provider_after_gateway_loss(app)

        # First reconcile raised -> one backoff sleep -> second reconcile resumed.
        assert reconcile_calls == 2
        assert sleeper.calls == 1
        assert gateway_state["gateway_paused"] is False
        assert gateway_state["commands_allowed"].is_set() is True


class TestActivateMeteringRuntimeErrors:
    def test_reports_timeout(self, monkeypatch):
        app = SimpleNamespace(state=SimpleNamespace(main_loop=object()))
        monkeypatch.setattr(lifespan, "get_running_app", lambda: app)

        async def fake_ensure(public_app, skip_provider_init=False):
            del public_app, skip_provider_init
            return True

        monkeypatch.setattr(lifespan, "ensure_metering_runtime", fake_ensure)

        class _TimingOutFuture:
            def result(self, timeout=None):
                del timeout
                raise FutureTimeoutError()

        def fake_run_coroutine_threadsafe(coro, running_loop):
            del running_loop
            coro.close()
            return _TimingOutFuture()

        monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", fake_run_coroutine_threadsafe)

        activated, error = lifespan.activate_metering_runtime_in_process(timeout=1.0)

        assert activated is False
        assert error == "timed out activating live metering runtime"

    def test_reports_generic_error(self, monkeypatch):
        app = SimpleNamespace(state=SimpleNamespace(main_loop=object()))
        monkeypatch.setattr(lifespan, "get_running_app", lambda: app)

        async def fake_ensure(public_app, skip_provider_init=False):
            del public_app, skip_provider_init
            return True

        monkeypatch.setattr(lifespan, "ensure_metering_runtime", fake_ensure)

        class _FailingFuture:
            def result(self, timeout=None):
                del timeout
                raise RuntimeError("boom")

        def fake_run_coroutine_threadsafe(coro, running_loop):
            del running_loop
            coro.close()
            return _FailingFuture()

        monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", fake_run_coroutine_threadsafe)

        activated, error = lifespan.activate_metering_runtime_in_process()

        assert activated is False
        assert error == "boom"


class TestIsGround:
    def test_is_ground_reads_config_flag(self, monkeypatch):
        # _is_ground mirrors config.is_ground() when the config loads.
        monkeypatch.setattr("sparkmeter.config.configdict.config", SimpleNamespace(is_ground=lambda: True))
        assert lifespan._is_ground() is True
        monkeypatch.setattr("sparkmeter.config.configdict.config", SimpleNamespace(is_ground=lambda: False))
        assert lifespan._is_ground() is False

    def test_is_ground_falls_back_to_env(self, monkeypatch):
        def boom():
            raise RuntimeError("config unavailable")

        monkeypatch.setattr("sparkmeter.config.configdict.config", SimpleNamespace(is_ground=boom))

        # When config.is_ground() raises, the SPARKMETER_MODE env var decides.
        monkeypatch.setenv("SPARKMETER_MODE", "ground")
        assert lifespan._is_ground() is True
        monkeypatch.setenv("SPARKMETER_MODE", "cloud")
        assert lifespan._is_ground() is False


class TestShutdownSkipsMissingTaskSlot:
    @pytest.mark.asyncio
    async def test_shutdown_skips_missing_task_slot(self):
        # Only the dispatcher task slot is populated; the sse slot is None.
        # The `if task is None: continue` guard must skip the empty slot while
        # still cancelling the present task and closing both clients.
        async def _long():
            await asyncio.sleep(3600)

        dispatcher = asyncio.create_task(_long())
        await asyncio.sleep(0)

        closed = []

        class _Client:
            def __init__(self, name):
                self.name = name

            async def close(self):
                closed.append(self.name)

        app = SimpleNamespace(
            state=SimpleNamespace(
                metering_dispatcher_task=dispatcher,
                metering_sse_task=None,
                metering_event_client=_Client("event"),
                metering=_Client("command"),
            )
        )

        await lifespan.shutdown_metering_runtime(app)

        assert dispatcher.cancelled()
        assert sorted(closed) == ["command", "event"]
        assert app.state.metering is None
        assert app.state.metering_sse_task is None


class _FakeRuntimeClient:
    """Command/event client stand-in with an async close() and transport name."""

    def __init__(self, name, transport_name):
        self.name = name
        self.transport_name = transport_name
        self.closed = False

    async def close(self):
        self.closed = True


def _make_ground_app():
    return SimpleNamespace(state=SimpleNamespace(flask_app=_FakeFlaskApp(), metering=None))


def _install_ensure_harness(
    monkeypatch,
    *,
    provider_url="http://drv",
    signature=("id", "http://drv", "http", True),
):
    """Wire up ensure_metering_runtime with real create_task but stubbed coroutines.

    Returns a `records` dict capturing collaborator arguments so tests can assert
    the runtime built what it should.
    """
    records = {
        "reconcile": [],
        "register_loop": [],
        "command_clients": [],
        "event_clients": [],
    }

    monkeypatch.setattr(lifespan, "_is_ground", lambda: True)
    monkeypatch.setattr(lifespan, "_metering_enabled", lambda: True)
    monkeypatch.setattr(lifespan, "_enabled_provider_signature", lambda flask_app: signature)
    monkeypatch.setattr(
        lifespan, "configured_provider_url", lambda *, default="", flask_app=None: provider_url
    )

    def fake_build_command(provider, client_id, provider_details=None):
        records["command_clients"].append(
            {"provider": provider, "client_id": client_id, "provider_details": provider_details}
        )
        return _FakeRuntimeClient("command", "fake-cmd")

    def fake_build_event(provider, client_id, provider_details=None):
        records["event_clients"].append(
            {"provider": provider, "client_id": client_id, "provider_details": provider_details}
        )
        return _FakeRuntimeClient("event", "fake-evt")

    monkeypatch.setattr(lifespan, "build_command_client", fake_build_command)
    monkeypatch.setattr(lifespan, "build_event_client", fake_build_event)

    from sparkmeter.metering import dispatch

    def fake_register(loop, queue):
        records["register_loop"].append((loop, queue))

    async def fake_dispatcher(client, queue, commands_allowed=None):
        return

    monkeypatch.setattr(dispatch, "register_loop", fake_register)
    monkeypatch.setattr(dispatch, "command_dispatcher", fake_dispatcher)

    async def fake_sse(app, event_client, client_id):
        return

    monkeypatch.setattr(lifespan, "_run_sse_consumer", fake_sse)

    async def fake_reconcile(app, skip_provider_init=False):
        records["reconcile"].append(skip_provider_init)

    monkeypatch.setattr(lifespan, "_run_provider_reconcile", fake_reconcile)

    return records


async def _drain_runtime_tasks(app):
    """Cancel+await the spawned stub tasks so no pending-task warnings leak."""
    for task in (
        getattr(app.state, "metering_dispatcher_task", None),
        getattr(app.state, "metering_sse_task", None),
    ):
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


class TestEnsureMeteringRuntimeStartup:
    @pytest.mark.asyncio
    async def test_ensure_config_change_shuts_down_then_early_returns(self, monkeypatch):
        # An existing client with a *different* signature forces a restart:
        # shutdown_metering_runtime is awaited, then the empty provider URL
        # early-returns False with metering cleared.
        monkeypatch.setattr(lifespan, "_is_ground", lambda: True)
        monkeypatch.setattr(lifespan, "_metering_enabled", lambda: True)
        monkeypatch.setattr(
            lifespan, "_enabled_provider_signature", lambda flask_app: ("new", "http://new", "http", True)
        )
        monkeypatch.setattr(lifespan, "configured_provider_url", lambda *, default="", flask_app=None: "")

        shutdowns = []

        async def fake_shutdown(app):
            shutdowns.append(1)
            app.state.metering = None

        monkeypatch.setattr(lifespan, "shutdown_metering_runtime", fake_shutdown)

        app = SimpleNamespace(
            state=SimpleNamespace(
                flask_app=_FakeFlaskApp(),
                metering=object(),
                metering_provider_signature=("old", "http://old", "http", True),
            )
        )

        result = await lifespan.ensure_metering_runtime(app, skip_provider_init=True)

        assert result is False
        assert shutdowns == [1]
        assert app.state.metering is None

    @pytest.mark.asyncio
    async def test_ensure_init_pass_logs_per_result_branch(self, monkeypatch, caplog):
        monkeypatch.setattr(lifespan, "_is_ground", lambda: True)
        monkeypatch.setattr(lifespan, "_metering_enabled", lambda: True)
        monkeypatch.setattr(
            lifespan, "_enabled_provider_signature", lambda flask_app: ("x", "y", "http", True)
        )

        results = [
            {"success": True, "provider": {"name": "Alpha"}},
            {"attempted": True, "reason": "conn refused", "provider": {"base_url": "http://b"}},
            {"provider": {}},
        ]
        monkeypatch.setattr(
            lifespan,
            "_initialize_configured_providers_with_app_context",
            lambda flask_app, timeout: results,
        )
        # Empty provider URL early-returns after the init-pass logging.
        monkeypatch.setattr(lifespan, "configured_provider_url", lambda *, default="", flask_app=None: "")

        app = SimpleNamespace(state=SimpleNamespace(flask_app=_FakeFlaskApp(), metering=None))

        with caplog.at_level(logging.INFO):
            result = await lifespan.ensure_metering_runtime(app)

        assert result is False
        by_message = {r.getMessage(): r.levelname for r in caplog.records}
        # success -> INFO, name from provider["name"]
        assert by_message["metering startup init succeeded for Alpha"] == "INFO"
        # attempted failure -> WARNING, name falls back to base_url, reason included
        assert by_message["metering startup init failed for http://b: conn refused"] == "WARNING"
        # not attempted -> INFO skipped, name falls back to "meter driver", default reason
        assert by_message["metering startup init skipped for meter driver: not configured"] == "INFO"

    @pytest.mark.asyncio
    async def test_ensure_init_pass_exception_is_swallowed(self, monkeypatch, caplog):
        monkeypatch.setattr(lifespan, "_is_ground", lambda: True)
        monkeypatch.setattr(lifespan, "_metering_enabled", lambda: True)
        monkeypatch.setattr(
            lifespan, "_enabled_provider_signature", lambda flask_app: ("x", "y", "http", True)
        )

        def boom(flask_app, timeout):
            raise RuntimeError("init boom")

        monkeypatch.setattr(lifespan, "_initialize_configured_providers_with_app_context", boom)
        monkeypatch.setattr(lifespan, "configured_provider_url", lambda *, default="", flask_app=None: "")

        app = SimpleNamespace(state=SimpleNamespace(flask_app=_FakeFlaskApp(), metering=None))

        with caplog.at_level(logging.INFO):
            # The init-pass exception must NOT propagate; startup continues and
            # then early-returns on the empty provider URL.
            result = await lifespan.ensure_metering_runtime(app)

        assert result is False
        assert "metering startup init pass failed" in caplog.text

    @pytest.mark.asyncio
    async def test_ensure_provider_resolution_falls_back_to_http(self, monkeypatch, caplog):
        records = _install_ensure_harness(monkeypatch, provider_url="http://drv")

        def boom():
            raise RuntimeError("interface lookup down")

        monkeypatch.setattr("sparkmeter.config.provider_settings.get_enabled_provider", boom)

        app = _make_ground_app()
        with caplog.at_level(logging.INFO):
            result = await lifespan.ensure_metering_runtime(app, skip_provider_init=True)

        assert result is True
        # When provider resolution fails, the command client is built from the
        # synthetic HTTP-fallback provider record.
        assert records["command_clients"][0]["provider"] == {
            "base_url": "http://drv",
            "selected_interface": "http",
        }
        assert "falling back to HTTP" in caplog.text

        await lifespan.shutdown_metering_runtime(app)

    @pytest.mark.asyncio
    async def test_ensure_happy_path_builds_runtime(self, monkeypatch):
        records = _install_ensure_harness(monkeypatch)
        provider = {
            "id": "id",
            "base_url": "http://drv",
            "selected_interface": "http",
            "enabled": True,
        }
        monkeypatch.setattr("sparkmeter.config.provider_settings.get_enabled_provider", lambda: provider)
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.get_live_interface_details",
            lambda base_url, selected_interface=None: {"iface": selected_interface},
        )

        app = _make_ground_app()
        loop = asyncio.get_running_loop()

        result = await lifespan.ensure_metering_runtime(app, skip_provider_init=True)

        assert result is True
        # register_loop received the running loop and the created command queue.
        assert len(records["register_loop"]) == 1
        reg_loop, reg_queue = records["register_loop"][0]
        assert reg_loop is loop
        assert reg_queue is app.state.metering_command_queue
        assert isinstance(reg_queue, asyncio.Queue)
        # app.state populated with the live runtime handles.
        assert app.state.metering.name == "command"
        assert app.state.metering_event_client.name == "event"
        assert app.state.metering_client_id.startswith("webapp-")
        assert app.state.metering_provider_signature == ("id", "http://drv", "http", True)
        assert isinstance(app.state.metering_dispatcher_task, asyncio.Task)
        assert isinstance(app.state.metering_sse_task, asyncio.Task)
        assert app.state.metering_gateway_state["commands_allowed"].is_set() is True
        # The real provider record and its interface details reached build_command_client.
        assert records["command_clients"][0]["provider"] is provider
        assert records["command_clients"][0]["provider_details"] == {"iface": "http"}

        await lifespan.shutdown_metering_runtime(app)

    @pytest.mark.asyncio
    async def test_ensure_reconcile_success_passes_skip_flag(self, monkeypatch):
        records = _install_ensure_harness(monkeypatch)
        provider = {
            "id": "id",
            "base_url": "http://drv",
            "selected_interface": "http",
            "enabled": True,
        }
        # Init pass runs (skip_provider_init=False) and reports success for the
        # provider whose signature matches the desired one, so the reconcile is
        # invoked with skip_provider_init=True.
        monkeypatch.setattr(
            lifespan,
            "_initialize_configured_providers_with_app_context",
            lambda flask_app, timeout: [{"success": True, "provider": provider}],
        )
        monkeypatch.setattr("sparkmeter.config.provider_settings.get_enabled_provider", lambda: provider)
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.get_live_interface_details",
            lambda base_url, selected_interface=None: None,
        )

        app = _make_ground_app()
        result = await lifespan.ensure_metering_runtime(app, skip_provider_init=False)

        assert result is True
        assert records["reconcile"] == [True]

        await lifespan.shutdown_metering_runtime(app)

    @pytest.mark.asyncio
    async def test_ensure_reconcile_failure_aborts_and_reraises(self, monkeypatch, caplog):
        _install_ensure_harness(monkeypatch)
        provider = {
            "id": "id",
            "base_url": "http://drv",
            "selected_interface": "http",
            "enabled": True,
        }
        monkeypatch.setattr("sparkmeter.config.provider_settings.get_enabled_provider", lambda: provider)
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.get_live_interface_details",
            lambda base_url, selected_interface=None: None,
        )

        async def boom_reconcile(app, skip_provider_init=False):
            raise RuntimeError("reconcile boom")

        monkeypatch.setattr(lifespan, "_run_provider_reconcile", boom_reconcile)

        shutdowns = []

        async def fake_shutdown(app):
            shutdowns.append(1)

        monkeypatch.setattr(lifespan, "shutdown_metering_runtime", fake_shutdown)

        app = _make_ground_app()
        with caplog.at_level(logging.INFO):
            with pytest.raises(RuntimeError, match="reconcile boom"):
                await lifespan.ensure_metering_runtime(app, skip_provider_init=True)

        assert shutdowns == [1]
        assert "aborting startup" in caplog.text

        await _drain_runtime_tasks(app)


class TestSseConsumerCancelled:
    @pytest.mark.asyncio
    async def test_sse_consumer_cancelled_in_stream_propagates(self, monkeypatch):
        app, gateway_state = _build_app()

        class _CancelClient:
            async def stream_events(self, client_id):
                raise asyncio.CancelledError
                yield  # pragma: no cover - makes this an async generator

        async def noop_pending(app):
            del app

        monkeypatch.setattr(lifespan, "_run_pending_provider_restart", noop_pending)
        monkeypatch.setattr("sparkmeter.metering.events.build_handlers", lambda app: [])

        sleeper = _SleepController()
        monkeypatch.setattr(asyncio, "sleep", sleeper)

        with pytest.raises(asyncio.CancelledError):
            await lifespan._run_sse_consumer(app, _CancelClient(), "cid")

        # CancelledError re-raises without triggering the generic-Exception
        # side effects: no restart flag, no backoff sleep.
        assert gateway_state["needs_full_restart"] is False
        assert sleeper.calls == 0


class TestObserveGatewayStatusGuards:
    @pytest.mark.asyncio
    async def test_observe_gateway_status_noop_without_state(self):
        # A gateway_status event with no gateway_state must return without
        # touching (None-dereferencing) anything.
        app = SimpleNamespace(state=SimpleNamespace(metering_gateway_state=None))
        await lifespan._observe_gateway_status(app, {"type": "gateway_status", "data": {"connected": False}})
        assert app.state.metering_gateway_state is None

    @pytest.mark.asyncio
    async def test_observe_disconnect_while_paused_is_noop(self):
        # Already paused + a fresh disconnect event: the early return prevents a
        # second recovery task from being spawned.
        app, gateway_state = _build_app(gateway_connected=False, gateway_paused=True)
        gateway_state["gateway_recovery_task"] = None

        await lifespan._observe_gateway_status(app, {"type": "gateway_status", "data": {"connected": False}})

        assert gateway_state["gateway_paused"] is True
        assert gateway_state["gateway_recovery_task"] is None
        assert gateway_state["gateway_connected"] is False


class TestRecoverProviderGuards:
    @pytest.mark.asyncio
    async def test_recover_noop_without_state(self, monkeypatch):
        waits = []

        async def fake_wait(app):
            waits.append(1)

        monkeypatch.setattr(lifespan, "_wait_for_gateway_online", fake_wait)

        app = SimpleNamespace(state=SimpleNamespace(metering_gateway_state=None))
        await lifespan._recover_provider_after_gateway_loss(app)

        # Missing state -> early return, the polling collaborator is never awaited.
        assert waits == []

    @pytest.mark.asyncio
    async def test_recover_reconcile_cancelled_reraises(self, monkeypatch):
        async def fake_wait(app):
            del app

        async def cancel_reconcile(app):
            raise asyncio.CancelledError

        sleeper = _SleepController()
        monkeypatch.setattr(lifespan, "_wait_for_gateway_online", fake_wait)
        monkeypatch.setattr(lifespan, "_run_provider_reconcile", cancel_reconcile)
        monkeypatch.setattr(asyncio, "sleep", sleeper)

        app, gateway_state = _build_app(gateway_connected=False, gateway_paused=True)
        gateway_state["gateway_recovery_task"] = object()

        with pytest.raises(asyncio.CancelledError):
            await lifespan._recover_provider_after_gateway_loss(app)

        # CancelledError propagates without the retry backoff sleep firing, and
        # the finally-block still clears the recovery-task handle.
        assert sleeper.calls == 0
        assert gateway_state["gateway_recovery_task"] is None


class TestWaitForGatewayOnlineCancelled:
    @pytest.mark.asyncio
    async def test_wait_for_gateway_online_cancelled_reraises(self, monkeypatch):
        monkeypatch.setattr(
            lifespan, "configured_provider_url", lambda *, default="", flask_app=None: "http://drv"
        )

        sleeper = _SleepController()
        monkeypatch.setattr(asyncio, "sleep", sleeper)

        class _AsyncClient:
            def __init__(self, timeout=None):
                del timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def get(self, url):
                del url
                raise asyncio.CancelledError

        monkeypatch.setattr(lifespan.httpx, "AsyncClient", _AsyncClient)
        app = SimpleNamespace(state=SimpleNamespace(flask_app=object()))

        with pytest.raises(asyncio.CancelledError):
            await lifespan._wait_for_gateway_online(app)

        # CancelledError propagates without the retry sleep firing.
        assert sleeper.calls == 0
