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
import uuid
from typing import Any

from sparkmeter.metering._generated import APIClient
from sparkmeter.metering._generated.models.configure_meter_command import ConfigureMeterCommand
from sparkmeter.metering._generated.models.configure_meter_params import ConfigureMeterParams
from sparkmeter.metering._generated.models.meter_behavior_command import MeterBehaviorCommand
from sparkmeter.metering._generated.models.meter_configuration import MeterConfiguration
from sparkmeter.metering._generated.models.register_meter_command import RegisterMeterCommand
from sparkmeter.metering._generated.models.register_meter_command_vendor_options import \
    RegisterMeterCommandVendorOptions
from sparkmeter.metering._generated.models.register_meter_params import RegisterMeterParams
from sparkmeter.metering._generated.models.set_balance_command import SetBalanceCommand
from sparkmeter.metering._generated.models.set_balance_params import SetBalanceParams
from sparkmeter.metering._generated.models.submit_command_v_1_commands_post_request_body_command_type_enum import \
    SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum as CommandTypeEnum
from sparkmeter.metering._generated.models.throttle_config import ThrottleConfig
from sparkmeter.metering._generated.models.unregister_meter_command import UnregisterMeterCommand
from sparkmeter.metering._generated.models.unregister_meter_params import UnregisterMeterParams

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
        logger.debug(
            "metering dispatch loop not registered; dropping command op=%r", cmd.get("op")
        )
        return False
    try:
        asyncio.run_coroutine_threadsafe(queue.put(cmd), loop)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("failed to enqueue metering command op=%r", cmd.get("op"))
        return False


async def command_dispatcher(client: APIClient, queue: asyncio.Queue) -> None:
    """Drain the command queue, submitting each entry to the provider."""
    while True:
        cmd = await queue.get()
        op = cmd.get("op")
        handler = _HANDLERS.get(op)
        if handler is None:
            logger.warning("metering dispatch: unknown op=%r, dropping", op)
            continue

        try:
            body = handler(cmd)
            await client.default.submit_command_v1_commands_post(body)
        except Exception:  # noqa: BLE001
            logger.exception("metering dispatch: handler op=%r failed", op)


def _correlation_id(cmd: dict[str, Any]) -> str:
    return cmd.get("correlation_id") or "dispatch-" + uuid.uuid4().hex[:12]


# ----------------------------------------------------------------------
# Op handlers — build a typed Command body from the legacy dict shape.
# ----------------------------------------------------------------------


_BEHAVIOR_FROM_STR = {
    "none": MeterBehaviorCommand.NONE,
    "enable": MeterBehaviorCommand.ENABLE,
    "disable": MeterBehaviorCommand.DISABLE,
    "reboot": MeterBehaviorCommand.REBOOT,
    "calibrate_start": MeterBehaviorCommand.CALIBRATE_START,
    "calibrate_finish": MeterBehaviorCommand.CALIBRATE_FINISH,
    "enter_unprovisioned": MeterBehaviorCommand.ENTER_UNPROVISIONED,
}


def _build_configure_meter(cmd: dict) -> ConfigureMeterCommand:
    behavior_str = (cmd.get("command") or "none").lower().strip()
    behavior = _BEHAVIOR_FROM_STR.get(behavior_str, MeterBehaviorCommand.NONE)
    return ConfigureMeterCommand(
        command_type=CommandTypeEnum.CONFIGURE_METER,
        correlation_id=_correlation_id(cmd),
        params=ConfigureMeterParams(
            meter_id=str(cmd["node_id"]),
            behavior=behavior,
            configuration=MeterConfiguration(
                power_limit_watts=float(cmd.get("power_limit", 65535)),
                current_limit_amps=float(cmd.get("current_limit", 65535)),
                startup_delay_seconds=int(cmd.get("startup_delay", 0)),
                throttle=ThrottleConfig(
                    on_seconds=int(cmd.get("throttle_on_time", 5)),
                    off_seconds=int(cmd.get("throttle_off_time", 10)),
                    count_limit=int(cmd.get("throttle_count_limit", 5)),
                ),
            ),
        ),
    )


def _build_set_balance(cmd: dict) -> SetBalanceCommand:
    # Balance is `float | str`; pass as string to preserve precision.
    return SetBalanceCommand(
        command_type=CommandTypeEnum.SET_BALANCE,
        correlation_id=_correlation_id(cmd),
        params=SetBalanceParams(
            balance=str(cmd.get("balance", 0)),
            meter_id=str(cmd["node_id"]),
            low_balance=bool(cmd.get("low_balance_flag", False)),
        ),
    )


def _build_register_meter(cmd: dict) -> RegisterMeterCommand:
    vendor_options = RegisterMeterCommandVendorOptions()
    if cmd.get("mac") is not None:
        vendor_options["mac"] = int(cmd["mac"])
    return RegisterMeterCommand(
        command_type=CommandTypeEnum.REGISTER_METER,
        correlation_id=_correlation_id(cmd),
        vendor_options=vendor_options if vendor_options else None,
        params=RegisterMeterParams(
            meter_id=str(cmd["node_id"]),
            meter_type=str(cmd.get("node_type", "SM5R")),
        ),
    )


def _build_unregister_meter(cmd: dict) -> UnregisterMeterCommand:
    return UnregisterMeterCommand(
        command_type=CommandTypeEnum.UNREGISTER_METER,
        correlation_id=_correlation_id(cmd),
        params=UnregisterMeterParams(meter_id=str(cmd["node_id"])),
    )


def _build_disable_all(cmd: dict) -> ConfigureMeterCommand:
    """Fan-out broadcast as per-node configure_meter is handled at the
    queue level by enqueuing individual commands. This handler isn't
    used directly; `enqueue_command({"op": "disable_all", ...})` is
    expanded by `dispatch.enqueue_disable_all` into per-node enqueues.
    """
    raise RuntimeError("disable_all should be expanded before reaching the handler")


_HANDLERS = {
    "configure_meter": _build_configure_meter,
    "set_balance": _build_set_balance,
    "register_meter": _build_register_meter,
    "unregister_meter": _build_unregister_meter,
}


def enqueue_disable_all(node_ids: list[int]) -> None:
    """Expand a broadcast disable into per-node configure_meter enqueues.

    The wire spec has no broadcast verb today; we fan out instead.
    """
    for node_id in node_ids:
        enqueue_command(
            {"op": "configure_meter", "node_id": int(node_id), "command": "disable"}
        )
