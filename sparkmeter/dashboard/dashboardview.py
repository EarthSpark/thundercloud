# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Dashboard chart views."""

import datetime
import http.client
from builtins import object

from dateutil.relativedelta import relativedelta
from flask import request
from flask.templating import render_template
from flask.wrappers import Response
from flask_security import roles_accepted
from werkzeug.exceptions import abort

from sparkmeter.config.configdict import config
from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.database.alchemy import sql
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.misc.datetimeutils import format_date
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.blueprint import AuthBlueprint

dashboard = AuthBlueprint('dashboard', __name__)


@dashboard.route("/dashboard/")
@roles_accepted('operator')
def index():
    """Dashboard index page."""
    return render_template('dashboard-index.html')


class LastTwoMonthsChart(object):

    """I create tariff charts for the last two months."""

    def __init__(self, ground, chart_type):
        """Create a new chart."""
        self.ground = ground
        self.chart_type = chart_type
        self.current_month = datetime.datetime.utcnow().date()
        self.previous_month = self.current_month - relativedelta(months=1)

    def _extract(self):
        """
        Extract data from postges directly into a pandas dataframe.

        This generates the appropriate query, then passes that query to pandas to directly import
        the raw data from postgres.
        """
        import pandas  # lazy load pandas to avoid loading it into memory when not needed
        user = get_current_user()
        query = DashboardDailyTariffSummary.get_last_two_months_summary_view(
            ground=self.ground,
            user=user)
        c = query.compile(sql.engine)
        df = pandas.read_sql(
            sql=c.string,
            con=sql.engine,
            params=c.params,
        )
        return df

    def _transform(self, df):
        """
        Transform a pandas dataframe into the data we want to chart.

        Input:
                name        date        transaction_amount  transaction_count  kwh_consumed  customer_count
            0   ANCHOR      2016-02-01  0                   0                  0.000000      2
            1   ANCHOR 1000 2016-02-01  0                   0                  0.000000      1
            2   EKO PWOP    2016-02-01  0                   0                  0.000000      2
        Output:
            name        ANCHOR        ANCHOR 1000  EKO PWOP
            2016-02-01  49.665125     3.429125     1.658125
            2016-03-01  58.241031     5.624906     1.728562
        """
        import pandas  # lazy load pandas to avoid loading it into memory when not needed

        # pivot the data setting the tariffs as columns
        df = df.pivot(index='date', columns='tariff_name', values=self.chart_type)

        # reindex the data using a pandas date_range. This will fill in any missing dates
        # freq=MS gives us a date range based on the start of each month.
        idx = pandas.date_range(end=self.current_month, periods=2, freq='MS')
        df = df.reindex(idx)
        df = df.fillna(0)

        return df

    def _create_chart(self, df):
        import vincent  # lazy load vincent to avoid loading it into memory when not needed

        # hack for vincent not handling the dates properly.
        df['dt'] = df.index
        df['dt'] = df['dt'].apply(lambda x: format_date(x, 'MMM, y'))
        df = df.set_index('dt')

        chart = vincent.StackedBar(df)
        chart.scales['x'].padding = 0.2
        chart.scales['y'].domain_min = 0

        chart.legend(title="Tariffs")
        return chart

    def process(self, fmt="json"):
        """Process a chart."""
        df = self._extract()
        values = self._transform(df)
        if fmt == "json":
            chart = self._create_chart(values)
            return chart.to_json()
        else:
            return values.to_csv(index_label="Date")


