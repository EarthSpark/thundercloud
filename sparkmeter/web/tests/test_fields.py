# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.

from unittest import mock

from sparkmeter.web.fields import HiddenIdField


def test_process_formdata():
    field = HiddenIdField()
    field = field.bind(mock.Mock(), 'field')
    field.process_formdata(["data"])
    assert field.data == "data"
    field.process_formdata([""])
    assert field.data == '1'  # Default Country Code
