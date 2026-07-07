# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.

import datetime
from unittest import mock

from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase


class SystemInfoTest(APIView0TestCaseBase):

    path = "v0/system-info"

    def test_get(self):
        response = self.get(self.path)
        self.verify_response(response)

    def test_get_with_sync_date(self):
        p = 'sparkmeter.ground.grounddomain.Ground.get_last_sync_date'
        with mock.patch(p) as f:
            f.return_value = datetime.datetime(2013, 1, 1, 1, 1, 1)
            response = self.get(self.path)
        self.verify_response(response)