class Last30DaysChart(object):

    """I create tariff charts for the last 30 days."""

    def __init__(self, ground, chart_type):
        """Create a new chart."""
        self.ground = ground
        self.chart_type = chart_type
        if self.chart_type == 'last-30-days-sales-amount' or self.chart_type == 'last-30-days-sales-count':
            self.prepaid_only = True
        else:
            self.prepaid_only = False
        # Dates are not available today, so start with yesterday
        self.yesterday = datetime.date.today() - relativedelta(days=1)
        # The starting date is included, so subtract one day so we get a
        # report for 30 days and not 31.
        self.thirty_days_ago = self.yesterday - relativedelta(days=29)

    def _extract(self):
        """
        Extract data from postges directly into a pandas dataframe.

        This generates the appropriate query, then passes that query to pandas to directly import
        the raw data from postgres.
        """
        import pandas  # lazy load pandas to avoid loading it into memory when not needed
        user = get_current_user()
        query = DashboardDailyTariffSummary.get_items_since_view(
            self.thirty_days_ago,
            prepaid_only=self.prepaid_only,
            ground=self.ground,
            user=user,
        )
        c = query.compile(sql.engine)
        df = pandas.read_sql(
            sql=c.string,
            con=sql.engine,
            params=c.params,
            parse_dates=['date'],
        )
        return df

    def _transform(self, df):
        """
        Transform a pandas dataframe into the data we want to chart.

        Input:
                name        date        transaction_amount  transaction_count  kwh_consumed  customer_count
            0   ANCHOR      2016-02-26  0                   0                  0.000000      2
            1   ANCHOR 1000 2016-02-26  0                   0                  0.000000      1
            2   EKO PWOP    2016-02-26  0                   0                  0.000000      2
        Output:
            name        ANCHOR        ANCHOR 1000  EKO PWOP
            2016-01-31  0.000000      0.000000     0.000000
            2016-02-01  49.665125     3.429125     1.658125
            2016-02-02  58.241031     5.624906     1.728562
            2016-02-03  45.366719     2.115937     1.853938
            2016-02-04  55.898438     5.846375     1.957906
        """
        import pandas  # lazy load pandas to avoid loading it into memory when not needed
        attrs = {
            'last-30-days-customer-count': 'customer_count',
            'last-30-days-consumption': 'kwh_consumed',
            'last-30-days-sales-amount': 'transaction_amount',
            'last-30-days-sales-count': 'transaction_count',
        }

        # pivot the data setting the tariffs as columns
        df = df.pivot(index='date', columns='name', values=attrs[self.chart_type])

        # reindex the data using a pandas date_range. This will fill in any missing dates
        idx = pandas.date_range(start=self.thirty_days_ago, end=self.yesterday, freq='D')
        df = df.reindex(idx)
        df = df.fillna(0)

        return df

    def _create_chart(self, df):
        import vincent  # lazy load vincent to avoid loading it into memory when not needed

        # hack for vincent not handling the dates properly.
        df['dt'] = df.index
        df['dt'] = df['dt'].apply(lambda x: format_date(x, 'MMM d'))
        df = df.set_index('dt')

        chart = vincent.StackedBar(df)
        chart.scales['x'].padding = 0.2
        chart.scales['y'].domain_min = 0

        chart.legend(title="Tariffs")
        return chart

    def process(self, fmt="json"):
        """Process a chart."""
        df = self._extract()
        values = self._transform(df)
        if fmt == "json":
            chart = self._create_chart(values)
            return chart.to_json()
        else:
            return values.to_csv(index_label="Date")


@dashboard.route("/dashboard/tariff-daily-summary/<chart_type>.<fmt>")
def tariff_daily_summary(chart_type, fmt="json"):
    """Data for the tariff daily summary charts."""
    if fmt not in ['json', 'csv']:
        abort(http.client.BAD_REQUEST)

    if config['HEROKU']:
        ground_serial = request.args.get('ground_serial')
    else:
        ground_serial = config.get('SERIAL')

    if ground_serial is None:
        ground = None
    else:
        ground = Ground.get_by_serial(ground_serial)

    if chart_type in ['energy-purchase',
                      'monthly-consumption',
                      'daily-avg-consumption']:
        chart = LastTwoMonthsChart(ground, chart_type)
    elif chart_type in ['last-30-days-customer-count',
                        'last-30-days-consumption',
                        'last-30-days-sales-amount',
                        'last-30-days-sales-count']:
        chart = Last30DaysChart(ground, chart_type)
    else:
        abort(http.client.BAD_REQUEST)

    chart_data = chart.process(fmt)

    if fmt == "json":
        return Response(chart_data, mimetype='application/json')
    elif fmt == "csv":
        return Response(chart_data, mimetype='text/csv')
