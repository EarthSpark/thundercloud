# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Dashboard domain models."""

from __future__ import division

import datetime

from dateutil.relativedelta import relativedelta
from dateutil.tz import tzlocal, tzutc
from flask_babel import lazy_gettext as _
from past.utils import old_div
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import and_, func, select
from sqlalchemy.sql.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.sql.sqltypes import Date, Float, Integer, Interval

from sparkmeter.database.sync import SYNC_CHANNEL_DASHBOARD, SYNC_GROUP_GROUND, syncchannel
from sparkmeter.database.tables import get_table_by_name
from sparkmeter.database.types import UUIDType
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterdomain import MeterView
from sparkmeter.models import BaseDomain
from sparkmeter.reading.readingdomain import Reading
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.transaction.transactiondomain import Transaction


@syncchannel(SYNC_CHANNEL_DASHBOARD)
class DashboardDailyTariffSummary(BaseDomain):
    """DashboardDailyTariffSummary Postgres SQLAlchemy Model.

    A DashboardDailyTariffSummary is a daily summary of reading/meter data grouped by tariff
    for a certain time period.
    """

    __tablename__ = "dashboard_daily_tariff_summary"
    __table_args__ = (
        UniqueConstraint(
            "ground_id", "tariff_id", "date", name="dashboard_tariff_summary_ground_tariff_date_unique"
        ),
    )

    #: The tariff this summary belongs to
    tariff_id = Column(
        UUIDType(binary=False),
        ForeignKey("tariff.id"),
        nullable=False,
        info={"label": _("Tariff Id")},
    )

    #: The ground this summary belongs to
    ground_id = Column(
        UUIDType(binary=False),
        ForeignKey("ground.id"),
        nullable=False,
    )

    #: The date in local time for this report.
    #: Note: Be careful when using this since almost all other times in
    #:       the database are stored in UTC
    date = Column(Date, nullable=False)

    #: The sum of all transactions values in this period
    transaction_amount = Column(Integer, nullable=False)

    #: The count of all transactions in this period
    transaction_count = Column(Integer, nullable=False)

    #: The sum of all readings energy values in this period
    kwh_consumed = Column(Float, nullable=False)

    #: The count of all active meters associated with this tariff during this period
    customer_count = Column(Integer, default=0, nullable=False)

    #: The relationship to the tariff in this summary object
    tariff = relationship("Tariff")

    #: The relationship to the ground in this summary object
    ground = relationship("Ground")

    @classmethod
    def get(cls, ground, tariff, date):
        """Get the summary associated with the provided parameters.

        :param ground: The ground associated with the summary
        :param tariff: The tariff associated with the summary
        :param date: The date associated with the summary
        """
        return cls.query.filter_by(ground=ground, tariff=tariff, date=date)

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for the this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                Ground.id == group.format_trigger_attr(cls.ground_id),
                distinct=True,
            )

    @classmethod
    def create_summary(cls, ground, tariff, date):
        """Create a summary based on a tariff and date."""
        if not isinstance(ground, Ground):
            raise TypeError("ground must be a Ground, not %s" % (type(ground).__name__))
        if not isinstance(tariff, Tariff):
            raise TypeError("tariff must be a Tariff, not %s" % (type(tariff).__name__))
        if not isinstance(date, datetime.date):
            raise TypeError("date must be a datetime.date, not %s" % (type(date).__name__))

        # Local time when this period starts, convert it to UTC and strip tzinfo
        # Since we use UTC without tzinfo in the DB.
        period_start = datetime.datetime(date.year, date.month, date.day, tzinfo=tzlocal())
        period_start = period_start.astimezone(tzutc()).replace(tzinfo=None)
        period_end = period_start + relativedelta(days=1)

        # Transaction for a specific tariff/period
        results = list(Transaction.get_by_tariff_period(tariff, ground, period_start, period_end))
        if results:
            transaction_amount, transaction_count = results[0]
        else:
            transaction_amount, transaction_count = 0, 0

        # Readings for a specific tariff/period
        query = Reading.get_by_tariff_date(tariff, ground, period_start, period_end)
        readings = query.with_entities(func.coalesce(func.sum(Reading.kilowatt_hours), 0))
        total_kwh = readings.one()[0]

        # Meters for a specific tariff
        meter_views = MeterView.get_view(active=True, ground=ground, tariff=tariff)
        meter_count = meter_views.count()
        # If the tariff contains no customers, nor transactions nor consumption
        # do not create a summary, skip it.
        if meter_count == 0 and transaction_count == 0 and total_kwh == 0:
            return None
        summary = cls(
            date=date,
            ground=ground,
            tariff=tariff,
            transaction_amount=transaction_amount,
            transaction_count=transaction_count,
            kwh_consumed=total_kwh,
            customer_count=meter_count,
        )

        return summary

    @classmethod
    def get_items_since_view(cls, date, prepaid_only=False, ground=None, user=None):
        """Get all summary items since a date.

        :param date: the date for the earliest summaries.
        :type: date: datetime.date
        :param prepaid_only: If set to True, only include pre-paid meter.
        :type prepaid_only: bool
        :param ground: ground to display the summaries for
        :type ground: sparkmeter.ground.grounddomain.Ground
        :param user: restrict the dashboard summaries to a user or ``None``
        :type user: sparkmeter.user.userdomain.User
        """
        ground_t = get_table_by_name("ground")

        columns = [
            Tariff.name,
            cls.date,
            func.sum(cls.transaction_amount).label("transaction_amount"),
            func.sum(cls.transaction_count).label("transaction_count"),
            func.sum(cls.kwh_consumed).label("kwh_consumed"),
            func.sum(cls.customer_count).label("customer_count"),
        ]
        joins = cls.__table__.join(ground_t, cls.ground_id == ground_t.c.id).join(
            Tariff, cls.tariff_id == Tariff.id
        )
        wheres = [
            cls.date >= date,
            cls.date < datetime.date.today(),
        ]
        if ground is not None:
            wheres.append(ground_t.c.id == ground.id)

        if user is not None:
            users_ground_t = get_table_by_name("users_grounds")
            subquery = select(users_ground_t.c.ground_id).where(users_ground_t.c.user_id == user.id)
            wheres.append(ground_t.c.id.in_(subquery))

        query = (
            select(*columns)
            .select_from(joins)
            .where(and_(*wheres))
            .group_by(Tariff.name, cls.date)
            .order_by(Tariff.name)
            .distinct()
        )

        # FIXME: filter out postpaid summaries using a prepaid field

        return query

    @classmethod
    def get_last_two_months_summary_view(cls, ground=None, user=None):
        """Get a summary for a tariff and a date.

        This queries the db for the last two months of summary data.
        It then groups the data by tariff name with the following functions:
            min of the date
            sum of transaction_amount
            sum of kwh_consumed
            avg of kwh_consumed

        :param ground: ground to display the summaries for
        :type ground: sparkmeter.ground.grounddomain.Ground
        :param user: restrict the dashboard summaries to a user or ``None``
        :type user: sparkmeter.user.userdomain.User
        :returns: a sql query of the summarized data
        """
        ground_t = get_table_by_name("ground")

        today = datetime.date.today()
        yesterday = today - relativedelta(days=1)
        first_last_month = today + relativedelta(months=-1, day=1)
        columns = [
            Tariff.name.label("tariff_name"),
            func.cast(func.date_trunc("month", cls.date), Date).label("date"),
            func.sum(cls.transaction_amount).label("energy-purchase"),
            func.sum(cls.kwh_consumed).label("monthly-consumption"),
            # SUM(consumed) / min(last day of month, yesterday)
            (
                old_div(
                    func.sum(cls.kwh_consumed),
                    func.date_part(
                        "day",
                        func.least(
                            # Last day of the month
                            func.date_trunc("month", cls.date) + func.cast("1 month - 1 day", Interval),
                            yesterday,
                        ),
                    ),
                )
            ).label("daily-avg-consumption"),
        ]
        joins = cls.__table__.join(ground_t, cls.ground_id == ground_t.c.id).join(
            Tariff, cls.tariff_id == Tariff.id
        )
        wheres = [
            cls.date >= first_last_month,
            cls.date < today,
        ]
        if ground is not None:
            wheres.append(ground_t.c.id == ground.id)

        if user is not None:
            users_ground_t = get_table_by_name("users_grounds")
            subquery = select(users_ground_t.c.ground_id).where(users_ground_t.c.user_id == user.id)
            wheres.append(ground_t.c.id.in_(subquery))

        query = (
            select(*columns)
            .select_from(joins)
            .where(and_(*wheres))
            # group by month
            .group_by(Tariff.name, func.date_trunc("month", cls.date))
        ).order_by(Tariff.name)

        return query
