# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.config.configdomain import ConfigParameter
from sparkmeter.config.configparameter import ParameterObject


class TestConfigParameterList(APIView0TestCaseBase):
    path = "v0/config/"

    def test_get(self):
        ignore_values = []
        for param in ConfigParameter.query.all():
            ignore_values.append(param.last_modified.isoformat())
        response = self.get(self.path)
        self.verify_response(response, ignore_values=ignore_values)


class TestConfigParameterSet(APIView0TestCaseBase):
    path = "v0/config/{}"

    def test_put_form(self):
        param_name = ParameterObject.ALLOW_NEGATIVE_BALANCE.name
        path = self.path.format(param_name)
        param = ConfigParameter.get_by_name(param_name)
        assert param.value is True
        prev_modified = param.last_modified

        response = self.put(path, data={"value": False})
        self.verify_response(response)

        self.session.expire_all()
        param = ConfigParameter.get_by_name(param_name)

        assert param.value is False
        # FIXME: freeze_time breaks itsdangerous, so only check
        #        it's newer/updated
        assert param.last_modified > prev_modified
        assert param.updated_by is not None

    def test_put_json(self):
        param_name = ParameterObject.ALLOW_NEGATIVE_BALANCE.name
        path = self.path.format(param_name)
        param = ConfigParameter.get_by_name(param_name)
        assert param.value is True
        prev_modified = param.last_modified

        response = self.put(path, json={"value": False})
        self.verify_response(response)

        self.session.expire_all()
        param = ConfigParameter.get_by_name(param_name)

        assert param.value is False
        # FIXME: freeze_time breaks itsdangerous, so only check
        #        it's newer/updated
        assert param.last_modified > prev_modified
        assert param.updated_by is not None

    def test_no_such_parameter(self):
        path = self.path.format("does-not-exist")
        response = self.put(path, json={"value": True})
        self.verify_response(response)

    def test_invalid_type(self):
        path = self.path.format(ParameterObject.ALLOW_NEGATIVE_BALANCE.name)
        response = self.put(path, json={"value": "xxx"})
        self.verify_response(response)
