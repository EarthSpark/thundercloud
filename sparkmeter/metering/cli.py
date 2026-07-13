"""
Dynamic CLI generated from the metering provider's OpenAPI spec.

Walks the discriminated `Command` union from `_generated/`, introspects
each command's `params` dataclass, and builds a click command per
operation. New commands added to the spec auto-appear in the CLI on
the next `./scripts/regen-metering-wire.sh`.

Usage:
    flask metering register-meter --meter-id 42 --meter-type SM5R
    flask metering ping-meter --meter-id 42
    flask metering set-balance --meter-id 42 --balance 12.50
    flask metering configure-provider --heartbeat-seconds 900 \\
        --vendor-option channel=25 --vendor-option aes-key=00112233...

For commands with nested dataclass params (e.g. `configure-meter`'s
`configuration` and its inner `throttle`), fields are flattened with
dotted prefixes:

    flask metering configure-meter --meter-id 42 --behavior enable \\
        --configuration.power-limit-watts 1500 \\
        --configuration.current-limit-amps 10 \\
        --configuration.throttle.on-seconds 5 \\
        --configuration.throttle.off-seconds 10 \\
        --configuration.throttle.count-limit 5

The CLI submits the command via the generated `APIClient`, then tails
the SSE stream for any reply matching the correlation id (up to
~10 seconds), and prints each event one per line. Exit code is 0 on
`command_accepted` / `command_applied` / typed query reply, 1 on
`command_failed` / `command_rejected` / `command_timed_out`, 2 on
HTTP error.
"""

import asyncio
import dataclasses
import inspect
import json
import logging
import os
import types
import typing
import uuid
from enum import Enum
from typing import Any, AsyncIterator, Union, get_args, get_origin

import click
import httpx
from flask.cli import with_appcontext

from sparkmeter.metering._generated import APIClient, ClientConfig, HttpxTransport
from sparkmeter.metering._generated.models.submit_command_v_1_commands_post_request_body import (
    SubmitCommandV1CommandsPostRequestBodyDiscriminator,
)
from sparkmeter.metering._generated.models.submit_command_v_1_commands_post_request_body_command_type_enum import (
    SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum as CommandTypeEnum,
)

logger = logging.getLogger(__name__)


metering = click.Group(
    "metering",
    help="Metering-provider commands. Built dynamically from the OpenAPI spec.",
)


# ---------------------------------------------------------------------------
# Type → click option mapping
# ---------------------------------------------------------------------------


_NoneType = type(None)


def _unwrap_optional(tp: Any) -> tuple[Any, bool]:
    """Return `(inner_type, is_optional)`. `Optional[T]` ↔ `T | None`."""
    origin = get_origin(tp)
    if origin is Union or origin is types.UnionType:
        args = [a for a in get_args(tp) if a is not _NoneType]
        if len(args) == 1:
            return args[0], True
        # Non-Optional union (e.g. `float | str`); fall through to STRING input.
        return args[0], _NoneType in get_args(tp)
    return tp, False


def _resolve_param_class(command_class: type) -> type:
    """The `params` field's type is the command's params dataclass.

    For commands where `params` has a default (e.g. `params: FooParams | None = None`),
    `get_type_hints` returns the Union; unwrap to the dataclass.
    """
    field = next(f for f in dataclasses.fields(command_class) if f.name == "params")
    type_hints = typing.get_type_hints(command_class)
    raw_type = type_hints[field.name]
    inner, _ = _unwrap_optional(raw_type)
    return inner


