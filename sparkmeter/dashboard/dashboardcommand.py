# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Dashboard manage commands.py."""

import datetime
import logging
import operator
from builtins import map

import click
from flask.cli import with_appcontext
from zope.component import getUtility

from sparkmeter.ground.grounddomain import Ground
from sparkmeter.interface import IApplication

logger = logging.getLogger(__name__)

dashboard = click.Group('dashboard', help='Dashboard management commands.')


@dashboard.command('tariff-summary')
@click.argument('day')
@with_appcontext
def tariff_summary(day):
    """Create a daily tariff summary."""
    from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
    from sparkmeter.models import session_scope
    from sparkmeter.tariff.tariffdomain import Tariff

    date = datetime.date(*list(map(int, day.split('-'))))

    with session_scope() as session:
        app = getUtility(IApplication)
        app.setup_databases()
        logger.info('Day %s' % (day, ))
        logger.info('%-15s %3s %8s %8s %6s %6s' % (
            'tariff',
            '#T',
            '$T',
            'kwh',
            '# customers',
            'query time',
        ))
        ground = Ground.get_default()
        for tariff in sorted(Tariff.get_all(), key=operator.attrgetter('name')):
            s = DashboardDailyTariffSummary.create_summary(ground, tariff, date)
            if s is None:
                continue
            logger.info('%-15s %3d %8d %8.2f %6d' % (
                tariff.name,
                s.transaction_count,
                s.transaction_amount,
                s.kwh_consumed,
                s.customer_count))
            session.add(s)
