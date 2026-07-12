# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Tasks relating to the dashboard."""

import datetime
import logging

from dateutil.relativedelta import relativedelta
from dateutil.tz import tzlocal, tzutc
from flask.globals import current_app

from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.models import session_scope
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.transaction.transactiondomain import Transaction

logger = logging.getLogger(__name__)


def nightly_dashboard_tariff_summary():
    """Collect tariff summaries for date before being run.

    This function's goal is to process all transactions that were processed
    yesterday and create a summary for that day.
    Since transactions are stored in UTC in the database, but this function is
    in local time and thus yesterday must be converted to UTC.
    """
    ground = Ground.get_default()
    yesterday = datetime.date.today() - relativedelta(days=1)
    # Find the start time in UTC
    yesterday_start = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=tzlocal())
    yesterday_start = yesterday_start.astimezone(tzutc()).replace(tzinfo=None)
    yesterday_end = yesterday_start + relativedelta(days=1)

    logger.info(
        "Queuing dashboard summary generation for all tariffs for %s, start=%s, end=%s",
        yesterday,
        yesterday_start,
        yesterday_end,
    )

    with current_app.app_context(), session_scope() as session:
        days_to_reprocess = [
            day.day_created
            for day in Transaction.get_processed_by_day(
                ground, yesterday_start, yesterday_end, created_before=yesterday
            )
        ]
        for tariff in Tariff.get_all():
            if DashboardDailyTariffSummary.query.filter_by(tariff=tariff, date=yesterday).count():
                logger.info(
                    "Skipping tariff summary for Tariff %s, existing summary found for %s"
                    % (tariff.name, yesterday)
                )
            else:
                summary = DashboardDailyTariffSummary.create_summary(ground, tariff, yesterday)
                if summary is None:
                    logger.info(
                        "Skipping tariff summary for Tariff %s, no updates during %s"
                        % (tariff.name, yesterday)
                    )
                else:
                    session.add(summary)

            for day in days_to_reprocess:
                day_summary = DashboardDailyTariffSummary.create_summary(ground, tariff, day.date())
                if day_summary is not None:
                    existing = DashboardDailyTariffSummary.get(ground, tariff, day.date()).one_or_none()
                    if existing:
                        day_summary.id = existing.id
                    logger.info("Refreshing tariff summary for Tariff %s on %s", tariff.name, day.date())
                    session.merge(day_summary)
