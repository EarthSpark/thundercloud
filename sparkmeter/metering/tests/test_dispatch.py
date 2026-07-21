"""Tests for the sync→async dispatch bridge and command handlers."""

import asyncio

import pytest
from meter_driver_spec.http.models import (
    ConfigureElectricalMeterCompatRequest,
    ElectricalMeterCommandName,
    RegisterNodeRequest,
    SetBalanceAndFlagsRequest,
)

from sparkmeter.metering import dispatch


class _FakeClient:
    """Records the typed command calls the handlers make."""

    def __init__(self):
        self.calls: list = []

    async def register_node(self, req):
        self.calls.append(("register_node", req))

    async def configure_meter(self, req):
        self.calls.append(("configure_meter", req))

    async def set_balance(self, node_id, req):
        self.calls.append(("set_balance", node_id, req))

    async def unregister_node(self, node_id):
        self.calls.append(("unregister_node", node_id))


class TestHandleConfigure:
    @pytest.mark.asyncio
    async def test_enable_sets_full_configuration(self):
        client = _FakeClient()
        await dispatch._handle_configure(
            client,
            {
                "op": "configure_meter",
                "node_id": 42,
                "command": "enable",
                "power_limit": 1500.0,
                "current_limit": 10.0,
                "startup_delay": 2,
                "throttle_on_time": 3,
                "throttle_off_time": 11,
                "throttle_count_limit": 4,
            },
        )
        assert len(client.calls) == 1
        _, req = client.calls[0]
        assert isinstance(req, ConfigureElectricalMeterCompatRequest)
        assert req.node_id == 42
        assert req.command is ElectricalMeterCommandName.ELECTRICALMETERCOMMANDENABLE
        assert req.configuration.power_limit == pytest.approx(1500.0)
        assert req.configuration.current_limit == pytest.approx(10.0)
        assert req.configuration.startup_delay == 2
        assert req.configuration.throttle_on_time == 3
        assert req.configuration.throttle_off_time == 11
        assert req.configuration.throttle_count_limit == 4

    @pytest.mark.asyncio
    async def test_disable(self):
        client = _FakeClient()
        await dispatch._handle_configure(client, {"node_id": 7, "command": "disable"})
        _, req = client.calls[0]
        assert req.command is ElectricalMeterCommandName.ELECTRICALMETERCOMMANDDISABLE

    @pytest.mark.asyncio
    async def test_unknown_command_dropped(self):
        client = _FakeClient()
        await dispatch._handle_configure(client, {"node_id": 7, "command": "wibble"})
        # No spec command name maps to "wibble", so nothing is submitted.
        assert client.calls == []


class TestHandleSetBalance:
    @pytest.mark.asyncio
    async def test_balance_becomes_spec_decimal(self):
        client = _FakeClient()
        await dispatch._handle_set_balance(
            client, {"node_id": 9, "balance": "12.5", "low_balance_flag": True}
        )
        kind, node_id, req = client.calls[0]
        assert kind == "set_balance"
        assert node_id == 9
        assert isinstance(req, SetBalanceAndFlagsRequest)
        assert req.balance.model_dump() == {"sign": 1, "coef": 125, "exp": -1}
        assert req.low_balance_flag is True

    @pytest.mark.asyncio
    async def test_zero_balance(self):
        client = _FakeClient()
        await dispatch._handle_set_balance(client, {"node_id": 9})
        _, _, req = client.calls[0]
        assert req.balance.model_dump() == {"sign": 1, "coef": 0, "exp": 0}


class TestHandleRegister:
    @pytest.mark.asyncio
    async def test_with_mac(self):
        client = _FakeClient()
        await dispatch._handle_register(client, {"node_id": 100, "node_type": "SM5R", "mac": 0xABCD})
        _, req = client.calls[0]
        assert isinstance(req, RegisterNodeRequest)
        assert req.node_id == 100
        assert req.node_type == "SM5R"
        assert req.mac == 0xABCD

    @pytest.mark.asyncio
    async def test_without_mac(self):
        client = _FakeClient()
        await dispatch._handle_register(client, {"node_id": 100, "node_type": "SM5R"})
        _, req = client.calls[0]
        assert req.mac is None


class TestHandleUnregister:
    @pytest.mark.asyncio
    async def test_basic(self):
        client = _FakeClient()
        await dispatch._handle_unregister(client, {"node_id": 55})
        assert client.calls == [("unregister_node", 55)]


