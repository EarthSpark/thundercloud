# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Utility functions for working with datetime objects."""

from __future__ import division

import datetime

import babel.dates
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc
from past.utils import old_div

from sparkmeter.config.configdict import config
from sparkmeter.user.userutils import get_current_user

_NEXT_MIDNIGHT_BOUNDARY = relativedelta(days=+1, hour=0, minute=0, second=0, microsecond=0)


def datetime_interval_to_day_interval(start, end):
    """Convert a datetime interval to a sequence of day intervals.

    :param start: beginning of interval
    :type start: datetime.datetime
    :param end: end of interval
    :type end: datetime.datetime
    :returns: a sequence of two sized tuples (start datetime, end datetime)
    :raises TypeError: if start or end are not datetime.datetime
    :raises ValueError: if start or end are None
    :raises ValueError: if start and end are not different
    :raises ValueError: if end is before start
    """
    if not isinstance(start, datetime.datetime):
        raise TypeError("start must be a datetime.datetime object, not %s" % (type(start).__name__,))
    if not isinstance(end, datetime.datetime):
        raise TypeError("end must be a datetime.datetime object, not %s" % (type(end).__name__,))
    if start == end:
        raise ValueError("start and end must be different")
    if start > end:
        raise ValueError("start must be before end")

    midnight = start + _NEXT_MIDNIGHT_BOUNDARY
    if end <= midnight:
        return [(start, end)]

    intervals = [(start, midnight)]
    while True:
        prev = midnight
        midnight += _NEXT_MIDNIGHT_BOUNDARY
        if end <= midnight:
            intervals.append((prev, end))
            break
        else:
            intervals.append((prev, midnight))
    return intervals


def reset_datetime_to_time(datetime_, time):
    """Reset the time part of a datetime.datetime object.

    :param datetime_: object to reset time
    :type datetime_: datetime.datetime
    :param time: object to use the time from
    :type time: datetime.time
    :returns: new datetime object with date from the datetime_ object
      and time from the time object
    """
    return datetime_.replace(
        hour=time.hour, minute=time.minute, second=time.second, microsecond=time.microsecond
    )


def format_date(dt, fmt):
    """Format a date in the current locale.

    :param dt: a database to format
    :param fmt: format, see babel for more information.
    :returns: the formatted date.
    """
    return babel.dates.format_date(dt, fmt, locale=get_current_user().locale)


def format_datetime(dt, fmt, tzinfo=None):
    """Format a date in the current locale.

    :param dt: a database to format
    :param fmt: format, see babel for more information.
    :param tzinfo: the timezone or None for UTC
    :returns: the formatted date.
    """
    if tzinfo is None:
        tzinfo = babel.dates.UTC
    return babel.dates.format_datetime(dt, fmt, tzinfo=tzinfo, locale=get_current_user().locale)


def format_minutes(minutes):
    """Convert minutes to a MM:SS string.

    :param minutes: minutes to convert
    :type: int
    :returns: a converted time in MM:SS format
    """
    return "%02d:%02d" % (old_div(minutes, 60), minutes % 60)


def datetime_from_timestamp_string(date_string, tzinfo=None):
    """Load a datetime from a timestamp string.

    :param date_string: string to load from
    :param tzinfo: timezone or None
    :returns: the datetime
    """
    dt = datetime.datetime.utcfromtimestamp(date_string)
    dt = dt.replace(tzinfo=tzinfo)
    return dt


def parse_datetime(value):
    """Parse an date from a string.

    :param value: the date string to parse
    :returns: the datatime object
    :raises ValueError: if the value is not a valid datetime string
    """
    return parse(value)


def datetime_as_utc(dt):
    """Convert a datetime to UTC.

    :param dt: a datetime, tz aware or not
    :returns: tz unaware in UTC
    """
    if dt.tzinfo:
        dt = dt.astimezone(tzutc())
    return dt.replace(tzinfo=None)


def round_time(dt):
    # type: (datetime.datetime) -> datetime.datetime
    """
    Trim the seconds off of a datetime.

    :param datetime dt: the datetime to strip seconds from
    """
    return dt - datetime.timedelta(seconds=dt.second, microseconds=dt.microsecond)


def get_next_heartbeat():
    """
    Get the next heartbeat datetime.

    This strips the current time down to the floored heartbeat period start, then adds the hearbeat period.
    """
    # FIXME: add some sort of caching here
    dt = datetime.datetime.utcnow()
    previous_hb = round_time(dt) - datetime.timedelta(minutes=dt.minute % config["HEARTBEAT_PERIOD"])
    next_hb = previous_hb + datetime.timedelta(minutes=config["HEARTBEAT_PERIOD"])
    return next_hb


def get_next_clear():
    """
    Get the next heartbeat clear datetime.

    This strips the current time down to the floored heartbeat period start,
    then adds the hearbeat period minus the clear time.
    """
    next_clear = get_next_heartbeat() - datetime.timedelta(minutes=config["CLEAR_PERIOD"])
    return next_clear


def month_delta(dt, months):
    """
    Add or subtract calendar months from the specified datetime.

    :param datetime dt: datetime to add or subtract calendar months
    :returns: dt plus the specified number of months

    Examples:
    >>> dt = datetime.datetime(2018, 1, 15)
    >>> month_delta(dt, 1)
    datetime.datetime(2018, 2, 15)
    >>> month_delta(dt, -1)
    datetime.datetime(2017, 12, 15)
    >>> month_delta(dt, 12)
    datetime.datetime(2019, 1, 15)
    >>> dt = datetime.datetime(2018, 1, 31)
    >>> month_delta(dt, 1)
    ValueError: day is out of range for month
    """
    months_per_year = 12
    m = months_per_year * dt.year + (dt.month - 1) + months
    return dt.replace(year=(m // months_per_year), month=(m % months_per_year) + 1)
