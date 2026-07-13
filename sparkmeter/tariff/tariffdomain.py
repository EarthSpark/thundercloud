# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Tariff domain models."""

from __future__ import division

import datetime
import logging
import re
from builtins import map, object, str

from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzlocal
from flask_babel import lazy_gettext as _
from past.utils import old_div
from sqlalchemy import func
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Boolean, Float, Integer, String

from sparkmeter.config.configdict import config
from sparkmeter.database.columns import JSONString
from sparkmeter.database.sync import SYNC_CHANNEL_TARIFF, SYNC_GROUP_CLOUD, syncchannel
from sparkmeter.misc.datetimeutils import format_minutes, month_delta, reset_datetime_to_time
from sparkmeter.misc.intervalutils import (
    check_interval_overlaps,
    check_intervals_gap,
    check_intervals_overlap,
)
from sparkmeter.models import BaseDomain

logger = logging.getLogger(__name__)


def find_period(periods, hour):
    """Find a time period given an hour."""
    for period in periods:
        period_start = int(period.start[:2])
        period_end = int(period.end[:2])
        if period_end == 0:
            period_end = 24
        if period_end > period_start:
            matches = hour >= period_start and hour < period_end
        else:
            matches = hour >= period_start or hour < period_end
        if matches:
            return period
    raise ValueError


def parse_plan_duration_and_start_day_string(value):
    """Parse a plan duration string.

    :param value: The value to parse
    :returns: A tuple of the span, unit, and start day
    """
    if value is None:
        raise ValueError("Cannot set the plan to None")
    match = PLAN_DURATION_AND_START_PATTERN.match(value)
    if not match:
        raise ValueError("Invalid plan duration string")
    try:
        span = int(match.group("span"))
        unit = match.group("unit")
        start_day = int(match.group("start_day"))
    except ValueError as verr:  # pragma: nocover
        raise ValueError("Could not parse integer values from {}".format(value)) from verr
    if span <= 0:
        raise ValueError("Span must be greater than 0")
    if start_day <= 0:
        raise ValueError("Start day must be greater than 0")
    return span, unit, start_day