async def _drain_with_dispatcher(client, queue, commands_allowed, done, timeout=1.0):
    """Run command_dispatcher until `done()` is truthy, then cancel it."""
    task = asyncio.create_task(dispatch.command_dispatcher(client, queue, commands_allowed))
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    try:
        while loop.time() < deadline:
            if done():
                return
            await asyncio.sleep(0.005)
        raise AssertionError("dispatcher did not reach the expected state in time")
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestCommandDispatcher:
    @pytest.mark.asyncio
    async def test_dispatches_queued_command_when_allowed(self):
        client = _FakeClient()
        queue: asyncio.Queue = asyncio.Queue()
        commands_allowed = asyncio.Event()
        commands_allowed.set()
        await queue.put({"op": "register_meter", "node_id": 7, "node_type": "SM5R"})

        await _drain_with_dispatcher(client, queue, commands_allowed, lambda: client.calls)

        kind, req = client.calls[0]
        assert kind == "register_node"
        # The queued dict was translated into a typed request carrying node_id.
        assert req.node_id == 7
        assert req.node_type == "SM5R"

    @pytest.mark.asyncio
    async def test_unknown_op_is_dropped_and_loop_continues(self):
        client = _FakeClient()
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put({"op": "does_not_exist"})
        await queue.put({"op": "unregister_meter", "node_id": 3})

        await _drain_with_dispatcher(client, queue, None, lambda: ("unregister_node", 3) in client.calls)

        # The unknown op was dropped; the following known op still ran.
        assert client.calls == [("unregister_node", 3)]

    @pytest.mark.asyncio
    async def test_handler_failure_is_isolated(self):
        class _BoomClient(_FakeClient):
            async def register_node(self, req):
                raise RuntimeError("kaboom")

        client = _BoomClient()
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put({"op": "register_meter", "node_id": 1})
        await queue.put({"op": "unregister_meter", "node_id": 2})

        await _drain_with_dispatcher(client, queue, None, lambda: ("unregister_node", 2) in client.calls)

        # The failing register handler did not stop the loop.
        assert ("unregister_node", 2) in client.calls

    @pytest.mark.asyncio
    async def test_commands_allowed_gate_blocks_until_set(self):
        client = _FakeClient()
        queue: asyncio.Queue = asyncio.Queue()
        commands_allowed = asyncio.Event()  # cleared: the gate is shut
        await queue.put({"op": "unregister_meter", "node_id": 9})

        task = asyncio.create_task(dispatch.command_dispatcher(client, queue, commands_allowed))
        try:
            # The dispatcher dequeues the command but blocks on the closed gate.
            await asyncio.sleep(0.02)
            assert client.calls == []

            # Opening the gate lets the already-dequeued command through.
            commands_allowed.set()
            loop = asyncio.get_running_loop()
            deadline = loop.time() + 1.0
            while loop.time() < deadline and not client.calls:
                await asyncio.sleep(0.005)
            assert client.calls == [("unregister_node", 9)]
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


class TestEnqueueCommand:
    def test_enqueue_drops_silently_without_loop(self):
        # Default state: no loop registered.
        dispatch.unregister_loop()
        assert dispatch.enqueue_command({"op": "register_meter", "node_id": 1}) is False

    def test_enqueue_returns_false_on_scheduling_error(self):
        # A registered loop/queue whose put() blows up: enqueue swallows it and
        # returns False rather than propagating into the sync caller.
        dispatch.register_loop(object(), object())  # object() has no .put()
        try:
            assert dispatch.enqueue_command({"op": "register_meter", "node_id": 1}) is False
        finally:
            dispatch.unregister_loop()

    @pytest.mark.asyncio
    async def test_enqueue_pushes_to_queue_when_loop_registered(self):
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        dispatch.register_loop(loop, queue)
        try:
            ok = dispatch.enqueue_command({"op": "register_meter", "node_id": 99})
            assert ok is True
            # The threadsafe wrapper schedules the put; allow the event loop
            # to process it.
            await asyncio.sleep(0)
            cmd = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert cmd == {"op": "register_meter", "node_id": 99}
        finally:
            dispatch.unregister_loop()


class TestEnqueueDisableAll:
    @pytest.mark.asyncio
    async def test_expands_to_per_node_configure_disable(self):
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        dispatch.register_loop(loop, queue)
        try:
            dispatch.enqueue_disable_all([1, 2, 3])
            # Each enqueue schedules a queue.put on the loop;
            # `await queue.get()` lets each put complete in turn.
            collected = []
            for _ in range(3):
                item = await asyncio.wait_for(queue.get(), timeout=1.0)
                collected.append(item)
            assert collected == [
                {"op": "configure_meter", "node_id": 1, "command": "disable"},
                {"op": "configure_meter", "node_id": 2, "command": "disable"},
                {"op": "configure_meter", "node_id": 3, "command": "disable"},
            ]
        finally:
            dispatch.unregister_loop()
