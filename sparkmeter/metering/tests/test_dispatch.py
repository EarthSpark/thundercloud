"""Tests for the sync→async dispatch bridge and command builders."""

import asyncio

import pytest

from sparkmeter.metering import dispatch
from sparkmeter.metering._generated.models.configure_meter_command import ConfigureMeterCommand
from sparkmeter.metering._generated.models.meter_behavior_command import MeterBehaviorCommand
from sparkmeter.metering._generated.models.register_meter_command import RegisterMeterCommand
from sparkmeter.metering._generated.models.set_balance_command import SetBalanceCommand
from sparkmeter.metering._generated.models.submit_command_v_1_commands_post_request_body_command_type_enum import (
    SubmitCommandV1CommandsPostRequestBodyCommandTypeEnum as CommandTypeEnum,
)
from sparkmeter.metering._generated.models.unregister_meter_command import UnregisterMeterCommand


class TestBuildConfigureMeter:
    def test_enable_sets_full_configuration(self):
        body = dispatch._build_configure_meter(
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
            }
        )
        assert isinstance(body, ConfigureMeterCommand)
        assert body.command_type is CommandTypeEnum.CONFIGURE_METER
        assert body.params.meter_id == "42"
        assert body.params.behavior is MeterBehaviorCommand.ENABLE
        assert body.params.configuration.power_limit_watts == pytest.approx(1500.0)
        assert body.params.configuration.current_limit_amps == pytest.approx(10.0)
        assert body.params.configuration.startup_delay_seconds == 2
        assert body.params.configuration.throttle.on_seconds == 3
        assert body.params.configuration.throttle.off_seconds == 11
        assert body.params.configuration.throttle.count_limit == 4

    def test_disable(self):
        body = dispatch._build_configure_meter({"op": "configure_meter", "node_id": 7, "command": "disable"})
        assert body.params.behavior is MeterBehaviorCommand.DISABLE

    def test_unknown_command_falls_back_to_none(self):
        body = dispatch._build_configure_meter({"op": "configure_meter", "node_id": 7, "command": "wibble"})
        assert body.params.behavior is MeterBehaviorCommand.NONE

    def test_correlation_id_default_starts_with_dispatch(self):
        body = dispatch._build_configure_meter({"op": "configure_meter", "node_id": 1, "command": "enable"})
        assert body.correlation_id.startswith("dispatch-")

    def test_correlation_id_passed_through(self):
        body = dispatch._build_configure_meter(
            {
                "op": "configure_meter",
                "node_id": 1,
                "command": "enable",
                "correlation_id": "fixed-id",
            }
        )
        assert body.correlation_id == "fixed-id"


class TestBuildSetBalance:
    def test_balance_serialized_as_string(self):
        body = dispatch._build_set_balance(
            {"op": "set_balance", "node_id": 9, "balance": "12.5", "low_balance_flag": True}
        )
        assert isinstance(body, SetBalanceCommand)
        assert body.command_type is CommandTypeEnum.SET_BALANCE
        assert body.params.meter_id == "9"
        assert body.params.balance == "12.5"
        assert body.params.low_balance is True

    def test_zero_balance(self):
        body = dispatch._build_set_balance({"op": "set_balance", "node_id": 9})
        assert body.params.balance == "0"


class TestBuildRegisterMeter:
    def test_with_mac_via_vendor_options(self):
        body = dispatch._build_register_meter(
            {
                "op": "register_meter",
                "node_id": 100,
                "node_type": "SM5R",
                "mac": 0xABCD,
            }
        )
        assert isinstance(body, RegisterMeterCommand)
        assert body.command_type is CommandTypeEnum.REGISTER_METER
        assert body.params.meter_id == "100"
        assert body.params.meter_type == "SM5R"
        assert body.vendor_options is not None
        assert body.vendor_options["mac"] == 0xABCD

    def test_without_mac_omits_vendor_options(self):
        body = dispatch._build_register_meter({"op": "register_meter", "node_id": 100, "node_type": "SM5R"})
        assert body.vendor_options is None


class TestBuildUnregisterMeter:
    def test_basic(self):
        body = dispatch._build_unregister_meter({"op": "unregister_meter", "node_id": 55})
        assert isinstance(body, UnregisterMeterCommand)
        assert body.command_type is CommandTypeEnum.UNREGISTER_METER
        assert body.params.meter_id == "55"


class TestEnqueueCommand:
    def test_enqueue_drops_silently_without_loop(self):
        # Default state: no loop registered.
        dispatch.unregister_loop()
        assert dispatch.enqueue_command({"op": "register_meter", "node_id": 1}) is False

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