@syncchannel(SYNC_CHANNEL_TARIFF)
class Tariff(BaseDomain):
    """Tariff model."""

    __tablename__ = "tariff"

    #: This tariff is using a flat rate pricing
    TYPE_FLAT = "flat"

    #: This tariff is using blockrate pricing
    TYPE_BLOCKRATE = "blockrate"

    #: The possible tariff types
    TYPES = [TYPE_FLAT, TYPE_BLOCKRATE]

    #: This tariff is using a flat load limit
    LOAD_LIMIT_TYPE_FLAT = "flat"

    #: This tariff is using a scheduled load limit
    LOAD_LIMIT_TYPE_SCHEDULED = "scheduled"

    #: The possible load limit types
    LOAD_LIMIT_TYPES = [LOAD_LIMIT_TYPE_FLAT, LOAD_LIMIT_TYPE_SCHEDULED]

    PLAN_DURATION_UNIT_DAY = "d"

    PLAN_DURATION_UNIT_MONTH = "m"

    PLAN_DURATION_UNITS = [PLAN_DURATION_UNIT_DAY, PLAN_DURATION_UNIT_MONTH]

    #: name of the tariff
    name = Column(String(100), nullable=False)

    #: in watts, the total load limit for this tariff, only used if
    #: load limit is flat.
    flat_load_limit = Column(Integer)

    #: plan price in credits, amount to transfer to plan wallet on purchase
    #: FIXME: a more appropriate name is plan_minimum_spend
    plan_price = Column(Float, server_default="0", default=0.0, nullable=False)

    #: plan fixed fee in credits, cost to purchase a plan
    plan_fixed_fee = Column(Float, server_default="0", default=0.0, nullable=False)

    #: if we should use plan calculation for this tariff
    plan_enabled = Column(Boolean, default=False)

    #: The time scalar spanned by the tariff, in conjunction with plan_duration_unit
    plan_duration_span = Column(Integer, server_default="1", default=1, nullable=False)

    #: The time unit spanned by the tariff, in conjunction with plan_duration_span
    plan_duration_unit = Column(String, default=PLAN_DURATION_UNIT_MONTH, nullable=False)

    #: Day of the month for the plan / cycle to start
    cycle_start_day_of_month = Column(Integer, server_default="1", default=1, nullable=False)

    #: flat price in credit/kwh, fee for the number of credits per kWh
    flat_price = Column(Float)

    #: tariff type
    tariff_type = Column(String, nullable=False)  # Flat/Blockrate Fee

    #: if we should use time calculation for this tariff
    tou_enabled = Column(Boolean, default=False)

    #: the blockrates for this tariff
    blockrates = Column(JSONString, default=[])

    #: the time of uses for this tariff
    tous = Column(JSONString, default=[])

    #: Low balance threshold
    low_balance_threshold = Column(Float, default=0.0, nullable=False)

    #: Load limit, flat or scheduled
    load_limit_type = Column(String, default="flat", nullable=False)

    #: the scheduled load limits for this Tariff
    load_limits = Column(JSONString, default=[])

    #: if we should use daily energy limit calculation for this tariff
    daily_energy_limit_enabled = Column(Boolean, default=False)

    #: the hour in local time that the daily energy limit resets
    daily_energy_limit_reset_hour = Column(Integer, default=0, nullable=False)

    #: the number of kwh that can be consumed during the daily period
    daily_energy_limit_value = Column(Float, default=0.0, nullable=False)

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)

    def __str__(self):  # pragma: nocoverage
        """Tariff object display name."""
        return self.name

    @property
    def plan_duration_and_start_day(self):
        """The plan duration and start day string."""
        if (
            self.plan_duration_span is None
            or self.plan_duration_unit is None
            or self.cycle_start_day_of_month is None
        ):
            return None
        return "{}{}{}".format(
            self.plan_duration_span, self.plan_duration_unit, self.cycle_start_day_of_month
        )

    @plan_duration_and_start_day.setter
    def plan_duration_and_start_day(self, value):
        """Set the plan duration and start day fields from the underlying string."""
        span, unit, start_day = parse_plan_duration_and_start_day_string(value)
        self.plan_duration_span = span
        self.plan_duration_unit = unit
        self.cycle_start_day_of_month = start_day

    @property
    def plan_is_monthly(self):
        return self.plan_duration_unit == self.PLAN_DURATION_UNIT_MONTH

    @property
    def plan_is_daily(self):
        return self.plan_duration_unit == self.PLAN_DURATION_UNIT_DAY

    def get_blockrates(self):
        # type: () -> List[TariffBlockrate]
        """Get a list of Blockrates for this tariff."""
        return list(TariffBlockrate.from_database(self.name, self.blockrates))

    def get_tous(self):
        """Get a list of TOUs for this tariff."""
        # type: () -> List[TariffTOU]
        return list(TariffTOU.from_database(self.name, self.tous))

    def get_load_limits(self):
        """Get a list of TOUs for this tariff."""
        # type: () -> List[TariffLoadLimit]
        return list(TariffLoadLimit.from_database(self.name, self.load_limits))

    def _get_cycle_start_date(self, year, month):
        """Get the date at which the periodic billing cycle would start for a given month

        :param year: year to consider
        :param month: month to consider
        :returns: non-localized datetime
        """
        return datetime.datetime(year=year, month=month, day=self.cycle_start_day_of_month)

    def get_last_cycle_start(self, date):
        """Get the date (UTC) at which the last cycle started.

        This method always returns a date even if the tariff doesn't have a plan enabled.

        :param date: current datetime object in UTC
        :returns: datetime in UTC.
        """
        # Daily plans use the same monthly cycle
        same_month_start_date = self._get_cycle_start_date(year=date.year, month=date.month)
        # return the start day that same month if it's strictly later than date
        if date >= same_month_start_date:
            return same_month_start_date
        return month_delta(same_month_start_date, -1)

    def get_next_cycle_start(self, date):
        """Get the date (UTC) at which a new cycle will start after date

        :param date: datetime object in UTC
        :returns: datetime in UTC.
        """
        if self.plan_is_daily:
            # Daily plans renew 24 hours after the heartbeat_end that triggers a plan not at midnight
            return date + relativedelta(days=1)
        same_month_start_date = self._get_cycle_start_date(year=date.year, month=date.month)
        # return the start day that same month if it's strictly later than date
        if date < same_month_start_date:
            return same_month_start_date
        return month_delta(same_month_start_date, 1)

    def validate_blockrates(self):
        """Validate the block rates for this tariff.

        :raises ValueError: if no block rates are created
        :raises ValueError: if the start/end values are empty
        :raises ValueError: if the start/end does not contain a valid time
        :raises ValueError: if the start/end are equal
        :raises ValueError: if the start value is greater than the end value
        :raises ValueError: if the block rates start/end values overlap
        :raises ValueError: if the block rates start/end values contain gaps
        """
        # FIXME: Int should be validated/converted by form or field.
        intervals = []
        for blockrate in self.get_blockrates():
            blockrate.validate()
            intervals.append((int(blockrate.lower), int(blockrate.upper) or TariffBlockrate.MAX_VALUE))

        if not intervals:
            raise ValueError(_("Please add some block rates."))

        overlap = check_intervals_overlap(intervals)
        if overlap is not None:
            raise ValueError(
                _(
                    "Block rate %(s1)d to %(e1)d overlaps with Block rate %(s2)d to %(e2)d",
                    s1=overlap.start1,
                    e1=overlap.end1,
                    s2=overlap.start2,
                    e2=overlap.end2,
                )
            )

        gaps = check_intervals_gap(intervals, imin=0, imax=TariffBlockrate.MAX_VALUE)
        if gaps:
            raise ValueError(
                _(
                    "Block rates contain at least one gap, between %(start)d and %(end)d",
                    start=gaps[0],
                    end=gaps[-1] + 1,
                )
            )

    def validate_tous(self):
        """Validate the TOUs period for this tariff.

        :raises ValueError: if no periods are created
        :raises ValueError: if the start/end values are empty/a valid time
        :raises ValueError: if the start/end are equal
        :raises ValueError: if the start value is greater than the end value
        :raises ValueError: if the periods start/end values overlap
        :raises ValueError: if the period value is empty/not a number/negative
        """
        intervals = []
        for tou in self.get_tous():
            tou.validate()
            start = tou.start_to_min_after_midnight()
            end = tou.end_to_min_after_midnight()
            if start > end:
                intervals.append((0, end))
                intervals.append((start, 24 * 60))
            else:
                intervals.append((start, end))

        if not intervals:
            raise ValueError(_("Please add some TOU periods."))

        overlap = check_intervals_overlap(intervals)
        if overlap is not None:
            raise ValueError(
                _(
                    "TOU period %(s1)s to %(e1)s overlaps with TOU period %(s2)s to %(e2)s",
                    s1=format_minutes(overlap.start1),
                    e1=format_minutes(overlap.end1),
                    s2=format_minutes(overlap.start2),
                    e2=format_minutes(overlap.end2),
                )
            )

    def validate_load_limits(self):
        """Validate the Load limit period for this tariff.

        :raises ValueError: if no periods are created
        :raises ValueError: if the start/end values are empty/a valid time
        :raises ValueError: if the start/end are equal
        :raises ValueError: if the start value is greater than the end value
        :raises ValueError: if the periods start/end values overlap
        :raises ValueError: if the period value is empty/not a number/negative
        """
        intervals = []
        load_limits = self.get_load_limits()
        for load_limit in load_limits:
            load_limit.validate()
            start = load_limit.start_to_min_after_midnight()
            end = load_limit.end_to_min_after_midnight()
            if start > end:
                intervals.append((0, end))
                intervals.append((start, 24 * 60))
            else:
                intervals.append((start, end))

        if not intervals:
            raise ValueError(_("Please add some Load limit periods."))

        overlap = check_intervals_overlap(intervals)
        if overlap is not None:
            raise ValueError(
                _(
                    "Load limit period %(s1)s to %(e1)s overlaps with load limit period %(s2)s to %(e2)s",
                    s1=format_minutes(overlap.start1),
                    e1=format_minutes(overlap.end1),
                    s2=format_minutes(overlap.start2),
                    e2=format_minutes(overlap.end2),
                )
            )

        uncovered = []
        for hour in range(24):
            try:
                find_period(load_limits, hour)
            except ValueError:
                uncovered.append(hour)
        if uncovered:
            raise ValueError(
                _(
                    "Load limit periods needs to cover %(hours)s",
                    hours=", ".join("{:2d}:00".format(h) for h in uncovered),
                )
            )

    def get_average_block_rate(self, lower, upper):
        """Calculate the average block rate for an interval.

        :param upper: upper of the interval to check
        :type upper: number (float or int)
        :param lower: lower of the interval to check
        :type lower: number (float or int)
        :returns: average rate for the time
        :rtype: float
        :raises TypeError: if upper or lower are not numbers
        :raises ValueError: if upper or lower are negative
        :raises ValueError: if lower is before upper
        """
        if not isinstance(lower, (float, int)):
            raise TypeError("lower must be a number, not %r" % (type(upper).__name__,))
        if not isinstance(upper, (float, int)):
            raise TypeError("upper must be a number, not %r" % (type(upper).__name__,))
        if upper < 0 and lower < 0:
            raise ValueError("upper and lower must be positive, not [{},{}]".format(lower, upper))
        if lower > upper:
            raise ValueError("upper must be higher than lower")

        rate = 0.0
        for blockrate in self.get_blockrates():
            if blockrate.overlap(lower, upper):
                if lower == upper:
                    multiplier = 1
                else:
                    overlap_lower = max(blockrate.lower, lower)
                    # Special case 0 which means, no limit
                    if blockrate.upper == 0:
                        overlap_upper = upper
                    else:
                        overlap_upper = min(blockrate.upper, upper)
                    multiplier = overlap_upper - overlap_lower
                rate += blockrate.value * multiplier

        delta = upper - lower
        if rate and delta:
            rate /= delta

        return rate

    @classmethod
    def get_by_name(cls, name, fail_on_multiple=False):
        """Get the tariffs with a given name.

        :param name: The name of the tariff
        :param fail_on_multiple: `True` if an exception should be raised when multiple tariffs with the
            same name exist
        :returns: The first tariff with a matching name
        """
        query = cls.query.filter(func.lower(cls.name) == func.lower(name))
        # To make sure the order is not undefined for testing purposes.
        query = query.order_by("name")
        if query.count() > 1:
            if fail_on_multiple:
                raise MultipleResultsFound("Multiple tariffs with name {} found".format(name))
            logger.warning("More than one tariff exists with the name %s. Using the first one." % (name,))
        elif query.count() == 0:
            raise NoResultFound("no tariff with name {} found.".format(name))
        return query.first()

    def display_rate(self):
        """Return a displayable formatted rate depending on the tariff_type."""
        if self.tariff_type == "flat":
            return str(self.flat_price)
        elif self.tariff_type == "blockrate":
            rates = [float(bl.value) for bl in self.get_blockrates()]
            return _("%(min)s to %(max)s", min=min(rates), max=max(rates))

    def display_tou(self):
        """Return a displayable formatted tou percent range."""
        if not self.tou_enabled:
            return ""

        mods = [float(tou.value) for tou in self.get_tous()]
        # add 100 to the list so if only one modifier is set it
        # doesn't look like the normal is never used
        mods.append(100)

        return _("%(min)d%% to %(max)d%%", min=min(mods), max=max(mods))

    def display_load_limit(self):
        """Return a displayable formatted load limit."""
        if self.load_limit_type == "flat":
            return str(self.flat_load_limit)

        mods = [float(p.value) for p in self.get_load_limits()]
        return _("%(min)d to %(max)d", min=min(mods), max=max(mods))

    def display_plan(self):
        """Return a displayable formatted plan."""
        if not self.plan_enabled:
            return _("Off")
        time_unit = "day" if self.plan_is_daily else "month"
        plan_cost = self.plan_price + self.plan_fixed_fee
        return "{} {} for {} {}".format(self.plan_duration_span, time_unit, plan_cost, config["CURRENCY"])

    # FIXME: Move this over to Meter.get_by_tariff
    def get_meters(self):
        """Get all meters using this tariff."""
        from sparkmeter.meter.meterdomain import Meter, MeterBilling

        return Meter.query.filter(
            Meter.meter_type == Meter.TYPE_CUSTOMER,
            MeterBilling.meter_id == Meter.id,
            MeterBilling.tariff_id == self.id,
        )

    # FIXME: This does not belong here, move to call-site, eg:
    #  for meter in Meter.get_by_tariff(tariff)
    #      meter.update_meter_state()
    def update_meters(self):
        """
        Update all meters with this tariff.

        This is used when changing a tariff power limit so we can make sure the new limit is applied.
        :returns: The number of meters updated.
        """
        i = 0
        for i, meter in enumerate(self.get_meters(), start=1):  # pragma: nocoverage
            # FIXME: Should be based on system_info
            meter.send_set_config_unconditionally()
        return i

    def get_current_load_limit(self, when=None):
        # type: (Optional[datetime.datetime]) -> int
        """Get the current load limit for a time of day.

        :param: when is a datetime object in localtime
        :returns: load limit in watts.
        """
        if self.load_limit_type == Tariff.LOAD_LIMIT_TYPE_FLAT:
            return self.flat_load_limit

        if when is None:
            when = datetime.datetime.now()

        period = find_period(self.get_load_limits(), when.hour)
        return int(period.value)

    def last_daily_energy_limit_reset_datetime(self):
        """Get the datetime for the last time the daily limit should have been reset.

        :returns: the last time the daily limit should have been reset.
        :rtype: datetime
        """
        current_hour = datetime.datetime.now().hour
        reset_hour = datetime.time(hour=self.daily_energy_limit_reset_hour)
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        if current_hour < self.daily_energy_limit_reset_hour:
            # we have not yet crossed the hour today, use yesterdays date
            return datetime.datetime.combine(yesterday, reset_hour)

        # otherwise use todays date for the last reset time
        return datetime.datetime.combine(today, reset_hour)


