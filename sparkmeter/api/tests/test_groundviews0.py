from unittest import mock

from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.ground.grounddomain import GroundPrivate


class GroundOverideMeterStateTest(APIView0TestCaseBase):
    path = "v0/ground/groundserial1/set-override-meter-state"

    def test_post_form(self):
        with mock.patch.object(GroundPrivate, "queue_override_meter_state") as queue_state:
            response = self.post(self.path, data={"state": "true"})
            queue_state.assert_called_once_with(True)
        self.verify_response(response)

    def test_post_json(self):
        with mock.patch.object(GroundPrivate, "queue_override_meter_state") as queue_state:
            response = self.post(self.path, json={"state": "true"})
            queue_state.assert_called_once_with(True)
        self.verify_response(response)

    def test_state_missing_parameter(self):
        response = self.post(self.path, data="")
        self.verify_response(response)
        assert self.ground.private.override_meter_state is False
        assert self.ground.private.override_meter_state_modified is None

    def test_state_cannot_be_empty(self):
        response = self.post(self.path, data="state=")
        self.verify_response(response)
        assert self.ground.private.override_meter_state is False
        assert self.ground.private.override_meter_state_modified is None

    def test_state_bad_value(self):
        response = self.post(self.path, data="state=bad-value")
        self.verify_response(response)
        assert self.ground.private.override_meter_state is False
        assert self.ground.private.override_meter_state_modified is None

    def test_no_such_ground(self):
        path = "v0/ground/invalid-ground-serial/set-override-meter-state"
        response = self.post(path, data="state=true")
        self.verify_response(response)
        assert self.ground.private.override_meter_state is False
        assert self.ground.private.override_meter_state_modified is None
