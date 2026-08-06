"""
Startup reconcile: re-register every meter in DB with the metering
provider on every webapp lifespan start.

The provider holds no durable per-meter state across restarts. This
module re-issues the full sequence on every webapp boot:

    configure_provider (heartbeat + vendor net params)
    for each meter in DB:
        register_meter
        configure_meter (limits + behavior verb)
        set_balance (if a balance is set)

DB queries here are blocking SQLAlchemy; they run in
`asyncio.to_thread` so the SSE consumer keeps draining events during
reconcile.
"""

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any, Optional

from meter_driver_spec.http.models import (
    ConfigureElectricalMeterCompatRequest,
    ElectricalMeterConfiguration,
    RegisterNodeRequest,
    SetBalanceAndFlagsRequest,
)
from past.utils import old_div

from sparkmeter.metering.runtime_client import behavior_to_command, to_spec_decimal

if TYPE_CHECKING:
    from flask import Flask

    from sparkmeter.metering.runtime_client import MeteringCommandClient

logger = logging.getLogger(__name__)
_AES_KEY_HEX_RE = re.compile(r"^[0-9a-fA-F]{32}$")


_KNOWN_METER_TYPES = {
    "SM5R",
    "SM5XR",
    "SM15R",
    "SM20R",
    "SM20XR",
    "SM60R",
    "SM60RP",
    "SM100E",
    "SM200E",
    "SMRSD",
    "SMRPI",
    "SMRSDRF",
    "SMRSDPLC",
    "SMRPIRF",
    "SMRPIPLC",
    "SM16R",
    "SMHCE",
}


async def reconcile_all(
    client: "MeteringCommandClient",
    flask_app: "Flask",
    *,
    skip_provider_init: bool = False,
) -> None:
    """Read all meters from DB and register them with the provider.

    `flask_app` is passed in explicitly because the DB loaders below run
    in worker threads via `asyncio.to_thread`, and Flask's `current_app`
    proxy is bound to a per-request thread-local that those worker
    threads never enter. The loaders push an explicit app context using
    this Flask instance.

    `skip_provider_init` is used when the caller has already issued the
    vendor-specific provider init for this runtime transition and only
    needs the per-meter reconcile sequence.
    """
    logger.info("metering reconcile: starting")

    if not skip_provider_init:
        driver_init_payload = await asyncio.to_thread(_load_driver_init_payload, flask_app)
        if driver_init_payload is not None:
            await client.init_driver(driver_init_payload)

    meters_data = await asyncio.to_thread(_load_meters, flask_app)
    logger.info("metering reconcile: registering %d meters", len(meters_data))

    for m in meters_data:
        try:
            logger.info(
                "metering reconcile: registering meter_id=%s type=%s",
                m.get("meter_id"),
                m.get("meter_type"),
            )
            await client.register_node(_build_register(m))

            cfg = _build_configure(m)
            if cfg is not None:
                logger.info(
                    "metering reconcile: configuring meter_id=%s behavior=%s power_limit=%s current_limit=%s",
                    m.get("meter_id"),
                    cfg.command.value,
                    cfg.configuration.power_limit,
                    cfg.configuration.current_limit,
                )
                await client.configure_meter(cfg)
            else:
                logger.warning(
                    "metering reconcile: skipping configure for meter_id=%s because no config payload was derived",
                    m.get("meter_id"),
                )

            balance = _build_balance(m)
            if balance is not None:
                logger.info(
                    "metering reconcile: setting balance for meter_id=%s low_balance=%s",
                    m.get("meter_id"),
                    balance.low_balance_flag,
                )
                await client.set_balance(int(m["meter_id"]), balance)
        except Exception:  # noqa: BLE001
            logger.exception("metering reconcile: failed for meter_id=%s", m.get("meter_id", "?"))

    logger.info("metering reconcile: done (%d meters registered)", len(meters_data))


# ----------------------------------------------------------------------
# Data loaders — blocking SQLAlchemy queries, run in a thread.
# ----------------------------------------------------------------------


def _load_driver_init_payload(flask_app: "Flask") -> dict[str, Any] | None:
    try:
        from sparkmeter.config.provider_settings import (
            get_enabled_provider,
            load_provider_runtime_settings,
        )
    except ImportError:
        return None

    # Config reads can touch Flask extensions / SQLAlchemy session state,
    # so wrap the whole body in an explicit app context. This function
    # runs inside `asyncio.to_thread`, which spawns a fresh OS thread
    # with no Flask context.
    with flask_app.app_context():
        enabled_provider = get_enabled_provider()
        driver_config = load_provider_runtime_settings(enabled_provider)
        driver_field_values = ((driver_config or {}).get("field_values")) or {}
        aes_key_hex = driver_field_values.get("aes_key")
        if not aes_key_hex:
            return None

        heartbeat = driver_field_values.get("heartbeat_period_duration")
        if heartbeat in (None, ""):
            return None

        payload: dict[str, Any] = {
            "heartbeat_period_duration": int(heartbeat),
            "aes_key": str(aes_key_hex).strip(),
        }
        channel = driver_field_values.get("channel")
        if channel is not None:
            try:
                payload["channel"] = int(channel)
            except (TypeError, ValueError):
                logger.warning(
                    "metering reconcile: skipping invalid channel %r; expected integer",
                    channel,
                )
        aes_key = payload["aes_key"]
        if not _AES_KEY_HEX_RE.fullmatch(aes_key):
            logger.warning(
                "metering reconcile: skipping invalid driver AES key %r; expected 32 hex characters",
                aes_key_hex,
            )
            return None

        return payload


