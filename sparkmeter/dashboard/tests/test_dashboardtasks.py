# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.

import datetime
from unittest import mock

import pytest
from dateutil import tz
from testfixtures import LogCapture

from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.dashboard.dashboardtasks import nightly_dashboard_tariff_summary
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (EventFactory, ReadingFactory, TariffFactory,
                                                TransactionFactory)


@pytest.fixture(autouse=True)
def tzlocal(mocker):

    def tzinfo():
        # EST timezone. Etc uses the POSIX sign standard with + to the west
        # and - to the east of UTC
        return tz.gettz('Etc/GMT+5')

    mocker.patch('sparkmeter.dashboard.dashboarddomain.tzlocal', tzinfo)
    mocker.patch('sparkmeter.dashboard.dashboardtasks.tzlocal', tzinfo)
    yield tzinfo


@pytest.fixture()
def dt(mocker):
    yield mocker.patch('sparkmeter.dashboard.dashboardtasks.datetime')


@pytest.fixture()
def logger():
    with LogCapture('sparkmeter.dashboard.dashboardtasks') as logger:
        yield logger


class DashboardTaskTest(SparkMeterTestCaseBase):

    def test_summary(self, config, dt, tzlocal, logger, mocker):
        # The range for processing is 2013-01-01 05:00Z TO 2013-01-02 05:00Z
        create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        create.return_value = EventFactory()
        t1 = TransactionFactory()
        t1.from_wallet.value = 100
        t1.created = datetime.datetime(2013, 1, 1, 5, 0)
        t1.process()
        t2 = self.create_transaction(amount=30)
        t2.from_wallet.value = 30
        t2.created = datetime.datetime(2013, 1, 1, 23, 0)
        t2.process()
        self.session.commit()
        t3 = t2.reverse(t2.user)
        t3.created = datetime.datetime(2013, 1, 2, 4, 59, 59, 999)
        self.session.add(t3)
        self.session.commit()
        t3.process()
        # T4 is outside of the processing window so it should be ignored
        t4 = TransactionFactory()
        t4.from_wallet.value = 100
        t4.created = datetime.datetime(2013, 1, 2, 5)
        t4.process()

        ReadingFactory(
            meter=t1.to_wallet.meter.code,
            heartbeat_start=datetime.datetime(2013, 1, 1, 5, 0),
            heartbeat_end=datetime.datetime(2013, 1, 1, 5, 15),
            kilowatt_hours=10)
        ReadingFactory(
            meter=t1.to_wallet.meter.code,
            heartbeat_start=datetime.datetime(2013, 1, 2, 4, 30),
            heartbeat_end=datetime.datetime(2013, 1, 2, 4, 45),
            kilowatt_hours=20)
        self.session.commit()

        ground_id = self.ground.id
        config.update(HEROKU=False)
        patch = 'sparkmeter.dashboard.dashboardtasks.session_scope'
        with mock.patch(patch) as session_scope:
            session_scope.return_value = self.session

        dt.date.today.return_value = datetime.date(2013, 1, 2)
        dt.datetime = datetime.datetime  # passthrough
        nightly_dashboard_tariff_summary()

        summary = self.session.query(DashboardDailyTariffSummary).one()
        assert summary.ground.id == ground_id
        assert summary.date == datetime.date(2013, 1, 1)
        assert summary.transaction_amount == 100
        assert summary.transaction_count == 3
        assert summary.kwh_consumed == 30.0
        assert summary.customer_count == 1
        logger.check(
            ('sparkmeter.dashboard.dashboardtasks',
             'INFO',
             'Queuing dashboard summary generation for all tariffs for '
             '2013-01-01, start=2013-01-01 05:00:00, end=2013-01-02 05:00:00'),
        )

    def test_no_updates(self, config, dt, tzlocal, logger):
        TariffFactory()
        self.session.commit()

        config.update(HEROKU=False)
        patch = 'sparkmeter.dashboard.dashboardtasks.session_scope'
        with mock.patch(patch) as session_scope:
            session_scope.return_value = self.session

        dt.date.today.return_value = datetime.date(2013, 1, 2)
        dt.datetime = datetime.datetime  # passthrough
        nightly_dashboard_tariff_summary()

        assert self.session.query(DashboardDailyTariffSummary).count() == 0
        logger.check(
            ('sparkmeter.dashboard.dashboardtasks',
             'INFO',
             'Queuing dashboard summary generation for all tariffs for '
             '2013-01-01, start=2013-01-01 05:00:00, end=2013-01-02 05:00:00'),
            ('sparkmeter.dashboard.dashboardtasks',
             'INFO',
             u'Skipping tariff summary for Tariff tar\xefff01, no updates during 2013-01-01'),
        )

    def test_duplicate(self, config, dt, tzlocal):
        tariff = TariffFactory()
        s = DashboardDailyTariffSummary(
            date=datetime.date(2013, 1, 1),
            tariff=tariff,
            ground=self.ground,
            transaction_amount=0,
            transaction_count=0,
            kwh_consumed=0,
            customer_count=0)
        self.session.add(s)
        self.session.commit()

        config['HEROKU'] = False
        patch = 'sparkmeter.dashboard.dashboardtasks.session_scope'
        with mock.patch(patch) as session_scope:
            session_scope.return_value = self.session

        dt.date.today.return_value = datetime.date(2013, 1, 2)
        dt.datetime = datetime.datetime  # passthrough
        nightly_dashboard_tariff_summary()

        assert self.session.query(DashboardDailyTariffSummary).count() == 1

    def test_update_old(self, send_set_config, config, dt, tzlocal):
        t1 = self.create_transaction(amount=3)
        t1.from_wallet.value = 100
        ctime = datetime.datetime(2012, 12, 31, tzinfo=tzlocal())
        t1.created = ctime.astimezone(tz.tzutc()).replace(tzinfo=None)
        s = DashboardDailyTariffSummary(
            date=datetime.date(2012, 12, 31),
            tariff=t1.to_wallet.meter.billing.tariff,
            ground=self.ground,
            transaction_amount=0,
            transaction_count=0,
            kwh_consumed=0,
            customer_count=0)
        self.session.add(s)
        self.session.commit()

        t1.process()
        ptime = datetime.datetime(2013, 1, 2, tzinfo=tzlocal()) - datetime.timedelta(hours=1)
        t1.processed_timestamp = ptime.astimezone(tz.tzutc()).replace(tzinfo=None)
        self.session.add(t1)
        self.session.commit()
        config['HEROKU'] = False
        patch = 'sparkmeter.dashboard.dashboardtasks.session_scope'
        with mock.patch(patch) as session_scope:
            session_scope.return_value = self.session

        dt.date.today.return_value = datetime.date(2013, 1, 2)
        dt.datetime = datetime.datetime  # passthrough
        nightly_dashboard_tariff_summary()
        summaries = DashboardDailyTariffSummary.get_all()
        assert len(summaries) == 2
        assert summaries[0].date == datetime.date(2012, 12, 31)
        assert summaries[0].transaction_count == 1
        assert summaries[1].date == datetime.date(2013, 1, 1)
        assert summaries[1].transaction_count == 0

    def test_new_processed(self, mocker, dt, config, logger, send_set_config,
                           tzlocal):
        create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        create.return_value = EventFactory()
        t1 = TransactionFactory()
        t1.from_wallet.value = 100
        t1.created = datetime.datetime(2013, 1, 1, 10)
        t1.process()
        t1.processed_timestamp = t1.created + datetime.timedelta(minutes=1)
        t2 = self.create_transaction(amount=30)
        t2.from_wallet.value = 30
        t2.created = datetime.datetime(2013, 1, 1, 23)
        t2.process()
        t2.processed_timestamp = t2.created + datetime.timedelta(minutes=1)
        self.session.commit()
        t3 = t2.reverse(t2.user)
        t3.created = datetime.datetime(2013, 1, 1, 23)
        self.session.add(t3)
        self.session.commit()
        t3.process()
        t3.processed_timestamp = t3.created + datetime.timedelta(minutes=1)
        t2.reversed_timestamp = t3.processed_timestamp

        # t4 is an old transaction that has only recently been synced and processed
        t4 = self.create_transaction(amount=50)
        t4.created = datetime.datetime(2012, 12, 31, 10)
        t4.from_wallet.value = 200
        self.session.add(t4)

        # t5 is an older transaction that was processed shortly after creation
        t5 = self.create_transaction(amount=60)
        t5.created = datetime.datetime(2012, 12, 31, 10)
        t5.from_wallet.value = 200
        t5.process()
        t5.processed_timestamp = t5.created + datetime.timedelta(minutes=1)
        self.session.add(t5)

        ReadingFactory(
            meter=t1.to_wallet.meter.code,
            heartbeat_start=datetime.datetime(2013, 1, 1, 10, 15),
            heartbeat_end=datetime.datetime(2013, 1, 1, 10, 30),
            kilowatt_hours=10)
        ReadingFactory(
            meter=t1.to_wallet.meter.code,
            heartbeat_start=datetime.datetime(2013, 1, 1, 10, 30),
            heartbeat_end=datetime.datetime(2013, 1, 1, 10, 45),
            kilowatt_hours=20)
        self.session.commit()

        ground_id = self.ground.id
        config.update(HEROKU=False)
        patch = 'sparkmeter.dashboard.dashboardtasks.session_scope'
        with mock.patch(patch) as session_scope:
            session_scope.return_value = self.session

        dt.date.today.return_value = datetime.date(2013, 1, 2)
        dt.datetime = datetime.datetime  # passthrough
        nightly_dashboard_tariff_summary()

        summaries = self.session.query(DashboardDailyTariffSummary).all()
        assert len(summaries) == 1

        expected_logs = [(
            'sparkmeter.dashboard.dashboardtasks',
            'INFO',
            'Queuing dashboard summary generation for all tariffs for '
            '2013-01-01, start=2013-01-01 05:00:00, end=2013-01-02 05:00:00'
        )]
        logger.check(*expected_logs)

        t4 = self.session.merge(t4)
        t4.process()
        t4.processed_timestamp = datetime.datetime(2013, 1, 1, 5)
        self.session.add(t4)
        self.session.commit()

        nightly_dashboard_tariff_summary()

        summaries = self.session.query(DashboardDailyTariffSummary).all()
        assert len(summaries) == 2
        summary = summaries[0]
        assert summary.ground.id == ground_id
        assert summary.date == datetime.date(2013, 1, 1)
        assert summary.transaction_amount == 100
        assert summary.transaction_count == 3
        assert summary.kwh_consumed == 30.0
        assert summary.customer_count == 1

        summary = summaries[1]
        assert summary.date == datetime.date(2012, 12, 31)
        assert summary.transaction_count == 2

        expected_logs.extend([
            ('sparkmeter.dashboard.dashboardtasks',
             'INFO',
             'Queuing dashboard summary generation for all tariffs for '
             '2013-01-01, start=2013-01-01 05:00:00, end=2013-01-02 05:00:00'),
            ('sparkmeter.dashboard.dashboardtasks',
             'INFO',
             u'Skipping tariff summary for Tariff tar\xefff01, existing summary found for 2013-01-01'),
        ])
        for tariff in self.session.query(Tariff).all():
            expected_logs.append((
                'sparkmeter.dashboard.dashboardtasks',
                'INFO',
                u'Refreshing tariff summary for Tariff {} on 2012-12-31'.format(tariff.name)
            ))
        logger.check(*expected_logs)
