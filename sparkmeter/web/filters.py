# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Flask/Jinja filters."""

from sparkmeter.misc.datetimeutils import format_datetime
from sparkmeter.misc.phoneutils import format_phone_number, parse_phone_number


def format_datetime_filter(dt, fmt="YYYY-MM-dd HH:mm:ss zzzz"):
    """A filter that will format a datetime.

    This will filter/convert a datetime object according to UTC and also make it
    suitable for showing in HTML/JS.

    Note: set fmt=None to get a localized datetime.
    EX: {{ meter.created|format_datetime(fmt=None) }}
    """
    if dt is None:
        return ""

    return format_datetime(dt, fmt)


def format_phone_number_filter(value):
    """A filter that will format a phone number."""
    if value is not None:
        try:
            number = parse_phone_number(value)
            value = format_phone_number(number)
        except ValueError:
            value = ""
    else:
        value = ""
    return value


def register_filters(app):
    """Register filters in the current application."""
    app.template_filter("format_datetime")(format_datetime_filter)
    app.template_filter("format_phone_number")(format_phone_number_filter)
