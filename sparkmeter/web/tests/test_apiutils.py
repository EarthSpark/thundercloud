# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Event views unittest."""

import pytest

from sparkmeter.exceptions import APIError
from sparkmeter.web.apiutils import check_param, get_params


class ApiUtilsTest(object):
    def test_get_params(self, app):
        with app.test_request_context(content_type="application/x-www-form-urlencoded"):
            # Form data returns a MultiDict
            params = get_params()
            assert params is not None

        with app.test_request_context(content_type="application/json", data="{}"):
            params = get_params()
            assert params == {}

    def test_get_params_unsupported_media_type(self, app):
        with app.test_request_context(content_type="text/plain"):
            with pytest.raises(APIError) as ctx:
                get_params()
        expected = {
            "error": "bad mimetype, must be application/x-www-form-urlencoded or application/json",
            "status": "failure",
        }
        assert ctx.value.to_dict() == expected

    def test_check_default(self):
        value = check_param({}, "default-var", default="default")
        assert value == "default"

    def test_check_type(self):
        value = check_param({"value": "1"}, "value", int)
        assert value == 1

    def test_check_param_missing(self):
        with pytest.raises(APIError) as ctx:
            check_param({}, "missing")
        expected = {
            "error": "missing parameter: missing",
            "status": "failure",
        }
        assert ctx.value.to_dict() == expected

    def test_check_param_empty(self):
        with pytest.raises(APIError) as ctx:
            check_param({"empty": ""}, "empty")
        expected = {
            "error": "bad parameter: empty, cannot be empty",
            "status": "failure",
        }
        assert ctx.value.to_dict() == expected

    def test_check_param_wrong_type(self):
        with pytest.raises(APIError) as ctx:
            check_param({"str": "foo"}, "str", int, "int")
        expected = {
            "error": "bad parameter: str, must be a int",
            "status": "failure",
        }
        assert ctx.value.to_dict() == expected
