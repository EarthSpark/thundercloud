"""Tests for the sync Flask-facing api.py surface.

Each function should push the right shape onto the dispatch queue and
not do any I/O of its own.

The dispatch queue uses `asyncio.run_coroutine_threadsafe` to schedule
puts onto an event loop running in another thread. Tests therefore
spin up a background thread running an event loop, register that
loop+queue with `dispatch`, and drain by hopping back into the loop.
"""

import asyncio
import threading
import time

import pytest

from sparkmeter.metering import api, dispatch


@pytest.fixture
def loop_with_queue():
    """Run an event loop in a background thread; register it with dispatch."""
    loop = asyncio.new_event_loop()
    queue: asyncio.Queue = asyncio.Queue()
    ready = threading.Event()

    def _run():
        asyncio.set_event_loop(loop)
        ready.set()
        loop.run_forever()

    thread = threading.Thread(target=_run, name="test-event-loop", daemon=True)
    thread.start()
    ready.wait()
    dispatch.register_loop(loop, queue)

    yield loop, queue

    dispatch.unregister_loop()
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=1.0)
    loop.close()


def _drain(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> list[dict]:
    """Drain the queue from the calling thread by hopping into the loop."""
    # Give already-scheduled puts a moment to settle.
    time.sleep(0.05)

    out: list[dict] = []

    async def _drain_inner():
        while not queue.empty():
            out.append(queue.get_nowait())

    fut = asyncio.run_coroutine_threadsafe(_drain_inner(), loop)
    fut.result(timeout=1.0)
    return out


def test_send_set_config_enqueues_configure_meter(loop_with_queue):
    loop, queue = loop_with_queue
    api.send_set_config(
        mac=42,
        command="enable",
        load_limit=1500.0,
        subnet=1,
        current_limit=10.0,
        balance=None,
        low_balance=False,
        firmware_version=None,
    )
    items = _drain(loop, queue)
    assert items == [
        {
            "op": "configure_meter",
            "node_id": 42,
            "command": "enable",
            "power_limit": 1500.0,
            "current_limit": 10.0,
        }
    ]


def test_send_set_config_with_balance_enqueues_two(loop_with_queue):
    loop, queue = loop_with_queue
    api.send_set_config(
        mac=42,
        command="enable",
        load_limit=1500.0,
        subnet=1,
        current_limit=10.0,
        balance="12.5",
        low_balance=True,
        firmware_version=None,
    )
    items = _drain(loop, queue)
    assert len(items) == 2
    assert items[0]["op"] == "configure_meter"
    assert items[1] == {
        "op": "set_balance",
        "node_id": 42,
        "balance": "12.5",
        "low_balance_flag": True,
    }


def test_register_meter_enqueues(loop_with_queue):
    loop, queue = loop_with_queue
    api.register_meter(node_id=100, node_type="SM5R", mac=0xABCD)
    items = _drain(loop, queue)
    assert items == [{"op": "register_meter", "node_id": 100, "node_type": "SM5R", "mac": 0xABCD}]


def test_unregister_meter_enqueues(loop_with_queue):
    loop, queue = loop_with_queue
    api.unregister_meter(node_id=55)
    items = _drain(loop, queue)
    assert items == [{"op": "unregister_meter", "node_id": 55}]


def test_legacy_register_node_alias_works(loop_with_queue):
    loop, queue = loop_with_queue
    api.register_node(node_id=1, node_type="SM5R")
    items = _drain(loop, queue)
    assert items == [{"op": "register_meter", "node_id": 1, "node_type": "SM5R", "mac": None}]


def test_legacy_unregister_node_alias_works(loop_with_queue):
    loop, queue = loop_with_queue
    api.unregister_node(node_id=1)
    items = _drain(loop, queue)
    assert items == [{"op": "unregister_meter", "node_id": 1}]


def test_disable_all_meters_with_explicit_node_ids(loop_with_queue):
    loop, queue = loop_with_queue
    api.disable_all_meters([1, 2, 3])
    items = _drain(loop, queue)
    assert len(items) == 3
    assert all(item["op"] == "configure_meter" for item in items)
    assert all(item["command"] == "disable" for item in items)
    assert sorted(item["node_id"] for item in items) == [1, 2, 3]


def test_enqueue_drops_silently_when_loop_unregistered():
    """Without a registered loop, sync API calls return without raising."""
    dispatch.unregister_loop()
    # Should not raise.
    api.register_meter(node_id=99, node_type="SM5R")
    api.unregister_meter(node_id=99)
    api.send_set_config(
        mac=1,
        command="disable",
        load_limit=0,
        subnet=0,
        current_limit=0,
        balance=None,
        low_balance=False,
        firmware_version=None,
    )