def _options_for_dataclass(
    cls: type, prefix: tuple[str, ...] = ()
) -> list[tuple[tuple[str, ...], dataclasses.Field, Any]]:
    """Yield `(path_segments, field, resolved_type)` for every leaf field
    on `cls`. Recurses into REQUIRED nested dataclasses; optional
    nested dataclasses are skipped (operators can populate them via
    `--vendor-option` or use a hand-tuned CLI for that operation).
    """
    out: list[tuple[tuple[str, ...], dataclasses.Field, Any]] = []
    type_hints = typing.get_type_hints(cls)
    for f in dataclasses.fields(cls):
        raw_type = type_hints.get(f.name, f.type)
        inner, was_optional = _unwrap_optional(raw_type)
        if dataclasses.is_dataclass(inner):
            field_has_default = (
                f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING  # type: ignore[misc]
            )
            if was_optional or field_has_default:
                # Skip optional nested dataclasses to keep the CLI
                # surface manageable.
                continue
            out.extend(_options_for_dataclass(inner, prefix + (f.name,)))
        else:
            out.append((prefix + (f.name,), f, raw_type))
    return out


def _option_name(path: tuple[str, ...]) -> str:
    """`('configuration', 'throttle', 'on_seconds')` → '--configuration.throttle.on-seconds'."""
    return "--" + ".".join(seg.replace("_", "-") for seg in path)


def _option_dest(path: tuple[str, ...]) -> str:
    """`('configuration', 'throttle', 'on_seconds')` → 'configuration__throttle__on_seconds'."""
    return "__".join(path)


def _click_kwargs_for(field: dataclasses.Field, ftype: Any) -> dict[str, Any]:
    """Build click.option kwargs for a field of the given type."""
    is_optional = (
        field.default is not dataclasses.MISSING or field.default_factory is not dataclasses.MISSING  # type: ignore[misc]
    )
    # Detect a union of multiple non-None types (e.g. `float | str`).
    # Operators pass the value as a string; the dataclass accepts it.
    origin = get_origin(ftype)
    non_none_args = [a for a in get_args(ftype) if a is not _NoneType] if origin else []
    is_real_union = (origin is Union or origin is types.UnionType) and len(non_none_args) > 1

    inner, was_optional = _unwrap_optional(ftype)
    if was_optional:
        is_optional = True
        ftype = inner

    kwargs: dict[str, Any] = {"required": not is_optional}
    if field.default is not dataclasses.MISSING:
        kwargs["default"] = field.default
    elif field.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
        kwargs["default"] = None
    else:
        kwargs["default"] = None

    if is_real_union:
        kwargs["type"] = click.STRING
    elif isinstance(ftype, type) and issubclass(ftype, Enum):
        kwargs["type"] = click.Choice([e.value for e in ftype])
    elif ftype is bool:
        # A pair of flag options: --foo / --no-foo.
        kwargs["is_flag"] = True
    elif ftype is int:
        kwargs["type"] = click.INT
    elif ftype is float:
        kwargs["type"] = click.FLOAT
    elif ftype is bytes:
        kwargs["type"] = click.STRING
        kwargs["metavar"] = "HEX"
    else:
        # str, lists, etc. — fall back to STRING.
        # list[str] gets multiple=True so operators can pass --target-meters
        # several times.
        if get_origin(ftype) is list:
            kwargs["multiple"] = True
            kwargs.pop("default", None)
            if not is_optional:
                kwargs["required"] = True
        kwargs["type"] = click.STRING

    return kwargs


def _coerce_value(field: dataclasses.Field, ftype: Any, raw: Any) -> Any:
    """Convert click's parsed value into the dataclass's expected type."""
    if raw is None:
        return None
    inner, _ = _unwrap_optional(ftype)
    if isinstance(inner, type) and issubclass(inner, Enum):
        return inner(raw)
    if inner is bytes:
        try:
            return bytes.fromhex(raw)
        except ValueError as exc:
            raise click.BadParameter(f"--{field.name} must be valid hex") from exc
    if get_origin(inner) is list:
        return list(raw)
    return raw


# ---------------------------------------------------------------------------
# Vendor-options: free-form `KEY=VALUE` repeatable
# ---------------------------------------------------------------------------