PLAN_DURATION_AND_START_PATTERN = re.compile(
    r"^(?P<span>\d+)(?P<unit>[{}])(?P<start_day>\d+)$".format("".join(Tariff.PLAN_DURATION_UNITS))
)


def _parse_dict_value(d, key, value_type):
    value = d.get(key)
    if value is not None:
        try:
            value = value_type(value)
        except ValueError:
            # Cannot parse the value, e.g.: string without a number for int/float
            value = None
        except TypeError:
            # Bad type, list, {}, None
            value = None
    return value


class TariffBlockrate(object):
    """Tariff blockrate model."""

    # FIXME: Get rid of this maximum value
    #   3686400 is the theoretical max for a 240v system. Half that for a 120v. I think.
    #   65535 * 2 is the max for the power limit
    MAX_VALUE = 65535

    def __init__(self, lower, upper, value):
        #: type: (int, int, float) -> None
        if not isinstance(lower, int):
            raise TypeError("lower must be an int, not {!r}.".format(lower))
        self.lower = lower

        if not isinstance(upper, int):
            raise TypeError("upper must be an int, not {!r}.".format(upper))
        self.upper = upper

        if type(value) not in [float, int]:
            raise TypeError("value must be a number, not {!r}.".format(value))
        self.value = value

    def __repr__(self):
        return "<{} lower={} upper={} value={}>".format(
            type(self).__name__, self.lower, self.upper, self.value
        )

    def __eq__(self, other):
        if self.lower != other.lower:
            return False
        if self.upper != other.upper:
            return False
        if self.value != other.value:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_database(cls, tariff_name, blockrates):
        # type: (str, List[Dict[str, Union[str, float]]]) -> Iterable[TariffBlockrate]
        """Create a new Tariff Blockrate from a dict.

        The dict is expected to come from the database.

        :param tariff_name: name of the parent tariff
        :param tous: a list of dictionaries
        :returns: a generator of newly created TariffBlockrate instances.
        """
        for d in blockrates:
            lower = _parse_dict_value(d, "lower", int)
            upper = _parse_dict_value(d, "upper", int)
            value = _parse_dict_value(d, "value", float)
            if lower is None or upper is None or value is None:
                logger.warning("Tariff {} has a blockrate tou: {}".format(tariff_name, d))
                continue
            yield cls(lower=lower, upper=upper, value=value)

    def overlap(self, lower, upper):
        """Check if an interval overlaps with this block rate.

        :param lower: lower interval point
        :param upper: upper interval point
        :returns: `True` if they overlap, `False` otherwise.
        """
        # Special case 0 which means, no limit
        if self.upper == 0:
            blockrate_upper = upper
        else:
            blockrate_upper = self.upper

        if lower == upper:
            return self.lower < lower <= blockrate_upper
        return check_interval_overlaps(self.lower, blockrate_upper, lower, upper)

    def validate(self):
        """Validate a block rate.

        :raises ValueError: if the start/end values are empty
        :raises ValueError: if the start/end does not contain a valid time
        :raises ValueError: if the start/end are equal
        :raises ValueError: if the start value is greater than the end value
        """
        # Validate lower
        lower = self.lower
        if lower < 0:
            raise ValueError(_("The lower value of a block rate must be a positive number."))

        # Validate upper
        upper = self.upper
        if upper < 0:
            raise ValueError(_("The upper value of a block rate must be a positive number."))

        if upper == 0:
            upper = TariffBlockrate.MAX_VALUE

        # Validate lower/upper
        if lower == upper:
            raise ValueError(
                _(
                    "Block rate lower (%(lower)d) must be different from upper (%(upper)d)",
                    lower=lower,
                    upper=upper,
                )
            )

        if lower > upper:
            raise ValueError(
                _(
                    "Block rate upper (%(upper)d) must be higher than lower (%(lower)d)",
                    lower=lower,
                    upper=upper,
                )
            )

        # Validate value
        value = self.value
        if value < 0:
            raise ValueError(_("The block rate value must be a positive number."))


