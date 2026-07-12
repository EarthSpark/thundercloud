# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import datetime

import pytest
from dateutil.tz import tzutc
from freezegun import freeze_time

from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.meter.meterdomain import MeterConfig
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (
    EventFactory,
    MeterFactory,
    ReadingFactory,
    TariffFactory,
    TransactionFactory,
)


class DashboardDailyTariffSummaryTest(SparkMeterTestCaseBase):
    def test_create_empty_summary(self):
        tariff = TariffFactory()
        MeterFactory(tariff=tariff, ground=self.ground)
        summary = DashboardDailyTariffSummary.create_summary(
            ground=self.ground, tariff=tariff, date=datetime.date(2013, 1, 1)
        )
        assert not summary

    def test_create_summary(self, mocker):
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

        tariff = Tariff.query.one()
        summary = DashboardDailyTariffSummary.create_summary(
            ground=self.ground, tariff=tariff, date=datetime.date(2013, 1, 1)
        )
        self.session.add(summary)
        self.session.commit()

        assert summary.date == datetime.date(2013, 1, 1)
        assert summary.tariff == tariff
        assert summary.transaction_amount == 100.0  # 100 + 30 - 30
        assert summary.transaction_count == 3
        assert summary.kwh_consumed == 30.0  # 10 + 20
        assert summary.customer_count == 1
        assert summary.ground.id == self.ground.id

    def test_summary_errors(self):
        msg = "ground must be a Ground, not NoneType"
        with pytest.raises(TypeError, match=msg):
            DashboardDailyTariffSummary.create_summary(None, None, None)

        msg = "tariff must be a Tariff, not NoneType"
        with pytest.raises(TypeError, match=msg):
            DashboardDailyTariffSummary.create_summary(self.ground, None, None)

        t = TariffFactory()
        msg = "date must be a datetime.date, not NoneType"
        with pytest.raises(TypeError, match=msg):
            DashboardDailyTariffSummary.create_summary(self.ground, t, None)

    @freeze_time("2013-01-03")
    def test_get_items_since_view(self):
        # All pre-paid
        meter = MeterFactory(config__state=MeterConfig.STATE_AUTO, ground=self.ground)
        summary = DashboardDailyTariffSummary(
            date=datetime.date(2013, 1, 2),
            ground=self.ground,
            tariff=meter.tariff,
            transaction_amount=0,
            transaction_count=0,
            kwh_consumed=0,
            customer_count=0,
        )
        self.session.add(summary)

        # Future
        summary2 = DashboardDailyTariffSummary(
            date=datetime.date(2014, 1, 1),
            ground=self.ground,
            tariff=meter.tariff,
            transaction_amount=0,
            transaction_count=0,
            kwh_consumed=0,
            customer_count=0,
        )
        self.session.add(summary2)

        # Not Prepaid
        tariff = TariffFactory()
        meter = MeterFactory(ground=self.ground, tariff=tariff, config__state=MeterConfig.STATE_ON)
        summary3 = DashboardDailyTariffSummary(
            date=datetime.date(2013, 1, 2),
            ground=self.ground,
            tariff=tariff,
            transaction_amount=0,
            transaction_count=0,
            kwh_consumed=0,
            customer_count=0,
        )
        self.session.add(summary3)
        self.session.commit()

        date = datetime.date(2013, 1, 1)
        # FIXME: this test fails at the moment because we aren't doing prepaid only at runtime. Will uncomment
        # when this is properly implemented.
        # summary4 = DashboardDailyTariffSummary.get_items_since_view(date, prepaid_only=True).one()
        # assert summary == summary4

        query = DashboardDailyTariffSummary.get_items_since_view(date, ground=self.ground, prepaid_only=False)
        results = self.session.execute(query)
        assert list(results) == [
            ("tar\xefff01", datetime.date(2013, 1, 2), 0, 0, 0.0, 0),
            ("tar\xefff02", datetime.date(2013, 1, 2), 0, 0, 0.0, 0),
        ]

    @freeze_time("2016-03-02")
    def test_get_monthly_summary_view(self):
        tariff1 = TariffFactory(name="tariff 1")
        MeterFactory(tariff=tariff1, ground=self.ground)
        tariff2 = TariffFactory(name="tariff 2")
        MeterFactory(tariff=tariff2, ground=self.ground)
        summary_data = [
            # Tariff 1 January (filtered out)
            (tariff1, datetime.date(2016, 1, 1), 1, 2),
            (tariff1, datetime.date(2016, 1, 31), 11, 12),
            # Tariff 1 February
            (tariff1, datetime.date(2016, 2, 1), 3, 4),
            (tariff1, datetime.date(2016, 2, 29), 5, 6),
            # Tariff 1 March
            (tariff1, datetime.date(2016, 3, 1), 7, 8),
            # Tariff 2 February
            (tariff2, datetime.date(2016, 2, 15), 1, 2),
            (tariff2, datetime.date(2016, 2, 29), 5, 6),
        ]
        for s in summary_data:
            summary = DashboardDailyTariffSummary(
                ground=self.ground,
                tariff=s[0],
                date=s[1],
                transaction_amount=s[2],
                kwh_consumed=s[3],
                customer_count=0,
                transaction_count=0,
            )
            self.session.add(summary)
        self.session.commit()
        query = DashboardDailyTariffSummary.get_last_two_months_summary_view(self.ground)
        expected = [
            # Tariff 1 February
            (
                "tariff 1",
                datetime.date(2016, 2, 1),
                8,  # 3 + 5
                10.0,  # 4 + 6
                0.344827586206897,
            ),  # (4 + 6) / 29
            # Tariff 1 March
            (
                "tariff 1",
                datetime.date(2016, 3, 1),
                7,  # 7
                8.0,  # 8
                8.0,
            ),  # 8 / 1
            # Tariff 2 February
            (
                "tariff 2",
                datetime.date(2016, 2, 1),
                6,  # 1 + 5
                8.0,  # 2 + 6
                0.275862068965517,
            ),  # (2 + 6) / 29
        ]
        results = list(self.session.execute(query))
        assert len(results) == len(expected)
        for result, exp in zip(results, expected):
            for r, e in zip(result, exp):
                if isinstance(e, float):
                    assert r == pytest.approx(e)
                else:
                    assert r == e

    @freeze_time("2016-03-06")
    def test_get_monthly_daily_average_summary_view(self):
        ground = self.ground

        tariff1 = TariffFactory(name="tariff 1")
        MeterFactory(tariff=tariff1, ground=ground)

        summary_data = [
            # Tariff 1 February
            (tariff1, datetime.date(2016, 2, 1), 3, 15),
            (tariff1, datetime.date(2016, 2, 10), 5, 14),
            # Tariff 1 March
            (tariff1, datetime.date(2016, 3, 1), 7, 8),
            (tariff1, datetime.date(2016, 3, 2), 7, 8),
            (tariff1, datetime.date(2016, 3, 3), 7, 8),
            (tariff1, datetime.date(2016, 3, 4), 7, 8),
            (tariff1, datetime.date(2016, 3, 5), 7, 8),
        ]
        for s in summary_data:
            summary = DashboardDailyTariffSummary(
                ground=ground,
                tariff=s[0],
                date=s[1],
                transaction_amount=s[2],
                kwh_consumed=s[3],
                customer_count=0,
                transaction_count=0,
            )
            self.session.add(summary)
        self.session.commit()
        query = DashboardDailyTariffSummary.get_last_two_months_summary_view(ground)
        expected = [
            # Tariff 1 February
            (
                "tariff 1",
                datetime.date(2016, 2, 1),
                8,  # 3 + 5
                29.0,  # 4 + 6
                1.0,
            ),  # (15 + 14) / 29
            # Tariff 1 March
            (
                "tariff 1",
                datetime.date(2016, 3, 1),
                35,  # 7 * 5
                40.0,  # 8 * 5
                8.0,
            ),  # (8 * 5) / 5
        ]
        results = list(self.session.execute(query))
        assert len(results) == len(expected)
        for result, exp in zip(results, expected):
            for r, e in zip(result, exp):
                if isinstance(e, float):
                    assert r == pytest.approx(e)
                else:
                    assert r == e
