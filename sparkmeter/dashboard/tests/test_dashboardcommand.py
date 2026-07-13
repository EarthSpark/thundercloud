# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.

import datetime

import pytest
from dateutil.tz import tzutc
from testfixtures import LogCapture

from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import EventFactory, ReadingFactory, TariffFactory, TransactionFactory


@pytest.fixture()
def logger():
    with LogCapture("sparkmeter.dashboard.dashboardcommand") as logger:
        yield logger


class TariffSummaryTest(SparkMeterTestCaseBase):
    def test_summary_empty(self, cli, logger):
        TariffFactory()
        self.session.commit()
        cli("dashboard", "tariff-summary", "2013-01-01")
        assert DashboardDailyTariffSummary.get_all() == []
        logger.check(
            ("sparkmeter.dashboard.dashboardcommand", "INFO", "Day 2013-01-01"),
            (
                "sparkmeter.dashboard.dashboardcommand",
                "INFO",
                "tariff           #T       $T      kwh # customers query time",
            ),
        )

    def test_summary(self, cli, mocker, logger):
        mocker.patch("sparkmeter.dashboard.dashboarddomain.tzlocal", tzutc)
        create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        create.return_value = EventFactory()

        t1 = TransactionFactory()
        t1.from_wallet.value = 100
        t1.process()

        t2 = self.create_transaction(amount=30)
        t2.from_wallet.value = 30
        t2.process()
        self.session.commit()
        t3 = t2.reverse(t2.user)
        t3.created = datetime.datetime(2013, 1, 1)
        self.session.add(t3)
        self.session.commit()
        t3.process()

        ReadingFactory(meter=t1.to_wallet.meter.code, kilowatt_hours=10)
        ReadingFactory(meter=t1.to_wallet.meter.code, kilowatt_hours=20)
        self.session.commit()

        cli("dashboard", "tariff-summary", "2013-01-01")

        summary = DashboardDailyTariffSummary.query.one()
        assert summary.ground.id == self.ground.id
        assert summary.date == datetime.date(2013, 1, 1)
        assert summary.transaction_amount == 100
        assert summary.transaction_count == 3
        assert summary.kwh_consumed == 30.0
        assert summary.customer_count == 1

        logger.check(
            ("sparkmeter.dashboard.dashboardcommand", "INFO", "Day 2013-01-01"),
            (
                "sparkmeter.dashboard.dashboardcommand",
                "INFO",
                "tariff           #T       $T      kwh # customers query time",
            ),
            (
                "sparkmeter.dashboard.dashboardcommand",
                "INFO",
                "tar\xefff01          3      100    30.00      1",
            ),
        )