def _parse_vendor_options(values: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for v in values:
        if "=" not in v:
            raise click.BadParameter(f"--vendor-option must be KEY=VALUE; got {v!r}")
        key, raw = v.split("=", 1)
        # Coerce simple types: digits → int, true/false → bool, else string.
        if raw.lstrip("-").isdigit():
            out[key] = int(raw)
        elif raw.lower() in ("true", "false"):
            out[key] = raw.lower() == "true"
        else:
            out[key] = raw
    return out


# ---------------------------------------------------------------------------
# Submission + reply tailing
# ---------------------------------------------------------------------------


def _provider_url() -> str:
    return os.environ.get("METERING_PROVIDER_URL", "http://localhost:8000")


def _make_client() -> tuple[APIClient, str]:
    client_id = "cli-" + uuid.uuid4().hex[:8]
    transport = HttpxTransport(
        base_url=_provider_url(),
        timeout=30.0,
        default_headers={"X-Client-Id": client_id},
    )
    return APIClient(ClientConfig(base_url=_provider_url()), transport=transport), client_id


_TERMINAL_EVENT_TYPES = frozenset(
    {
        "command_accepted",
        "command_applied",
        "command_rejected",
        "command_failed",
        "command_timed_out",
        "command_cached",
        "provider_status",
        "network_health",
        "capabilities",
        "meter_neighbors",
        "meter_config",
        "meter_version",
        "meter_instant_reading",
        "meter_errors",
        "firmware_update_status",
        "rf_test_result",
        "meter_memory",
        "meter_register",
    }
)

_FAILURE_EVENT_TYPES = frozenset({"command_failed", "command_rejected", "command_timed_out"})


async def _stream_events_raw(base_url: str, client_id: str) -> AsyncIterator[dict]:
    """Stream typed events as raw dicts.

    Bypasses the generated `stream_events_v1_events_get`: that method
    calls the transport's buffered `request()`, which never returns for
    an infinite SSE stream. Here we use `httpx.AsyncClient.stream()`
    explicitly so the response body is consumed line-by-line.
    """
    headers = {"X-Client-Id": client_id, "Accept": "text/event-stream"}
    async with httpx.AsyncClient(base_url=base_url, timeout=None) as client:
        async with client.stream(
            "GET",
            "/v1/events",
            params={"client_id": client_id},
            headers=headers,
        ) as response:
            response.raise_for_status()
            data_lines: list[str] = []
            async for line in response.aiter_lines():
                if line == "":
                    if data_lines:
                        yield json.loads("\n".join(data_lines))
                        data_lines = []
                elif line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())


async def _submit_and_tail(body: Any, correlation_id: str, timeout: float = 10.0) -> int:
    client, client_id = _make_client()
    try:
        async with client:
            try:
                await client.default.submit_command_v1_commands_post(body)
            except Exception as exc:  # noqa: BLE001
                click.echo(f"submit failed: {exc!r}", err=True)
                return 2

            exit_code = 0
            saw_terminal = False

            async def _consume() -> None:
                nonlocal exit_code, saw_terminal
                async for raw_event in _stream_events_raw(_provider_url(), client_id):
                    if raw_event.get("correlation_id") != correlation_id:
                        continue
                    event_type = raw_event.get("event_type", "?")
                    click.echo(json.dumps(raw_event, sort_keys=True))
                    if event_type in _TERMINAL_EVENT_TYPES:
                        saw_terminal = True
                        if event_type in _FAILURE_EVENT_TYPES:
                            exit_code = 1
                        return

            try:
                await asyncio.wait_for(_consume(), timeout=timeout)
            except asyncio.TimeoutError:
                if not saw_terminal:
                    click.echo("(no reply within timeout)", err=True)
                    exit_code = 1

            return exit_code
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Build a click command for one Command class
# ---------------------------------------------------------------------------


def _command_name(command_type_value: str) -> str:
    return command_type_value.replace("_", "-")


