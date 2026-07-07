# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import pytest
from flask.testing import FlaskClient  # noqa
from flask.wrappers import Response  # noqa

from sparkmeter.api.apiviews0 import assert_one_of_params, check_param
from sparkmeter.exceptions import APIError
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import GroundFactory, SalesAccountFactory, UserFactory
from sparkmeter.user.userdomain import Role


class APIView0TestCaseBase(SparkMeterTestCaseBase):

    headers = {}

    @pytest.fixture(autouse=True)
    def _setup_api(self, _setup_base, client):
        self.client = client
        self.ground = GroundFactory.get_default()  # type: Ground
        self.session.flush()
        self.account = SalesAccountFactory(credit_wallet__value=1000)  # type: SalesAccount
        self.user = UserFactory(roles=[Role.get_by_name('api')],
                                api_sales_account=self.account)  # type: UserFactory
        self.session.flush()
        yield

    def _add_auth_token(self, kwargs):
        headers = kwargs.get('headers', self.headers.copy())
        headers['Authentication-Token'] = self.user.get_auth_token()
        kwargs['headers'] = headers

    def get(self, path, **kwargs):
        """
        Does a GET request
        :param path:  path
        :param kwargs: arguments passed on to Client.get()
        :return: the response
        :rtype: Response
        """
        self._add_auth_token(kwargs)
        return self.client.get('/api/' + path, **kwargs)

    def post(self, path, **kwargs):
        """
        Does a POST request
        :param path:  path
        :param kwargs: arguments passed on to Client.post()
        :return: the response
        :rtype: Response
        """
        self._add_auth_token(kwargs)
        return self.client.post('/api/' + path, **kwargs)

    def put(self, path, **kwargs):
        """
        Does a PUT request
        :param path:  path
        :param kwargs: arguments passed on to Client.put()
        :return: the response
        :rtype: Response
        """
        self._add_auth_token(kwargs)
        return self.client.put('/api/' + path, **kwargs)

    def patch(self, path, **kwargs):
        """
        Does a PATCH request
        :param path:  path
        :param kwargs: arguments passed on to Client.patch()
        :return: the response
        :rtype: Response
        """
        self._add_auth_token(kwargs)
        return self.client.patch('/api/' + path, **kwargs)


class BlueprintTest(APIView0TestCaseBase):

    def test_unauthorized(self):
        path = "/api/v0/system-info"
        response = self.client.get(path)
        self.verify_response(response)

    def test_not_found(self):
        path = "/api/v0/does-not-exist"
        response = self.client.get(path)
        self.verify_response(response)

    def test_bad_mimetype(self):
        path = "v0/transaction/"
        response = self.post(path, headers={'Content-Type': 'text/plain'})
        self.verify_response(response)


class CheckParamsTest(object):

    def test_check_default(self):
        value = check_param({}, 'default-var', default='default')
        assert value == 'default'

    def test_check_type(self):
        value = check_param({'value': '1'}, 'value', int)
        assert value == 1

    def test_check_param_missing(self):
        with pytest.raises(APIError) as ctx:
            check_param({}, 'missing')
        expected = {
            'error': 'missing parameter: missing',
            'status': 'failure',
        }
        assert ctx.value.to_dict() == expected

    def test_check_param_empty(self):
        with pytest.raises(APIError) as ctx:
            check_param({'empty': ''}, 'empty')
        expected = {
            'error': 'bad parameter: empty, cannot be empty',
            'status': 'failure',
        }
        assert ctx.value.to_dict() == expected

    def test_check_param_empty_allowed(self):
        value = check_param({'empty': ''}, 'empty', allow_empty=True)
        assert value == ''

    def test_check_param_wrong_type(self):
        with pytest.raises(APIError) as ctx:
            check_param({'str': 'foo'}, 'str', int, 'int')
        expected = {
            'error': 'bad parameter: str, must be a int',
            'status': 'failure',
        }
        assert ctx.value.to_dict() == expected
        with pytest.raises(APIError) as ctx:
            check_param({'str': 'foo'}, 'str', list, 'int')
        expected = {
            'error': 'bad parameter: str, must be a list',
            'status': 'failure',
        }
        assert ctx.value.to_dict() == expected


class AssertOneOfParamsTest(object):

    def test_ok(self):
        assert_one_of_params(['param1'], ['param1', 'param2'])

    def test_none_supplied(self):
        with pytest.raises(APIError) as ctx:
            assert_one_of_params(None, ['param1', 'param2'])
        assert ctx.value.to_dict() == {
            'error': 'no valid parameters found, expected one or many from: param1, param2',
            'status': 'failure'
        }

    def test_empty_supplied(self):
        with pytest.raises(APIError) as ctx:
            assert_one_of_params([], ['param1', 'param2'])
        assert ctx.value.to_dict() == {
            'error': 'no valid parameters found, expected one or many from: param1, param2',
            'status': 'failure'
        }
