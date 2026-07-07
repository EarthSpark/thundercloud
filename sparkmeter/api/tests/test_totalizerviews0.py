# -*- coding: utf-8 -*-
# Copyright © 2019 SparkMeter, Inc.
# All Rights Reserved.
import urllib.parse

from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.meter.meterstate import MeterState
from sparkmeter.tests.test_data_factory import MeterFactory, TotalizerMeterFactory


class TotalizerListTest(APIView0TestCaseBase):

    path = "v0/totalizers"

    def _query(self, **kwargs):
        return self.get(self.path + '?' + urllib.parse.urlencode(kwargs))

    def test_list_all(self):
        MeterFactory(customer__name='Customer #1')
        TotalizerMeterFactory()
        TotalizerMeterFactory()
        self.session.commit()
        response = self.get(self.path)
        self.verify_response(response)

    def test_error_unknown_parameter(self):
        response = self.get(self.path + '?unknown-parameter')
        self.verify_response(response)

    def test_meter_serial(self):
        MeterFactory()
        TotalizerMeterFactory()
        totalizer = TotalizerMeterFactory()
        self.session.commit()
        response = self._query(meter_serial=totalizer.serial.lower())
        self.verify_response(response)

    def test_error_no_such_meter(self):
        response = self._query(meter_serial='no-such-meter')
        self.verify_response(response)

    def test_error_no_such_totalizer(self):
        meter = MeterFactory(customer__name='Customer #1')
        TotalizerMeterFactory()
        TotalizerMeterFactory()
        self.session.commit()
        response = self._query(meter_serial=meter.serial.lower())
        self.verify_response(response)

    def test_empty_totalizers(self):
        response = self._query()
        self.verify_response(response)

    def test_meter_state_values(self):
        TotalizerMeterFactory(system_info__current_state=MeterState.STATE_THROTTLE_ERROR.id)
        self.session.commit()
        response = self.get(self.path)
        self.verify_response(response)
