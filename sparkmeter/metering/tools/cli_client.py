"""
CLI helpers for one-off metering-provider commands.

Used by Flask CLI commands (e.g. `flask meter ping`) that fan out a
single command across some set of meters and print whatever the
provider returns.

Each helper:
1. opens an `APIClient` against the metering provider URL
2. submits the command with a fresh correlation id
3. tails the SSE stream long enough to surface the matching reply
4. prints a one-line summary per meter

Failure cases (provider down, `command_failed` reason="unsupported",
`command_timed_out`) print to stderr and contribute to the exit code.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from collections.abc import Awaitable, Callable

import click

from sparkmeter.metering._generated import APIClient, ClientConfig, HttpxTransport
from sparkmeter.metering._generated.models.ping_meter_command import PingMeterCommand
from sparkmeter.metering._generated.models.ping_meter_params import PingMeterParams
from sparkmeter.metering._generated.models.query_meter_neighbors_command import \
    QueryMeterNeighborsCommand
from sparkmeter.metering._generated.models.query_meter_neighbors_params import \
    QueryMeterNeighborsParams
from sparkmeter.metering._generated.models.submit_command_v_1_commands_post_request_body_command_type_enum import \
    SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum as CommandTypeEnum

logger = logging.getLogger(__name__)


PROVIDER_URL_DEFAULT = os.environ.get("METERING_PROVIDER_URL", "http://localhost:8000")
PER_METER_TIMEOUT_SECONDS = 10.0


def _make_client() -> APIClient:
    """Open a short-lived client against the configured provider URL."""
    client_id = "cli-" + uuid.uuid4().hex[:8]
    transport = HttpxTransport(
        base_url=PROVIDER_URL_DEFAULT,
        timeout=30.0,
        default_headers={"X-Client-Id": client_id},
    )
    return APIClient(ClientConfig(base_url=PROVIDER_URL_DEFAULT), transport=transport)


async def submit_ping(client: APIClient, meter_id: str, correlation_id: str) -> None:
    body = PingMeterCommand(
        command_type=CommandTypeEnum.PING_METER,
        correlation_id=correlation_id,
        params=PingMeterParams(meter_id=meter_id),
    )
    await client.default.submit_command_v1_commands_post(body)


async def submit_query_neighbors(
    client: APIClient, meter_id: str, correlation_id: str
) -> None:
    body = QueryMeterNeighborsCommand(
        command_type=CommandTypeEnum.QUERY_METER_NEIGHBORS,
        correlation_id=correlation_id,
        params=QueryMeterNeighborsParams(meter_id=meter_id),
    )
    await client.default.submit_command_v1_commands_post(body)


CommandSubmitter = Callable[[APIClient, str, str], Awaitable[None]]


async def run_per_meter_command(
    submitter: CommandSubmitter, meter_ids: list[str]
) -> None:
    """Submit `submitter` for each meter, then tail SSE for replies.

    Per-meter outcome is printed on a single line. Exit code is 0 on
    success, 1 if any meter's reply is `command_failed` or
    `command_timed_out`, 2 if the provider is unreachable.
    """
    if not meter_ids:
        click.echo("no meters to query", err=True)
        return

    correlation_to_meter: dict[str, str] = {
        f"cli-{uuid.uuid4().hex[:12]}": mid for mid in meter_ids
    }
    pending = set(correlation_to_meter)

    client = _make_client()
    try:
        async with client:
            try:
                for correlation_id, meter_id in correlation_to_meter.items():
                    await submitter(client, meter_id, correlation_id)
            except Exception as exc:  # noqa: BLE001
                click.echo(f"failed to submit to provider: {exc!r}", err=True)
                sys.exit(2)

            await _tail_until_resolved(
                client, correlation_to_meter, pending
            )
    finally:
        # Already inside `async with client` — but ensure close in case
        # of exception paths; APIClient.close is idempotent.
        await client.close()

    if pending:
        sys.exit(1)


async def _tail_until_resolved(
    client: APIClient,
    correlation_to_meter: dict[str, str],
    pending: set[str],
) -> None:
    deadline = asyncio.get_event_loop().time() + PER_METER_TIMEOUT_SECONDS

    async def _consume() -> None:
        async for raw_event in client.default.stream_events_v1_events_get():
            corr = raw_event.get("correlation_id")
            if corr not in correlation_to_meter or corr not in pending:
                continue
            meter_id = correlation_to_meter[corr]
            event_type = raw_event.get("event_type", "?")
            if event_type in {
                "command_applied",
                "command_failed",
                "command_timed_out",
                "command_rejected",
                "meter_neighbors",
                "meter_config",
                "meter_version",
                "meter_instant_reading",
                "meter_errors",
                "rf_test_result",
            }:
                pending.discard(corr)
                _print_summary(meter_id, event_type, raw_event)
            if not pending:
                return

    try:
        await asyncio.wait_for(_consume(), timeout=PER_METER_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        for corr in list(pending):
            meter_id = correlation_to_meter[corr]
            click.echo(f"{meter_id}: timed out waiting for reply", err=True)
    if asyncio.get_event_loop().time() >= deadline:
        return


def _print_summary(meter_id: str, event_type: str, raw: dict) -> None:
    """Print a single-line summary of an event for a meter."""
    if event_type == "command_failed":
        reason = raw.get("reason", "?")
        click.echo(f"{meter_id}: failed ({reason})", err=True)
    elif event_type == "command_rejected":
        reason = raw.get("reason", "?")
        click.echo(f"{meter_id}: rejected ({reason})", err=True)
    elif event_type == "command_timed_out":
        click.echo(f"{meter_id}: timed out", err=True)
    elif event_type == "command_applied":
        result = raw.get("result") or {}
        click.echo(f"{meter_id}: applied {json.dumps(result, sort_keys=True)}")
    else:
        # Typed query reply (meter_neighbors, meter_config, etc.).
        click.echo(f"{meter_id}: {event_type} {json.dumps(raw, sort_keys=True)}")