def _build_click_command(command_class: type, command_type_enum_value: str) -> click.Command:
    params_class = _resolve_param_class(command_class)
    leaf_options = _options_for_dataclass(params_class)
    type_hints_cache: dict[type, dict[str, Any]] = {}

    def _hints(cls: type) -> dict[str, Any]:
        if cls not in type_hints_cache:
            type_hints_cache[cls] = typing.get_type_hints(cls)
        return type_hints_cache[cls]

    def _build_params(kwargs: dict[str, Any]) -> Any:
        """Reconstruct the nested dataclass tree from flat kwargs.

        Mirrors `_options_for_dataclass`: only required nested
        dataclasses are constructed; optional ones are left at their
        default (typically None).
        """

        def build(cls: type, prefix: tuple[str, ...]) -> Any:
            init_kwargs: dict[str, Any] = {}
            for f in dataclasses.fields(cls):
                ftype = _hints(cls).get(f.name, f.type)
                inner, was_optional = _unwrap_optional(ftype)
                field_has_default = (
                    f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING  # type: ignore[misc]
                )
                if dataclasses.is_dataclass(inner):
                    if was_optional or field_has_default:
                        # Skip — the optional nested dataclass stays at
                        # its default (None or factory result).
                        continue
                    init_kwargs[f.name] = build(inner, prefix + (f.name,))
                else:
                    dest = _option_dest(prefix + (f.name,))
                    raw = kwargs.get(dest)
                    if raw is None and field_has_default:
                        continue
                    init_kwargs[f.name] = _coerce_value(f, ftype, raw)
            return cls(**init_kwargs)

        return build(params_class, ())

    @click.pass_context
    def callback(ctx: click.Context, **kwargs: Any) -> None:
        correlation_id = kwargs.pop("correlation_id", None) or "cli-" + uuid.uuid4().hex[:12]
        vendor_option_values = kwargs.pop("vendor_option", ())
        vendor_options_dict = _parse_vendor_options(vendor_option_values)

        params = _build_params(kwargs)

        cmd_kwargs: dict[str, Any] = {
            "command_type": CommandTypeEnum(command_type_enum_value),
            "correlation_id": correlation_id,
            "params": params,
        }
        # vendor_options is the same wrapper class per command type;
        # construct via the cattrs structure-from-dict helper so we
        # don't have to import ~20 vendor-options modules here.
        if vendor_options_dict:
            from sparkmeter.metering._generated.core.cattrs_converter import structure_from_dict

            vendor_options_class = next(
                f for f in dataclasses.fields(command_class) if f.name == "vendor_options"
            )
            inner_cls, _ = _unwrap_optional(_hints(command_class)[vendor_options_class.name])
            cmd_kwargs["vendor_options"] = structure_from_dict(vendor_options_dict, inner_cls)

        body = command_class(**cmd_kwargs)
        ctx.exit(asyncio.run(_submit_and_tail(body, correlation_id)))

    callback = with_appcontext(callback)

    cmd = click.command(_command_name(command_type_enum_value), help=_command_help(command_class))(callback)

    # Apply options last-to-first so they appear in declaration order.
    for path, field, ftype in reversed(leaf_options):
        kwargs = _click_kwargs_for(field, ftype)
        cmd = click.option(_option_name(path), _option_dest(path), **kwargs)(cmd)
    cmd = click.option(
        "--vendor-option",
        "vendor_option",
        multiple=True,
        metavar="KEY=VALUE",
        help="Vendor-specific option, repeatable.",
    )(cmd)
    cmd = click.option(
        "--correlation-id",
        default=None,
        help="Correlation id; auto-generated if omitted.",
    )(cmd)
    return cmd


def _command_help(command_class: type) -> str:
    doc = inspect.getdoc(command_class) or ""
    return doc.split("\n\n")[0]  # first paragraph


# ---------------------------------------------------------------------------
# Register one command per discriminated-union variant
# ---------------------------------------------------------------------------


def _register_all() -> None:
    discriminator = SubmitCommandV1CommandsPostRequestBodyDiscriminator()
    mapping = discriminator.get_mapping()
    for command_type_value, command_class in mapping.items():
        try:
            cmd = _build_click_command(command_class, command_type_value)
        except Exception:  # noqa: BLE001
            logger.exception("failed to build CLI for %s; skipping", command_class.__name__)
            continue
        metering.add_command(cmd)


_register_all()
