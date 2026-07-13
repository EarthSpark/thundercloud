"""Tests for the dynamic OpenAPI-driven CLI.

The CLI is built at module import time from the discriminated `Command`
union in `_generated/`. These tests verify:

- All command_type values appear as CLI subcommands.
- Top-level scalar params translate to flat options.
- Nested-dataclass params translate to dotted options.
- Submission goes through `submit_command_v1_commands_post` with the
  correct typed body.
- `--vendor-option KEY=VALUE` populates the vendor_options wrapper.

Submission and SSE-tailing are mocked so tests don't touch the network.
"""

import pytest

from sparkmeter.metering import cli as metering_cli
from sparkmeter.metering._generated.models.configure_meter_command import ConfigureMeterCommand
from sparkmeter.metering._generated.models.configure_provider_command import ConfigureProviderCommand
from sparkmeter.metering._generated.models.meter_behavior_command import MeterBehaviorCommand
from sparkmeter.metering._generated.models.ping_meter_command import PingMeterCommand
from sparkmeter.metering._generated.models.register_meter_command import RegisterMeterCommand
from sparkmeter.metering._generated.models.set_balance_command import SetBalanceCommand


@pytest.fixture
def captured(mocker):
    """Capture every (body, exit_code) submitted via the dynamic CLI."""
    captured: list = []

    async def fake_submit_and_tail(body, correlation_id, timeout=10.0):
        captured.append(body)
        return 0

    mocker.patch.object(metering_cli, "_submit_and_tail", fake_submit_and_tail)
    return captured


def _expected_command_names() -> set[str]:
    from sparkmeter.metering._generated.models.submit_command_v_1_commands_post_request_body import (
        SubmitCommandV1CommandsPostRequestBodyDiscriminator,
    )

    discriminator = SubmitCommandV1CommandsPostRequestBodyDiscriminator()
    return {ct.replace("_", "-") for ct in discriminator.get_mapping()}


class TestRegistration:
    def test_every_spec_command_appears_as_subcommand(self):
        registered = set(metering_cli.metering.commands.keys())
        assert _expected_command_names().issubset(registered)


class TestRegisterMeter:
    def test_required_params_only(self, cli, captured):
        result = cli(
            "metering",
            "register-meter",
            "--meter-id",
            "42",
            "--meter-type",
            "SM5R",
        )
        assert result.exit_code == 0
        assert len(captured) == 1
        body = captured[0]
        assert isinstance(body, RegisterMeterCommand)
        assert body.params.meter_id == "42"
        assert body.params.meter_type == "SM5R"

    def test_with_vendor_option(self, cli, captured):
        result = cli(
            "metering",
            "register-meter",
            "--meter-id",
            "42",
            "--meter-type",
            "SM5R",
            "--vendor-option",
            "mac=43981",
        )
        assert result.exit_code == 0
        body = captured[0]
        assert body.vendor_options is not None
        assert body.vendor_options["mac"] == 43981

    def test_correlation_id_passed_through(self, cli, captured):
        result = cli(
            "metering",
            "register-meter",
            "--meter-id",
            "42",
            "--meter-type",
            "SM5R",
            "--correlation-id",
            "fixed-id",
        )
        assert result.exit_code == 0
        assert captured[0].correlation_id == "fixed-id"


class TestSetBalance:
    def test_balance_passes_through_as_string(self, cli, captured):
        result = cli(
            "metering",
            "set-balance",
            "--meter-id",
            "9",
            "--balance",
            "12.5",
        )
        assert result.exit_code == 0
        body = captured[0]
        assert isinstance(body, SetBalanceCommand)
        assert body.params.meter_id == "9"
        assert body.params.balance == "12.5"


class TestPingMeter:
    def test_basic(self, cli, captured):
        result = cli("metering", "ping-meter", "--meter-id", "42")
        assert result.exit_code == 0
        body = captured[0]
        assert isinstance(body, PingMeterCommand)
        assert body.params.meter_id == "42"


class TestConfigureMeter:
    def test_with_nested_throttle_options(self, cli, captured):
        result = cli(
            "metering",
            "configure-meter",
            "--meter-id",
            "42",
            "--behavior",
            "enable",
            "--configuration.power-limit-watts",
            "1500",
            "--configuration.current-limit-amps",
            "10",
            "--configuration.startup-delay-seconds",
            "2",
            "--configuration.throttle.on-seconds",
            "5",
            "--configuration.throttle.off-seconds",
            "10",
            "--configuration.throttle.count-limit",
            "5",
        )
        assert result.exit_code == 0
        body = captured[0]
        assert isinstance(body, ConfigureMeterCommand)
        assert body.params.meter_id == "42"
        assert body.params.behavior is MeterBehaviorCommand.ENABLE
        assert body.params.configuration.power_limit_watts == pytest.approx(1500.0)
        assert body.params.configuration.current_limit_amps == pytest.approx(10.0)
        assert body.params.configuration.startup_delay_seconds == 2
        assert body.params.configuration.throttle.on_seconds == 5
        assert body.params.configuration.throttle.off_seconds == 10
        assert body.params.configuration.throttle.count_limit == 5


class TestConfigureProvider:
    def test_minimal(self, cli, captured):
        result = cli(
            "metering",
            "configure-provider",
            "--heartbeat-seconds",
            "900",
        )
        assert result.exit_code == 0
        body = captured[0]
        assert isinstance(body, ConfigureProviderCommand)
        assert body.params.heartbeat_seconds == 900

    def test_with_vendor_options(self, cli, captured):
        result = cli(
            "metering",
            "configure-provider",
            "--heartbeat-seconds",
            "900",
            "--vendor-option",
            "channel=25",
            "--vendor-option",
            "aes_key=00112233445566778899aabbccddeeff",
        )
        assert result.exit_code == 0
        body = captured[0]
        assert body.vendor_options["channel"] == 25
        assert body.vendor_options["aes_key"] == "00112233445566778899aabbccddeeff"


class TestVendorOptionParsing:
    @pytest.mark.parametrize(
        "raw,key,expected",
        [
            ("channel=25", "channel", 25),
            ("flag=true", "flag", True),
            ("name=hello", "name", "hello"),
            ("negative=-5", "negative", -5),
        ],
    )
    def test_parses_typed_values(self, raw, key, expected):
        out = metering_cli._parse_vendor_options((raw,))
        assert out[key] == expected

    def test_invalid_format_raises(self):
        from click import BadParameter

        with pytest.raises(BadParameter):
            metering_cli._parse_vendor_options(("no-equals-sign",))
