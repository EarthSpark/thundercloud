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
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sparkmeter.metering._generated.models.configure_meter_command import ConfigureMeterCommand
from sparkmeter.metering._generated.models.configure_meter_params import ConfigureMeterParams
from sparkmeter.metering._generated.models.configure_provider_command import \
    ConfigureProviderCommand
from sparkmeter.metering._generated.models.configure_provider_command_vendor_options import \
    ConfigureProviderCommandVendorOptions
from sparkmeter.metering._generated.models.configure_provider_params import ConfigureProviderParams
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

if TYPE_CHECKING:
    from flask import Flask

    from sparkmeter.metering._generated import APIClient

logger = logging.getLogger(__name__)


_KNOWN_METER_TYPES = {
    "SM5R", "SM5XR", "SM15R", "SM20R", "SM20XR", "SM60R", "SM60RP",
    "SM100E", "SM200E", "SMRSD", "SMRPI", "SMRSDRF", "SMRSDPLC",
    "SMRPIRF", "SMRPIPLC", "SM16R", "SMHCE",
}


async def reconcile_all(client: "APIClient", flask_app: "Flask") -> None:
    """Read all meters from DB and register them with the provider.

    `flask_app` is passed in explicitly because the DB loaders below run
    in worker threads via `asyncio.to_thread`, and Flask's `current_app`
    proxy is bound to a per-request thread-local that those worker
    threads never enter. The loaders push an explicit app context using
    this Flask instance.
    """
    logger.info("metering reconcile: starting")

    provider_cmd = await asyncio.to_thread(_load_provider_command, flask_app)
    if provider_cmd is not None:
        await client.default.submit_command_v1_commands_post(provider_cmd)

    meters_data = await asyncio.to_thread(_load_meters, flask_app)
    logger.info("metering reconcile: registering %d meters", len(meters_data))

    for m in meters_data:
        try:
            await client.default.submit_command_v1_commands_post(_build_register(m))

            cfg = _build_configure(m)
            if cfg is not None:
                await client.default.submit_command_v1_commands_post(cfg)

            balance = _build_balance(m)
            if balance is not None:
                await client.default.submit_command_v1_commands_post(balance)
        except Exception:  # noqa: BLE001
            logger.exception(
                "metering reconcile: failed for meter_id=%s", m.get("meter_id", "?")
            )

    logger.info("metering reconcile: done (%d meters registered)", len(meters_data))


# ----------------------------------------------------------------------
# Data loaders — blocking SQLAlchemy queries, run in a thread.
# ----------------------------------------------------------------------


def _load_provider_command(flask_app: "Flask") -> Optional[ConfigureProviderCommand]:
    try:
        from sparkmeter.config.configdict import config
        from sparkmeter.config.configparameter import parameters
    except ImportError:
        return None

    # Config reads can touch Flask extensions / SQLAlchemy session state,
    # so wrap the whole body in an explicit app context. This function
    # runs inside `asyncio.to_thread`, which spawns a fresh OS thread
    # with no Flask context.
    with flask_app.app_context():
        heartbeat = config.get("HEARTBEAT_PERIOD")
        if heartbeat is None:
            return None

        vendor_options = ConfigureProviderCommandVendorOptions()
        channel = getattr(parameters, "RADIO_CHANNEL", None)
        aes_key_hex = getattr(parameters, "RADIO_AES_KEY", None)
        if channel is not None:
            try:
                vendor_options["channel"] = int(channel)
            except (TypeError, ValueError):
                pass
        if aes_key_hex:
            try:
                vendor_options["aes_key"] = str(aes_key_hex)
            except (TypeError, ValueError):
                logger.warning("metering reconcile: invalid RADIO_AES_KEY, skipping")

        return ConfigureProviderCommand(
            command_type=CommandTypeEnum.CONFIGURE_PROVIDER,
            correlation_id="reconcile-" + uuid.uuid4().hex[:12],
            vendor_options=vendor_options if vendor_options else None,
            # HEARTBEAT_PERIOD is in minutes in the existing config; the
            # provider takes seconds.
            params=ConfigureProviderParams(heartbeat_seconds=int(heartbeat) * 60),
        )


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


def _build_register(m: dict) -> RegisterMeterCommand:
    vendor_options = RegisterMeterCommandVendorOptions()
    if m.get("mac") is not None:
        vendor_options["mac"] = int(m["mac"])
    return RegisterMeterCommand(
        command_type=CommandTypeEnum.REGISTER_METER,
        correlation_id="reconcile-register-" + uuid.uuid4().hex[:12],
        vendor_options=vendor_options if vendor_options else None,
        params=RegisterMeterParams(
            meter_id=str(m["meter_id"]),
            meter_type=str(m.get("meter_type") or "SM5R"),
        ),
    )


def _build_configure(m: dict) -> Optional[ConfigureMeterCommand]:
    config = m.get("config")
    if config is None:
        return None
    behavior = (
        MeterBehaviorCommand.ENABLE if m.get("is_active") else MeterBehaviorCommand.DISABLE
    )
    return ConfigureMeterCommand(
        command_type=CommandTypeEnum.CONFIGURE_METER,
        correlation_id="reconcile-configure-" + uuid.uuid4().hex[:12],
        params=ConfigureMeterParams(
            meter_id=str(m["meter_id"]),
            behavior=behavior,
            configuration=MeterConfiguration(
                power_limit_watts=float(config.get("power_limit") or 65535),
                current_limit_amps=float(config.get("current_limit") or 65535),
                startup_delay_seconds=int(config.get("startup_delay") or 0),
                throttle=ThrottleConfig(
                    on_seconds=int(config.get("throttle_on_time") or 5),
                    off_seconds=int(config.get("throttle_off_time") or 10),
                    count_limit=int(config.get("throttle_count_limit") or 5),
                ),
            ),
        ),
    )


def _build_balance(m: dict) -> Optional[SetBalanceCommand]:
    balance = m.get("balance")
    if balance is None:
        return None
    return SetBalanceCommand(
        command_type=CommandTypeEnum.SET_BALANCE,
        correlation_id="reconcile-balance-" + uuid.uuid4().hex[:12],
        params=SetBalanceParams(
            balance=str(Decimal(str(balance))),
            meter_id=str(m["meter_id"]),
            low_balance=bool(m.get("low_balance")),
        ),
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
    return {
        "power_limit": getattr(cfg, "power_limit", None),
        "current_limit": getattr(cfg, "current_limit", None),
        "startup_delay": getattr(cfg, "startup_delay", None),
        "throttle_on_time": getattr(cfg, "throttle_on_time", None),
        "throttle_off_time": getattr(cfg, "throttle_off_time", None),
        "throttle_count_limit": getattr(cfg, "throttle_count_limit", None),
    }


def _is_active(meter) -> bool:
    return bool(getattr(meter, "is_active", True))
