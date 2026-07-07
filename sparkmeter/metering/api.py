"""
Sync-callable surface for the rest of the webapp.

The seam between sync Flask domain code and the async generated client
owned by the FastAPI lifespan. Each function here builds a dict and
pushes it onto the dispatch queue (fire-and-forget; the caller does
not wait for the operation to complete).

When the FastAPI lifespan isn't running (CLI / management scripts,
unit tests), enqueues drop silently — sync paths shouldn't hard-depend
on the metering provider being up.
"""

import logging

from sparkmeter.metering import dispatch

logger = logging.getLogger(__name__)


def send_set_config(
    mac: int,
    command: str,
    load_limit: float | int,
    subnet: int,
    current_limit: float | int,
    balance,
    low_balance: bool,
    firmware_version,
) -> None:
    """Configure a meter and (optionally) update its display balance.

    `command` is the legacy 'enable'/'disable' string; the dispatcher
    maps it to the wire `behavior` enum. `subnet` and `firmware_version`
    are unused at the wire level today; kept in the signature so
    existing callers don't need to change.
    """
    dispatch.enqueue_command(
        {
            "op": "configure_meter",
            "node_id": int(mac),
            "command": command,
            "power_limit": float(load_limit),
            "current_limit": float(current_limit),
        }
    )

    if balance is not None:
        dispatch.enqueue_command(
            {
                "op": "set_balance",
                "node_id": int(mac),
                "balance": balance,
                "low_balance_flag": bool(low_balance),
            }
        )


def disable_all_meters(node_ids: list[int] | None = None) -> None:
    """Disable every customer meter at the radio level.

    If `node_ids` is None, the function loads the active customer-meter
    codes from DB.
    """
    if node_ids is None:
        try:
            from flask import current_app

            from sparkmeter.meter.meterdomain import Meter
            from sparkmeter.models import session_scope

            with current_app.app_context(), session_scope():
                node_ids = [
                    m.code
                    for m in Meter.query.filter_by(
                        meter_type=Meter.TYPE_CUSTOMER
                    ).all()
                ]
        except Exception:  # noqa: BLE001
            logger.exception("disable_all_meters: failed to load meter list")
            return

    dispatch.enqueue_disable_all([int(n) for n in node_ids])


def register_meter(node_id: int, node_type: str, mac: int | None = None) -> None:
    dispatch.enqueue_command(
        {
            "op": "register_meter",
            "node_id": int(node_id),
            "node_type": str(node_type),
            "mac": int(mac) if mac is not None else None,
        }
    )


def unregister_meter(node_id: int) -> None:
    dispatch.enqueue_command({"op": "unregister_meter", "node_id": int(node_id)})


# Backwards-compatible aliases for existing callers.
def register_node(node_id: int, node_type: str, mac: int | None = None) -> None:
    register_meter(node_id, node_type, mac)


def unregister_node(node_id: int) -> None:
    unregister_meter(node_id)
