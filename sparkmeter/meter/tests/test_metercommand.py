# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import datetime
from unittest import mock

import pytest
from testfixtures import LogCapture

from sparkmeter.meter.meterdomain import Meter
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (
    EventFactory,
    GroundFactory,
    MeterFactory,
    TariffFactory,
    TransactionFactory,
)


@pytest.fixture()
def getUtility(mocker):
    yield mocker.patch("sparkmeter.meter.metercommand.getUtility")


@pytest.fixture()
def logger():
    with LogCapture(
        ("sparkmeter.controller", "sparkmeter.meter.metercommand", "sparkmeter.meter.meterdomain")
    ) as logger:
        yield logger


class MeterCommandTest(SparkMeterTestCaseBase):
    def test_convert_customer_meter(self, cli, logger):
        m = MeterFactory()
        transaction = TransactionFactory(_to_wallet_meter=m)
        transaction.from_wallet.value = 100
        transaction.process()
        self.session.commit()

        result = cli("meter", "convert-to-totalizer", "-s", m.serial)
        assert result.exit_code == 0

        logger.check(
            ("sparkmeter.meter.meterdomain", "INFO", "Removing transactions for meter SM15R-01-00000001"),
            (
                "sparkmeter.meter.meterdomain",
                "INFO",
                "Removing Customer and Billing for meter SM15R-01-00000001",
            ),
            ("sparkmeter.meter.meterdomain", "INFO", "Removing wallets for meter SM15R-01-00000001"),
        )
        m = Meter.get_by_id(m.id)
        assert m.meter_type == Meter.TYPE_TOTALIZER
        assert not m.billing
        assert not m.credit_wallet
        assert not m.debt_wallet
        assert not m.plan_wallet
        assert not m.customer

    def test_convert_customer_meter_does_not_exist(self, cli, logger):
        result = cli("meter", "convert-to-totalizer", "-s", "invalid-serial")
        assert result.exit_code == 1
        logger.check(("sparkmeter.meter.metercommand", "ERROR", "meter does not exist"))

    def test_convert_customer_meter_must_be_a_customer(self, cli, logger):
        m = MeterFactory(
            billing=None,
            customer=None,
            meter_type=Meter.TYPE_TOTALIZER,
            credit_wallet=None,
            debt_wallet=None,
            plan_wallet=None,
        )
        self.session.commit()
        result = cli("meter", "convert-to-totalizer", "-s", m.serial)
        assert result.exit_code == 1
        logger.check(("sparkmeter.meter.metercommand", "ERROR", "meter must be a customer meter"))

    def test_convert_totalizer(self, cli, logger):
        m = MeterFactory(
            billing=None,
            customer=None,
            meter_type=Meter.TYPE_TOTALIZER,
            credit_wallet=None,
            debt_wallet=None,
            plan_wallet=None,
        )
        t = TariffFactory()
        self.session.commit()

        result = cli("meter", "convert-to-customer", "-s", m.serial, "-t", t.name)
        assert result.exit_code == 0

        logger.check(
            (
                "sparkmeter.meter.meterdomain",
                "INFO",
                "Creating wallets for meter 00000001-0000-0000-0000-000000000001",
            )
        )
        assert m.meter_type == Meter.TYPE_CUSTOMER
        assert m.billing.tariff.id == t.id
        assert m.credit_wallet
        assert m.debt_wallet
        assert m.plan_wallet
        assert m.customer

    def test_convert_totalizer_meter_does_not_exist(self, cli, logger):
        result = cli("meter", "convert-to-customer", "-s", "invalid-serial", "-t", "unused")
        assert result.exit_code == 1
        logger.check(("sparkmeter.meter.metercommand", "ERROR", "meter does not exist"))

    def test_convert_totalizer_meter_must_be_a_totalizer(self, cli, logger):
        m = MeterFactory()
        self.session.commit()
        result = cli("meter", "convert-to-customer", "-s", m.serial, "-t", "unused")
        assert result.exit_code == 1
        logger.check(("sparkmeter.meter.metercommand", "ERROR", "meter must be a totalizer meter"))

    def test_convert_totalizer_meter_tariff_does_not_exist(self, cli, logger):
        m = MeterFactory(
            billing=None,
            customer=None,
            meter_type=Meter.TYPE_TOTALIZER,
            credit_wallet=None,
            debt_wallet=None,
            plan_wallet=None,
        )
        self.session.commit()
        result = cli("meter", "convert-to-customer", "-s", m.serial, "-t", "invalid-tariff")
        assert result.exit_code == 1
        logger.check(("sparkmeter.meter.metercommand", "ERROR", "tariff does not exist"))

    def test_create(self, cli, config, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        ground = GroundFactory()
        tariff = TariffFactory()
        self.session.commit()
        config.update(
            SERIAL=ground.serial,
            NEW_METER_ACCT_CREDIT=500,
            NEW_METER_STATE=1,
            NEW_METER_HIDDEN=False,
            NEW_METER_SUBNET=127,
            NEW_METER_TARIFF=tariff.name,
        )
        result = cli("meter", "create", "-s", "SM15R-01-00000000")
        assert result.exit_code == 0

        meter = Meter.query.one()
        assert meter.serial == "SM15R-01-00000000"
        assert meter.ground.id == ground.id
        assert meter.config.state == 1
        assert not meter.config.hidden
        assert meter.config.subnet == 127
        assert meter.tariff.id == tariff.id
        assert event_create.mock_calls == [
            mock.call("meter-created", obj=mock.ANY),
        ]

    def test_create_error_duplicate(self, cli, config, logger, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        ground = GroundFactory()
        tariff = TariffFactory()
        self.session.commit()
        config.update(SERIAL=ground.serial, NEW_METER_TARIFF=tariff.name)
        result = cli("meter", "create", "-s", "SM15R-01-00000000")
        assert result.exit_code == 0
        result = cli("meter", "create", "-s", "SM15R-01-00000000")
        assert result.exit_code == 1

        logger.check(
            (
                "sparkmeter.meter.metercommand",
                "ERROR",
                "ERROR: meter with serial SM15R-01-00000000 already exists",
            )
        )
        # FIXME: This should not have created the event!
        assert event_create.mock_calls == [
            mock.call("meter-created", obj=mock.ANY),
        ]

    def test_create_error_unknown_model(self, cli, config, logger, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        ground = GroundFactory()
        tariff = TariffFactory()
        self.session.commit()
        config.update(SERIAL=ground.serial, NEW_METER_TARIFF=tariff.name)
        result = cli("meter", "create", "-s", "SM2R-01-00000000")
        assert result.exit_code == 1

        logger.check(("sparkmeter.meter.metercommand", "ERROR", "ERROR: No model found for SM2R-01-00000000"))
        assert len(event_create.mock_calls) == 0

    def test_remove(self, cli, logger):
        m1 = MeterFactory()
        m1.credit_wallet.value = 10
        m1.debt_wallet.value = 20
        m1.plan_wallet.value = 30
        TransactionFactory(_to_wallet_meter=m1)
        self.session.commit()

        with mock.patch("sparkmeter.meter.metercommand.input") as f:
            f.return_value = "N"
            cli("meter", "remove", "-s", m1.serial)

        logger.check(
            ("sparkmeter.meter.metercommand", "INFO", "Meter: SM15R-01-00000001"),
            ("sparkmeter.meter.metercommand", "INFO", "Customer: str\xebet"),
            ("sparkmeter.meter.metercommand", "WARNING", "Credit balance: 10.000000"),
            ("sparkmeter.meter.metercommand", "WARNING", "Debt balance: 20.000000"),
            ("sparkmeter.meter.metercommand", "WARNING", "Plan balance: 30.000000"),
            (
                "sparkmeter.meter.metercommand",
                "WARNING",
                "Transaction 00000007-0000-0000-0000-000000000001 2013-01-01 01:01:01 100.0 credit",
            ),
            ("sparkmeter.meter.metercommand", "INFO", "Okay, aborting"),
        )
        logger.clear()

        with mock.patch("sparkmeter.meter.metercommand.input") as f:
            f.return_value = "Y"
            cli("meter", "remove", "-s", m1.serial)

        logger.check(
            ("sparkmeter.meter.metercommand", "INFO", "Meter: SM15R-01-00000001"),
            ("sparkmeter.meter.metercommand", "INFO", "Customer: str\xebet"),
            ("sparkmeter.meter.metercommand", "WARNING", "Credit balance: 10.000000"),
            ("sparkmeter.meter.metercommand", "WARNING", "Debt balance: 20.000000"),
            ("sparkmeter.meter.metercommand", "WARNING", "Plan balance: 30.000000"),
            (
                "sparkmeter.meter.metercommand",
                "WARNING",
                "Transaction 00000007-0000-0000-0000-000000000001 2013-01-01 01:01:01 100.0 credit",
            ),
            ("sparkmeter.meter.meterdomain", "INFO", "Removing transactions for meter SM15R-01-00000001"),
            (
                "sparkmeter.meter.meterdomain",
                "INFO",
                "Removing meter SM15R-01-00000001 and associated tables",
            ),
            ("sparkmeter.meter.meterdomain", "INFO", "Removing transactions for meter SM15R-01-00000001"),
            (
                "sparkmeter.meter.meterdomain",
                "INFO",
                "Removing Customer and Billing for meter SM15R-01-00000001",
            ),
            ("sparkmeter.meter.meterdomain", "INFO", "Removing wallets for meter SM15R-01-00000001"),
        )

    def test_remove_does_not_exist(self, cli, logger):
        result = cli("meter", "remove", "-s", "foobar")
        assert result.exit_code == 1
        logger.check(("sparkmeter.meter.metercommand", "ERROR", "No such meter with serial: foobar"))

    def test_send_config(self, cli, logger):
        m1 = MeterFactory()
        self.session.commit()

        result = cli("meter", "send-config")
        assert result.exit_code == 1
        logger.check(
            ("sparkmeter.meter.metercommand", "INFO", "must supply either --all or a --mac parameter")
        )

        with mock.patch("sparkmeter.meter.meterdomain.Meter.send_set_config_unconditionally") as f:
            result = cli("meter", "send-config", "-a")
            assert result.exit_code == 0
            assert f.mock_calls == [mock.call()]

            f.reset_mock()

            result = cli("meter", "send-config", "-m", str(m1.code))
            assert result.exit_code == 0
            assert f.mock_calls == [mock.call()]

    def test_get_heartbeat_reading_no_data(self, cli):
        """`meter get-heartbeat -m <mac>` exits 1 when no readings exist."""
        m = MeterFactory()
        self.session.commit()
        result = cli("meter", "get-heartbeat", "-m", str(m.code))
        assert result.exit_code == 1

    def test_get_heartbeat_reading_prints_latest(self, cli):
        """`meter get-heartbeat -m <mac>` prints the latest stored reading."""
        from sparkmeter.meter.meterstate import MeterState
        from sparkmeter.reading.readingdomain import Reading

        m = MeterFactory()
        self.session.add(
            Reading(
                meter=m.code,
                state=MeterState.STATE_ON.id,
                uptime=10,
                heartbeat_start=datetime.datetime(2026, 1, 1, 0, 0),
                heartbeat_end=datetime.datetime(2026, 1, 1, 0, 15),
            )
        )
        self.session.commit()
        result = cli("meter", "get-heartbeat", "-m", str(m.code))
        assert "'meter': '%d'" % m.code in result.output

    def test_ping(self, cli, mocker, capfd):
        """`meter ping -m <mac>` submits a `ping_meter` to the metering provider."""
        submitted = []

        async def fake_submit_ping(client, meter_id, correlation_id):
            submitted.append((meter_id, correlation_id))

        async def fake_run_per_meter_command(submitter, meter_ids):
            for mid in meter_ids:
                await submitter(mocker.MagicMock(), mid, "corr-" + mid)

        mocker.patch("sparkmeter.metering.tools.cli_client.submit_ping", fake_submit_ping)
        mocker.patch(
            "sparkmeter.metering.tools.cli_client.run_per_meter_command",
            fake_run_per_meter_command,
        )

        m = MeterFactory()
        self.session.commit()
        result = cli("meter", "ping", "-m", str(m.code))
        assert result.exit_code == 0
        assert submitted == [(str(m.code), f"corr-{m.code}")]

    def test_ping_all(self, cli, mocker):
        """`meter ping` (no mac) submits a `ping_meter` for every meter."""
        submitted = []

        async def fake_submit_ping(client, meter_id, correlation_id):
            submitted.append(meter_id)

        async def fake_run_per_meter_command(submitter, meter_ids):
            for mid in meter_ids:
                await submitter(mocker.MagicMock(), mid, "corr-" + mid)

        mocker.patch("sparkmeter.metering.tools.cli_client.submit_ping", fake_submit_ping)
        mocker.patch(
            "sparkmeter.metering.tools.cli_client.run_per_meter_command",
            fake_run_per_meter_command,
        )

        MeterFactory()
        MeterFactory()
        self.session.commit()
        result = cli("meter", "ping")
        assert result.exit_code == 0
        assert len(submitted) == 2


class NeighborListCommandTest(SparkMeterTestCaseBase):
    def test_get_neighborlists(self, cli, mocker, capfd):
        """`meter get-neighborlists` submits `query_meter_neighbors` for every meter."""
        submitted = []

        async def fake_submit_neighbors(client, meter_id, correlation_id):
            submitted.append(meter_id)

        async def fake_run_per_meter_command(submitter, meter_ids):
            for mid in meter_ids:
                await submitter(mocker.MagicMock(), mid, "corr-" + mid)

        mocker.patch(
            "sparkmeter.metering.tools.cli_client.submit_query_neighbors",
            fake_submit_neighbors,
        )
        mocker.patch(
            "sparkmeter.metering.tools.cli_client.run_per_meter_command",
            fake_run_per_meter_command,
        )

        MeterFactory(code=1)
        MeterFactory(code=2)
        self.session.commit()
        result = cli("meter", "get-neighborlists")
        assert result.exit_code == 0
        assert sorted(submitted) == ["1", "2"]


class WithForeverTest:
    def test_runs_once_without_forever(self):
        from sparkmeter.meter.metercommand import with_forever

        call_count = [0]

        @with_forever
        def counting_fn():
            call_count[0] += 1

        counting_fn(forever=False)
        assert call_count[0] == 1

    def test_loops_with_forever(self):
        from sparkmeter.meter.metercommand import with_forever

        call_count = [0]

        @with_forever
        def counting_fn():
            call_count[0] += 1
            if call_count[0] >= 3:
                raise StopIteration()

        with pytest.raises(StopIteration):
            counting_fn(forever=True, delay=0)
        assert call_count[0] == 3


class ReadingGeneratorTest(SparkMeterTestCaseBase):
    def test_heartbeat(self, mocker):
        from sparkmeter.reading.readingcommand import ReadingGenerator

        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()

        m = MeterFactory()
        self.session.commit()

        rg = ReadingGenerator(energy_watts=60, cycle_length=15)
        rg.create_for_meter(m.serial)
