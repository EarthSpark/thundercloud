# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import datetime
from unittest import mock

from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.web.filters import format_datetime_filter, format_phone_number_filter


class FiltersTest(SparkMeterTestCaseBase):

    @mock.patch('sparkmeter.misc.datetimeutils.get_current_user')
    def test_format_datetime(self, mock_current_user):

        # test english formatting
        mock_current_user().locale = 'en_US'

        dt = datetime.datetime(2015, 5, 28, 8, 12, 46, 286176)
        result = format_datetime_filter(dt)
        assert result == '2015-05-28 08:12:46 Coordinated Universal Time'

        dt = datetime.datetime(2015, 5, 28, 14, 12, 46, 286176)
        result = format_datetime_filter(dt)
        assert result == '2015-05-28 14:12:46 Coordinated Universal Time'

        # test french formatting
        mock_current_user().locale = 'fr_FR'

        dt = datetime.datetime(2015, 5, 28, 8, 12, 46, 286176)
        result = format_datetime_filter(dt)
        assert result == '2015-05-28 08:12:46 temps universel coordonné'

        dt = datetime.datetime(2015, 5, 28, 14, 12, 46, 286176)
        result = format_datetime_filter(dt)
        assert result == '2015-05-28 14:12:46 temps universel coordonné'

        assert '' == format_datetime_filter(None)

    def test_format_phone_number(self):
        v = format_phone_number_filter(None)
        assert v == ""

        v = format_phone_number_filter("busted")
        assert v == ""

        v = format_phone_number_filter("+5516991234567")
        assert v == "+55 16 99123-4567"
