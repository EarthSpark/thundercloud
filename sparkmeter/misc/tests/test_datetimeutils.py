# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Unittests for sparkmeter.misc.datetimeutils"""

import datetime

import freezegun
import pytest

from sparkmeter.misc.datetimeutils import (
    datetime_interval_to_day_interval,
    get_next_clear,
    get_next_heartbeat,
    month_delta,
    reset_datetime_to_time,
)


def test_datetime_interval_to_day_interval_same_day():
    intervals = datetime_interval_to_day_interval(
        datetime.datetime(2001, 1, 5, 12, 0), datetime.datetime(2001, 1, 5, 18, 0)
    )

    assert intervals == [(datetime.datetime(2001, 1, 5, 12, 0), datetime.datetime(2001, 1, 5, 18, 0))]


def test_datetime_interval_to_day_interval_one_crossing():
    intervals = datetime_interval_to_day_interval(
        datetime.datetime(2001, 1, 5, 23, 0), datetime.datetime(2001, 1, 6, 1, 0)
    )

    assert intervals == [
        (datetime.datetime(2001, 1, 5, 23, 0), datetime.datetime(2001, 1, 6, 0, 0)),
        (datetime.datetime(2001, 1, 6, 0, 0), datetime.datetime(2001, 1, 6, 1, 0)),
    ]


def test_datetime_interval_to_day_interval_two_crossings():
    intervals = datetime_interval_to_day_interval(
        datetime.datetime(2001, 1, 5, 12, 0), datetime.datetime(2001, 1, 7, 12, 0)
    )

    assert intervals == [
        (datetime.datetime(2001, 1, 5, 12, 0), datetime.datetime(2001, 1, 6, 0, 0)),
        (datetime.datetime(2001, 1, 6, 0, 0), datetime.datetime(2001, 1, 7, 0, 0)),
        (datetime.datetime(2001, 1, 7, 0, 0), datetime.datetime(2001, 1, 7, 12, 0)),
    ]


def test_datetime_interval_to_day_interval_start_at_midnight():
    intervals = datetime_interval_to_day_interval(
        datetime.datetime(2001, 1, 6, 0, 0), datetime.datetime(2001, 1, 6, 10, 0)
    )

    assert intervals == [(datetime.datetime(2001, 1, 6, 0, 0), datetime.datetime(2001, 1, 6, 10, 0))]


def test_datetime_interval_to_day_interval_end_at_midnight():
    intervals = datetime_interval_to_day_interval(
        datetime.datetime(2001, 1, 5, 23, 0), datetime.datetime(2001, 1, 6, 0, 0)
    )

    assert intervals == [(datetime.datetime(2001, 1, 5, 23, 0), datetime.datetime(2001, 1, 6, 0, 0))]


def test_datetime_interval_to_day_interval_errors():
    msg = "start must be a datetime.datetime object, not int"
    with pytest.raises(TypeError, match=msg):
        datetime_interval_to_day_interval(1, 1)

    now = datetime.datetime.now()
    msg = "end must be a datetime.datetime object, not int"
    with pytest.raises(TypeError, match=msg):
        datetime_interval_to_day_interval(now, 1)

    now = datetime.datetime.now()
    msg = "start and end must be different"
    with pytest.raises(ValueError, match=msg):
        datetime_interval_to_day_interval(now, now)

    now = datetime.datetime.now()
    msg = "start must be before end"
    with pytest.raises(ValueError, match=msg):
        datetime_interval_to_day_interval(start=now.replace(year=3000, month=1, day=1), end=now)


def test_reset_datetime_to_time():
    d = datetime.datetime(2001, 2, 3)
    t = datetime.time(12, 34, 56, 789)
    v = reset_datetime_to_time(d, t)
    assert v == datetime.datetime(2001, 2, 3, 12, 34, 56, 789)


def test_get_next_heartbeat(config):
    for period in [15, 60]:
        config["HEARTBEAT_PERIOD"] = period
        for h in [0, 12]:
            for m in [4, 30, 44, 59]:
                for s in [0, 30]:
                    dt = datetime.datetime(2018, 1, 1, h, m, s)
                    with freezegun.freeze_time(dt):
                        expected = dt.replace(
                            minute=dt.minute // period * period, second=0, microsecond=0
                        ) + datetime.timedelta(minutes=period)
                        assert get_next_heartbeat() == expected


def test_get_next_clear(config):
    config["HEARTBEAT_PERIOD"] = 15
    for clear in [2, 10]:
        config["CLEAR_PERIOD"] = clear
        for h in [0, 12]:
            for m in [4, 30, 44, 59]:
                for s in [0, 30]:
                    dt = datetime.datetime(2018, 1, 1, h, m, s)
                    with freezegun.freeze_time(dt):
                        next = get_next_heartbeat()
                        next_clear = get_next_clear()
                        assert next_clear == next - datetime.timedelta(minutes=clear)


@pytest.mark.parametrize(
    "dt_tuple, months, expected",
    (
        ((1, 1, 1), -1, ValueError("year 0 is out of range")),
        ((2018, 1, 1), 1, (2018, 2, 1)),
        # handles year rollover going backwards
        ((2018, 1, 1), -1, (2017, 12, 1)),
        ((2018, 1, 1), -13, (2016, 12, 1)),
        # handles year rollover going forward
        ((2017, 12, 1), 1, (2018, 1, 1)),
        ((2018, 1, 1), 13, (2019, 2, 1)),
        # preserves days, hours, minutes, etc.
        ((2018, 1, 15, 1, 1, 1, 1), 1, (2018, 2, 15, 1, 1, 1, 1)),
        # exception thrown when an invalid date would be created
        ((2018, 1, 31), 1, ValueError("day is out of range for month")),
    ),
)
def test_month_delta(dt_tuple, months, expected):
    dt = datetime.datetime(*dt_tuple)
    if isinstance(expected, Exception):
        with pytest.raises(type(expected)) as ex:
            actual = month_delta(dt, months)
        assert ex.value.args == expected.args
    else:
        dt_expected = datetime.datetime(*expected)
        actual = month_delta(dt, months)
        assert actual == dt_expected