def _load_meters(flask_app: "Flask") -> list[dict[str, Any]]:
    """Load all meters from DB as plain dicts.

    Runs inside `asyncio.to_thread`. The caller passes the Flask app
    explicitly because the lifespan worker thread has no Flask context;
    `current_app` would raise `RuntimeError: Working outside of
    application context`.
    """
    from sparkmeter.meter.meterdomain import Meter
    from sparkmeter.models import session_scope

    rows: list[dict[str, Any]] = []
    with flask_app.app_context(), session_scope():
        for meter in Meter.query.all():
            rows.append(
                {
                    "meter_id": str(meter.code),
                    "meter_type": _resolve_meter_type(meter),
                    "mac": int(meter.code),
                    "balance": _balance_of(meter),
                    "low_balance": _low_balance_of(meter),
                    "config": _config_of(meter),
                    "is_active": _is_active(meter),
                }
            )
    return rows


# ----------------------------------------------------------------------
# Per-meter command builders
# ----------------------------------------------------------------------


def _build_register(m: dict) -> RegisterNodeRequest:
    return RegisterNodeRequest(
        node_id=int(m["meter_id"]),
        node_type=str(m.get("meter_type") or "SM5R"),
        mac=int(m["mac"]) if m.get("mac") is not None else None,
    )


def _build_configure(m: dict) -> Optional[ConfigureElectricalMeterCompatRequest]:
    config = m.get("config")
    if config is None:
        return None
    behavior_name = str(config.get("behavior") or "").strip().lower()
    if not behavior_name:
        behavior_name = "enable" if m.get("is_active") else "disable"
    behavior = "enable" if behavior_name == "enable" else "disable"
    command = behavior_to_command(behavior)
    if command is None:
        return None
    return ConfigureElectricalMeterCompatRequest(
        node_id=int(m["meter_id"]),
        command=command,
        configuration=ElectricalMeterConfiguration(
            power_limit=float(config.get("power_limit") or 65535),
            current_limit=float(config.get("current_limit") or 65535),
            startup_delay=int(config.get("startup_delay") or 0),
            throttle_on_time=int(config.get("throttle_on_time") or 5),
            throttle_off_time=int(config.get("throttle_off_time") or 10),
            throttle_count_limit=int(config.get("throttle_count_limit") or 5),
        ),
    )


def _build_balance(m: dict) -> Optional[SetBalanceAndFlagsRequest]:
    balance = m.get("balance")
    if balance is None:
        return None
    return SetBalanceAndFlagsRequest(
        balance=to_spec_decimal(balance),
        low_balance_flag=bool(m.get("low_balance")),
    )


# ----------------------------------------------------------------------
# Adapters from existing meter model fields to reconcile dict shape.
# ----------------------------------------------------------------------


def _resolve_meter_type(meter) -> str:
    model = getattr(meter, "model", None)
    if model is None:
        return "SM5R"
    name = (getattr(model, "name", "") or "").upper().strip()
    if name in _KNOWN_METER_TYPES:
        return name
    return "SM5R"


def _balance_of(meter):
    billing = getattr(meter, "billing", None)
    if billing is None:
        return None
    return getattr(billing, "balance", None)


def _low_balance_of(meter):
    billing = getattr(meter, "billing", None)
    if billing is None:
        return False
    return bool(getattr(billing, "low_balance", False))


def _config_of(meter) -> dict | None:
    cfg = getattr(meter, "config", None)
    if cfg is None:
        return None
    if not meter.is_customer_meter():
        return None

    try:
        from sparkmeter.config.configparameter import parameters
        from sparkmeter.meter.meterdomain import MeterConfig
    except ImportError:
        return None

    try:
        override_meter_state = meter.ground.private.override_meter_state
        nominal_voltage = parameters.NOMINAL_VOLTAGE
        tariff_load_limit = meter.tariff.get_current_load_limit()
        continuous_power = meter.continuous_current_limit * nominal_voltage
        provider_uses_engineering_units = bool(getattr(meter, "provider_id", None))
        power_limit = min(continuous_power, tariff_load_limit)
        if not provider_uses_engineering_units:
            power_limit = old_div(power_limit, meter.scalars.power_scalar)
        current_limit = meter.model.inrush_limit
        if not provider_uses_engineering_units:
            current_limit = old_div(current_limit, meter.scalars.current_scalar)
        current_limit = min(current_limit, 65535)
        behavior = (
            "enable" if meter.state_value == MeterConfig.STATE_ON and not override_meter_state else "disable"
        )
    except Exception:  # noqa: BLE001
        logger.exception("metering reconcile: failed to derive config for meter %s", meter.code)
        return None

    return {
        "behavior": behavior,
        "power_limit": float(power_limit),
        "current_limit": float(current_limit),
        "startup_delay": int(getattr(cfg, "startup_delay", None) or 0),
        "throttle_on_time": int(getattr(cfg, "throttle_on_time", None) or 5),
        "throttle_off_time": int(getattr(cfg, "throttle_off_time", None) or 10),
        "throttle_count_limit": int(getattr(cfg, "throttle_count_limit", None) or 5),
    }


def _is_active(meter) -> bool:
    return bool(getattr(meter, "is_active", True))
