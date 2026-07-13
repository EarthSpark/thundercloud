# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.

import datetime
import uuid
from builtins import object
from decimal import Decimal

import speaklater

from sparkmeter.database.types import Choice
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.tests.base import WebViewTestCaseBase


class TestJsonEncoder(WebViewTestCaseBase):
    def assertJSON(self, value, expected):
        serialized = json_dumps(value)
        assert serialized == expected

    def test_datetime(self):
        value = datetime.datetime(1970, 1, 1, 12, 30, 45)
        self.assertJSON(value, '"1970-01-01T12:30:45"')

    def test_date(self):
        value = datetime.datetime(1970, 1, 1)
        self.assertJSON(value, '"1970-01-01T00:00:00"')

    def test_time(self):
        value = datetime.time(1, 2, 3)
        self.assertJSON(value, '"01:02:03"')

    def test_lazystring(self):
        value = speaklater.make_lazy_string(lambda: "foo")
        assert speaklater.is_lazy_string(value)
        self.assertJSON(value, '"foo"')

    def test_choice(self):
        value = Choice(code="code", value="value")
        self.assertJSON(value, '"code"')

    def test_uuid(self):
        value = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.assertJSON(value, '"00000000-0000-0000-0000-000000000001"')

    def test_object_json_method(self):
        class ObjectJSON(object):
            def __init__(self, value):
                self.value = value

            def __json__(self):
                return self.value

        value = ObjectJSON("json")
        self.assertJSON(value, '"json"')

    def test_string(self):
        self.assertJSON("string", '"string"')
        self.assertJSON("string", '"string"')

    def test_number(self):
        self.assertJSON(1, "1")
        self.assertJSON(1.5, "1.5")
        self.assertJSON(Decimal(1.3333), "1.3333")

    def test_singletons(self):
        self.assertJSON(True, "true")
        self.assertJSON(False, "false")
        self.assertJSON(None, "null")
