# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import datetime
import http.client
import urllib.parse

import pytest
from freezegun import freeze_time

from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import (GroundFactory, MeterFactory, OperatorFactory,
                                                TariffFactory)


class DashboardViewTest(WebViewTestCaseBase):

    def _generateSummaryData(self, ground, tariff1, tariff2):
        summary_data = [
            # Tariff 1 January
            (tariff1, datetime.date(2016, 1, 1), 1, 2),  # too old, filtered out
            (tariff1, datetime.date(2016, 1, 31), 11, 12),
            # Tariff 1 February
            (tariff1, datetime.date(2016, 2, 1), 3, 4),
            (tariff1, datetime.date(2016, 2, 29), 5, 6),
            # Tariff 1 March
            (tariff1, datetime.date(2016, 3, 1), 7, 8),
            (tariff1, datetime.date(2016, 3, 2), 7, 8),  # tomorrow, filtered out

            # Tariff 2 February
            (tariff2, datetime.date(2016, 2, 15), 1, 2),
            (tariff2, datetime.date(2016, 2, 29), 5, 6),
        ]
        for s in summary_data:
            summary = DashboardDailyTariffSummary(
                ground=ground,
                tariff=s[0],
                date=s[1],
                transaction_amount=s[2],
                kwh_consumed=s[3],
                customer_count=s[1].day,
                transaction_count=s[1].day)
            self.session.add(summary)

    def _createExampleDashboardData(self):
        tariff1 = TariffFactory(name='tariff 1')
        meter1 = MeterFactory(tariff=tariff1)
        tariff2 = TariffFactory(name='tariff 2')
        MeterFactory(tariff=tariff2, ground=meter1.ground)
        ground = meter1.ground
        self._generateSummaryData(ground, tariff1, tariff2)
        self.session.commit()

    def _createExamplesDashboardDataMultigrid(self, operator_role):
        other = GroundFactory()
        self.session.commit()
        tariff1 = TariffFactory(name='tariff 1')
        tariff2 = TariffFactory(name='tariff 2')
        MeterFactory(tariff=tariff1, ground=self.ground)
        MeterFactory(tariff=tariff2, ground=other)
        self._generateSummaryData(self.ground, tariff1, tariff2)
        self._generateSummaryData(other, tariff1, tariff2)
        users = [
            OperatorFactory(roles=[operator_role],
                            username='none',
                            grounds=[]),
            OperatorFactory(roles=[operator_role],
                            username='only-1',
                            grounds=[self.ground]),
            OperatorFactory(roles=[operator_role],
                            username='only-2',
                            grounds=[other]),
            OperatorFactory(roles=[operator_role],
                            username='all',
                            grounds=[self.ground, other]),
        ]
        self.session.commit()
        return other, users

    def test_index(self, client):
        path = "/dashboard/"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2016-03-02")
    def test_last_two_months_energy_purchase(self, client):
        self._createExampleDashboardData()
        path = "/dashboard/tariff-daily-summary/energy-purchase.json"
        response = client.get(path)
        d = [{u'val': 8.0, u'col': u'tariff 1', u'idx': u'Feb, 2016'},  # 3 + 5 = 8
             {u'val': 6.0, u'col': u'tariff 2', u'idx': u'Feb, 2016'},  # 1 + 5 = 6
             {u'val': 7.0, u'col': u'tariff 1', u'idx': u'Mar, 2016'},  # 7 = 7
             {u'val': 0.0, u'col': u'tariff 2', u'idx': u'Mar, 2016'}]
        assert d == response.json()['data'][0]['values']
        self.verify_response(response)

    @freeze_time("2016-03-02")
    def test_last_two_months_monthly_consumption(self, client):
        self._createExampleDashboardData()
        path = "/dashboard/tariff-daily-summary/monthly-consumption.json"
        response = client.get(path)
        d = [{u'val': 10.0, u'col': u'tariff 1', u'idx': u'Feb, 2016'},  # 4 + 6 = 10
             {u'val': 8.0, u'col': u'tariff 2', u'idx': u'Feb, 2016'},  # 2 + 6 = 8
             {u'val': 8.0, u'col': u'tariff 1', u'idx': u'Mar, 2016'},  # 8 = 8
             {u'val': 0.0, u'col': u'tariff 2', u'idx': u'Mar, 2016'}]
        assert d == response.json()['data'][0]['values']
        self.verify_response(response)

    @freeze_time("2016-03-02")
    def test_last_two_months_daily_avg_consumption(self, client):
        self._createExampleDashboardData()
        path = "/dashboard/tariff-daily-summary/daily-avg-consumption.json"
        response = client.get(path)
        d = [{u'val': pytest.approx(0.344827586206897),  # (4 + 6) / 29
              u'col': u'tariff 1', u'idx': u'Feb, 2016'},
             # (2 + 6) / 31 = 0.27..
             {u'val': pytest.approx(0.275862068965517), u'col': u'tariff 2', u'idx': u'Feb, 2016'},
             {u'val': 8.0, u'col': u'tariff 1', u'idx': u'Mar, 2016'},  # 8 / 1 = 8
             {u'val': 0.0, u'col': u'tariff 2', u'idx': u'Mar, 2016'}]
        assert d == response.json()['data'][0]['values']
        self.verify_response(response)

    @freeze_time("2016-03-02")
    def test_last_two_months_daily_avg_consumption_csv(self, client):
        self._createExampleDashboardData()
        path = "/dashboard/tariff-daily-summary/daily-avg-consumption.csv"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2016-03-02")
    def test_last_30_days_customer_count(self, client):
        self._createExampleDashboardData()
        path = "/dashboard/tariff-daily-summary/last-30-days-customer-count.json"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2016-03-02")
    def test_last_30_days_consumption(self, client):
        self._createExampleDashboardData()
        path = "/dashboard/tariff-daily-summary/last-30-days-consumption.json"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2016-03-02")
    def test_last_30_days_sales_amount(self, client):
        self._createExampleDashboardData()
        path = "/dashboard/tariff-daily-summary/last-30-days-sales-amount.json"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2016-03-02")
    def test_last_30_days_sales_count(self, client):
        self._createExampleDashboardData()
        path = "/dashboard/tariff-daily-summary/last-30-days-sales-count.json"
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2016-03-02")
    def test_last_30_days_sales_count_csv(self, client):
        self._createExampleDashboardData()
        path = "/dashboard/tariff-daily-summary/last-30-days-sales-count.csv"
        response = client.get(path)
        self.verify_response(response)

    def test_tariff_summary_bad_graph_name(self, client):
        path = "/dashboard/tariff-daily-summary/does-not-exist.json"
        response = client.get(path)
        assert response.status_code == http.client.BAD_REQUEST

    def test_tariff_summary_bad_chart_format(self, client):
        path = "/dashboard/tariff-daily-summary/last-30-days-sales-count.doc"
        response = client.get(path)
        assert response.status_code == http.client.BAD_REQUEST

    @freeze_time("2016-03-02")
    def test_tariff_daily_summary(self, client, config, operator_role):
        other, users = self._createExamplesDashboardDataMultigrid(operator_role)

        for params in [dict(HEROKU=True),
                       dict(HEROKU=False, SERIAL=self.ground.serial),
                       dict(HEROKU=False, SERIAL=other.serial)]:
            if params.get('SERIAL') == self.ground.serial:
                where = 'ground1'
            elif params.get('SERIAL') == other.serial:
                where = 'ground2'
            else:
                where = 'cloud'
            for user in users:
                config.update(**params)
                client.login_as(user)
                path = "/dashboard/tariff-daily-summary/daily-avg-consumption.json"
                response = client.get(path)
                variant = '%s-%s' % (where, user.username)
                self.verify_response(response, variant=variant)

    @freeze_time("2016-03-02")
    def test_last_30_days(self, client, config, operator_role):
        other, users = self._createExamplesDashboardDataMultigrid(operator_role)

        for params in [dict(HEROKU=True),
                       dict(HEROKU=True, SERIAL=self.ground.serial),
                       dict(HEROKU=True, SERIAL=other.serial),
                       dict(HEROKU=False, SERIAL=self.ground.serial),
                       dict(HEROKU=False, SERIAL=other.serial)]:
            if params['HEROKU']:
                where = 'cloud'
            else:
                where = 'ground'

            if params.get('SERIAL') == self.ground.serial:
                where += '1'
            elif params.get('SERIAL') == other.serial:
                where += '2'
            for user in users:
                config.update(**params)
                client.login_as(user)
                path = "/dashboard/tariff-daily-summary/last-30-days-consumption.json"
                if params.get('SERIAL'):
                    path += '?' + urllib.parse.urlencode(
                        dict(ground_serial=params.get('SERIAL')))
                response = client.get(path)
                variant = '%s-%s' % (where, user.username)
                self.verify_response(response, variant=variant)