class _TariffPeriod(object):
    """Tariff base period.

    Used by TOU and LoadLimit which are conceptually similar.
    """

    class_name = ""

    def __init__(self, start, end, value):
        # type: (str, str, Union[float, int]) -> None
        if not isinstance(start, str):
            raise TypeError("start must be a str, not {!r}.".format(start))
        self.start = start

        if not isinstance(end, str):
            raise TypeError("end must be a str, not {!r}.".format(end))
        self.end = end

        if type(value) not in [float, int]:
            raise TypeError("value must be a number, not {!r}.".format(value))
        self.value = value

    def __repr__(self):
        return "<{} start={} end={} value={}>".format(type(self).__name__, self.start, self.end, self.value)

    def __eq__(self, other):
        if self.start != other.start:
            return False
        if self.end != other.end:
            return False
        if self.value != other.value:
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_database(cls, tariff_name, tous):
        # type: (List[Dict[str, Union[str, float]]]) -> Iterable[Any]
        """Create a new period from a dict.

        The dict is expected to come from the database.

        :param tariff_name: name of the parent tariff
        :param tous: a list of dictionaries
        :returns: a generator of newly created period instances.
        """
        for d in tous:
            start = _parse_dict_value(d, "start", str)
            end = _parse_dict_value(d, "end", str)
            value = _parse_dict_value(d, "value", float)
            if start is None or end is None or value is None:
                logger.warning("Tariff {} has a bad tou: {}".format(tariff_name, d))
                continue
            yield cls(start=start, end=end, value=value)

    def superset_of(self, heartbeat_start, heartbeat_end):
        """Check if heartbeat_start/heartbeat_end interval is within this period.

        :param heartbeat_start: start of the interval to check
        :type heartbeat_start: datetime.datetime.
        :param heartbeat_end: heartbeat_end of the interval to check
        :type heartbeat_end: datetime.datetime.
        :returns: `True` if they overlap, otherwise `False`
        :raises TypeError: if heartbeat_start or heartbeat_end are not datetime.datetime
        :raises ValueError: if heartbeat_start or heartbeat_end are None
        :raises ValueError: if heartbeat_start and heartbeat_end are not different
        :raises ValueError: if heartbeat_end is before heartbeat_start
        """
        if not isinstance(heartbeat_start, datetime.datetime):
            raise TypeError(
                "heartbeat_start must be a datetime.datetime, not a '%s'" % (type(heartbeat_start).__name__,)
            )
        if not isinstance(heartbeat_end, datetime.datetime):
            raise TypeError(
                "heartbeat_end must be a datetime.datetime, not a '%s'" % (type(heartbeat_end).__name__,)
            )
        if heartbeat_start == heartbeat_end:
            raise ValueError(
                "heartbeat_start (%s) and heartbeat_end (%s) must be different"
                % (heartbeat_start, heartbeat_end)
            )
        if heartbeat_start.tzinfo != tzlocal():
            raise ValueError("heartbeat_start must be in tzlocal() timezone")
        if heartbeat_end.tzinfo != tzlocal():
            raise ValueError("heartbeat_end must be in tzlocal() timezone")

        start = datetime.time(*list(map(int, self.start.split(":"))))
        end = datetime.time(*list(map(int, self.end.split(":"))))

        # Reset the start/end for this period relative to the start date, use
        # the start date as a reference for both so that they end up on the
        # same day, which is important for some of the checks below.
        tou_start = reset_datetime_to_time(heartbeat_start, start)
        tou_end = reset_datetime_to_time(heartbeat_start, end)

        # Simple case, heartbeat end is after heart beat start, do a simple
        # range check of hr_start/hr_end in [tou_start..tou_end)
        if start < end:
            return tou_end > heartbeat_start >= tou_start and tou_end >= heartbeat_end > tou_start

        # Heartbeat starting after heartbeat end means that we have a period
        # that crosses a midnight boundary. Remember that period start/end are
        # swapped here, since start > end,

        # First figure out the two midnights,
        # 1) this is the midnight before the heartbeat_start
        midnight_before = reset_datetime_to_time(heartbeat_start, datetime.time(0))
        # 2) and this is the one the day after (or the next day)
        midnight_after = midnight_before + relativedelta(days=1)

        # Then reset heartbeat end previous day so that we can use
        # midnight before and tou end to check the right interval period
        if heartbeat_end > midnight_after:
            heartbeat_end -= relativedelta(days=1)

        # We have three different intervals to check:
        # For example, let's assume that we have these two periods:
        #   06..20: period1 (daylight)
        #   20..06: period2 (darkness)
        #
        # The daylight period check is already done above, since it's within
        # a simple period, to be able to check if a heartbeat is within
        # the "darkness"
        # period, that crosses a midnight boundary, we need to check
        # the following:
        #   00..06, eg between midnight before heartbeat start and tou end (a)
        #   20..00, eg between tou start and the next midnight (b)
        #   20..06, eg a midnight boundary crossing (c)

        # a) between midnight and the beginning of the period
        if tou_end > heartbeat_start >= midnight_before and tou_end >= heartbeat_end > midnight_before:
            return True
        # b) between TOU start and the midnight the next day
        elif midnight_after > heartbeat_start >= tou_start and midnight_after >= heartbeat_end > tou_start:
            return True
        # c) heartbeat start before midnight, heartbeat end after midnight
        elif midnight_after > heartbeat_start >= tou_start and tou_end >= heartbeat_end > midnight_before:
            return True
        else:
            return False

    def validate(self):
        """Validate a period.

        :raises ValueError: if the start/end values are empty
        :raises ValueError: if the start/end does not contain a valid time
        :raises ValueError: if the start/end are equal
        :raises ValueError: if the start value is greater than the end value
        """
        # FIXME: Times should be validated/converted by form or field.
        # FIXME: If we will allow 24:00 times in the future, we should do the substitution here
        try:
            start = self.start_to_min_after_midnight()
        except ValueError:
            raise ValueError(
                _(
                    "The start value of a {} must be a valid time, not {}.".format(
                        self.class_name,
                        self.start,
                    )
                )
            )

        try:
            end = self.end_to_min_after_midnight()
        except ValueError:
            raise ValueError(
                _(
                    "The end value of a {} must be a valid time, not {}.".format(
                        self.class_name,
                        self.end,
                    )
                )
            )

        if start == end:
            raise ValueError(
                _(
                    "{} start ({}) must be different from end ({})".format(
                        self.class_name, format_minutes(start), format_minutes(end)
                    )
                )
            )
        if not self.start.endswith(":00"):
            raise ValueError('The {} "{}" must start on the hour'.format(self.class_name, self.start))
        if not self.end.endswith(":00"):
            raise ValueError('The {} "{}" must end on the hour'.format(self.class_name, self.end))
        if self.value < 0:
            raise ValueError(
                _(
                    "The {} modifier must be a positive number.".format(
                        self.class_name,
                    )
                )
            )

    def start_to_min_after_midnight(self):
        """Convert the start time of this period to minutes after midnight.

        :returns: minutes after midnight
        :rtype: int
        """
        start = parse("1900-01-01 " + str(self.start))

        # Python time() objects, which we store in SQL, shouldn't need to be converted to
        # datetime, however, you cannot A) do deltas with times() B) parse() always return
        # datetime objects. So let's convert to minutes after midnight which we can easily
        # use to check for overlaps
        return int(old_div((start - datetime.datetime(1900, 1, 1)).total_seconds(), 60))

    def end_to_min_after_midnight(self):
        """Convert the end time of this TOU to minutes after midnight.

        :returns: minutes after midnight
        :rtype: int
        """
        if self.end in ["00:00", "24:00"]:
            endstr = "1900-01-02 00:00"
        else:
            endstr = "1900-01-01 " + str(self.end)

        end = parse(endstr)

        # Python time() objects, which we store in SQL, shouldn't need to be converted to
        # datetime, however, you cannot A) do deltas with times() B) parse() always return
        # datetime objects. So let's convert to minutes after midnight which we can easily
        # use to check for overlaps
        end = int(old_div((end - datetime.datetime(1900, 1, 1)).total_seconds(), 60))

        # To be able to check the whole ranges of dates between 00:00 and 23:59 we allow
        # the user to shortcut 23:59 + one second as 00:00, but only for the end range of
        # the value
        if end == 0:
            end = 24 * 60

        return end


class TariffTOU(_TariffPeriod):
    class_name = "TOU period"


class TariffLoadLimit(_TariffPeriod):
    class_name = "Load limit period"
