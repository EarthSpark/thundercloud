# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Event keywords."""

from builtins import object

from babel.dates import format_datetime
from babel.numbers import format_currency, format_decimal
from flask_babel import lazy_gettext as _

from sparkmeter.config.configdict import config


class EventKeyword(object):

    """Event Keyword.

    An event keyword is a variable that get replaced by a value when
    a message is rendered, for instance when sending an sms.
    """

    def __init__(self, name, description, example):
        self.name = name
        self.description = description
        self.example = example

    def format(self, value, locale):
        """Format a value for display according to a locale."""
        return value


class StringKeyword(EventKeyword):

    """A String Keyword."""


class CurrencyKeyword(EventKeyword):

    """A Currency Keyword."""

    def format(self, value, locale):
        """Format a curreny value for display according to a locale."""
        currency = config.get('CURRENCY', 'USD')
        return format_currency(value, currency, format="#,##0.00", locale=locale)


class BooleanKeyword(EventKeyword):

    """A Boolean Keyword."""

    def format(self, value, locale):
        """Format a boolean value for display according to a locale."""
        if value:
            return _('yes')
        else:
            return _('no')


class EnergyKeyword(EventKeyword):

    """An Energy Keyword."""

    def format(self, value, locale):
        """Format an energy value for display according to a locale."""
        return format_decimal(value, '#,##0.### kWh', locale=locale)


class DateTimeKeyword(EventKeyword):

    """A DateTime Keyword."""

    def format(self, value, locale):
        """Format a datetime value for display according to a locale."""
        return format_datetime(value, "short", locale=locale)
