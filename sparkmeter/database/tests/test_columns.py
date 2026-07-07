# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.

from sparkmeter.database.columns import IntBoolean
from sparkmeter.tests.base import SparkMeterTestCaseBase


class ColumnTest(SparkMeterTestCaseBase):

    def test_int_boolean(self):
        col = IntBoolean()
        assert col.get_col_spec() == 'SMALLINT'
        func = col.literal_processor('postgres')
        assert func(True) == '1'
        assert func(False) == '0'
        func = col.result_processor('postgres', 'SMALLINT')
        assert func(-1) is None
        assert func(0) is False
        assert func(1) is True
