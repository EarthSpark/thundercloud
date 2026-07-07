from unittest import mock

import pytest

from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.meter.meterdomain import Meter, MeterConfig
from sparkmeter.tests.test_data_factory import MeterFactory


class MeterSetOperatingModeTest(APIView0TestCaseBase):

    path = "v0/meter/SM15R-01-00000001/set-operating-mode"

    @pytest.fixture(autouse=True)
    def _setup_meter(self):
        self.meter = MeterFactory(serial='SM15R-01-00000001',
                                  config__state=MeterConfig.STATE_OFF)
        self.session.commit()
        yield

    def test_post_form(self):
        with mock.patch.object(Meter, 'set_state') as set_state:
            response = self.post(self.path, data={'state': 'on'})
            set_state.assert_called_once_with(MeterConfig.STATE_ON)
        self.verify_response(response)

    def test_post_json(self):
        with mock.patch.object(Meter, 'set_state') as set_state:
            response = self.post(
                self.path.lower(), json={'state': 'on'})
            set_state.assert_called_once_with(MeterConfig.STATE_ON)
        self.verify_response(response)

    def test_state_missing_parameter(self):
        response = self.post(self.path, data='')
        self.verify_response(response)
        assert self.meter.config.state == MeterConfig.STATE_OFF

    def test_state_cannot_be_empty(self):
        response = self.post(self.path, data='state=')
        self.verify_response(response)
        assert self.meter.config.state == MeterConfig.STATE_OFF

    def test_state_bad_value(self):
        response = self.post(self.path, data='state=bad-value')
        self.verify_response(response)
        assert self.meter.config.state == MeterConfig.STATE_OFF

    def test_no_such_meter(self):
        path = "v0/meter/invalid-meter-serial/set-operating-mode"
        response = self.post(path, data='state=on')
        self.verify_response(response)
        assert self.meter.config.state == MeterConfig.STATE_OFF

    def test_invalid_meter(self):
        self.meter.meter_type = Meter.TYPE_TOTALIZER
        self.session.commit()
        response = self.post(self.path, data='state=on')
        self.verify_response(response)
        assert self.meter.config.state == MeterConfig.STATE_OFF


class MeterListModelsTest(APIView0TestCaseBase):

    path = "v0/meters/models"

    @pytest.fixture(autouse=True)
    def _setup_meter(self):
        self.meter = MeterFactory(serial='SM15R-01-00000001')
        self.session.commit()
        yield

    def test_get_json(self):
        response = self.get(self.path)
        self.verify_response(response)
        data = response.json()
        meter_counted = False
        for model in data['models']:
            if model['name'] == self.meter.model.name:
                assert model['count'] == 1
                meter_counted = True
                continue
            assert model['count'] == 0
        assert meter_counted
