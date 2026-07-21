"""
Command dispatch from sync Flask code to the async generated APIClient.

Flask request handlers run on Starlette's WSGI threadpool — sync code,
not in the asyncio event loop — so they can't `await client.default.submit_command_v1_commands_post(...)`
directly. `enqueue_command()` is the sync entry point: pushes a command
dict onto an asyncio queue via `run_coroutine_threadsafe` and returns
immediately.

`command_dispatcher()` is the async loop the FastAPI lifespan starts;
it drains the queue and submits each command to the provider. Each
command's `op` field maps to a handler in `_HANDLERS`. A handler
failure logs and skips to the next command.

The queue lives in process memory; commands queued during a crash or
shutdown are dropped. Operators rely on the next reconcile (run on
every webapp lifespan start) to restore meter state from DB.
"""

import asyncio
import logging
from typing import Any

from meter_driver_spec.http.models import (
    ConfigureElectricalMeterCompatRequest,
    ElectricalMeterConfiguration,
    RegisterNodeRequest,
    SetBalanceAndFlagsRequest,
)

from sparkmeter.metering.runtime_client import behavior_to_command, to_spec_decimal

logger = logging.getLogger(__name__)


_LOOP: asyncio.AbstractEventLoop | None = None
_QUEUE: asyncio.Queue | None = None


def register_loop(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
    global _LOOP, _QUEUE
    _LOOP = loop
    _QUEUE = queue


def unregister_loop() -> None:
    global _LOOP, _QUEUE
    _LOOP = None
    _QUEUE = None


def enqueue_command(cmd: dict[str, Any]) -> bool:
    """Sync API: push a command dict into the dispatcher queue.

    Returns True on success, False if the asyncio loop isn't running
    (e.g., during a CLI / management invocation). Callers tolerate
    False — sync paths shouldn't hard-depend on the provider being up.
    """
    loop = _LOOP
    queue = _QUEUE
    if loop is None or queue is None:
        logger.debug("metering dispatch loop not registered; dropping command op=%r", cmd.get("op"))
        return False
    try:
        asyncio.run_coroutine_threadsafe(queue.put(cmd), loop)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("failed to enqueue metering command op=%r", cmd.get("op"))
        return False


async def command_dispatcher(
    client,
    queue: asyncio.Queue,
    commands_allowed: asyncio.Event | None = None,
) -> None:
    """Drain the command queue, submitting each entry to the provider."""
    while True:
        cmd = await queue.get()
        if commands_allowed is not None:
            await commands_allowed.wait()
        op = cmd.get("op")
        handler = _HANDLERS.get(op)
        if handler is None:
            logger.warning("metering dispatch: unknown op=%r, dropping", op)
            continue

        try:
            await handler(client, cmd)
        except Exception:  # noqa: BLE001
            logger.exception("metering dispatch: handler op=%r failed", op)


# ----------------------------------------------------------------------
# Op handlers — build a spec command model and submit it (see runtime_client).
# ----------------------------------------------------------------------


async def _handle_register(client, cmd: dict) -> None:
    await client.register_node(
        RegisterNodeRequest(
            node_id=int(cmd["node_id"]),
            node_type=str(cmd.get("node_type", "SM5R")),
            mac=int(cmd["mac"]) if cmd.get("mac") is not None else None,
        )
    )


async def _handle_configure(client, cmd: dict) -> None:
    command = behavior_to_command(cmd.get("command"))
    if command is None:
        logger.warning(
            "metering dispatch: no spec command for behavior=%r on meter %s; configure dropped",
            cmd.get("command"),
            cmd.get("node_id"),
        )
        return
    await client.configure_meter(
        ConfigureElectricalMeterCompatRequest(
            node_id=int(cmd["node_id"]),
            command=command,
            configuration=ElectricalMeterConfiguration(
                power_limit=float(cmd.get("power_limit", 65535)),
                current_limit=float(cmd.get("current_limit", 65535)),
                startup_delay=int(cmd.get("startup_delay", 0)),
                throttle_on_time=int(cmd.get("throttle_on_time", 5)),
                throttle_off_time=int(cmd.get("throttle_off_time", 10)),
                throttle_count_limit=int(cmd.get("throttle_count_limit", 5)),
            ),
        )
    )


async def _handle_set_balance(client, cmd: dict) -> None:
    await client.set_balance(
        int(cmd["node_id"]),
        SetBalanceAndFlagsRequest(
            balance=to_spec_decimal(cmd.get("balance", 0)),
            low_balance_flag=bool(cmd.get("low_balance_flag", False)),
        ),
    )


async def _handle_unregister(client, cmd: dict) -> None:
    await client.unregister_node(int(cmd["node_id"]))


_HANDLERS = {
    "configure_meter": _handle_configure,
    "set_balance": _handle_set_balance,
    "register_meter": _handle_register,
    "unregister_meter": _handle_unregister,
}


def enqueue_disable_all(node_ids: list[int]) -> None:
    """Expand a broadcast disable into per-node configure_meter enqueues.

    The wire spec has no broadcast verb today; we fan out instead.
    """
    for node_id in node_ids:
        enqueue_command({"op": "configure_meter", "node_id": int(node_id), "command": "disable"})
