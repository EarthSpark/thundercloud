# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import pytest
from werkzeug.exceptions import NotFound

from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.web.permission import verify_permission


@pytest.fixture()
def current_user(mocker):
    from unittest.mock import MagicMock
    mock_user = MagicMock()
    mocker.patch('sparkmeter.web.permission.current_user', mock_user)
    yield mock_user


class PermissionTest(SparkMeterTestCaseBase):
    def _test_tariff_edit(self, config, current_user, perm):
        @verify_permission('tariff', perm)
        def function():
            return True

        current_user.has_role.return_value = False
        config.clear()
        with pytest.raises(NotFound):
            function()

        current_user.has_role.return_value = True
        config['HEROKU'] = True
        assert function()

        current_user.has_role.return_value = True
        config['HEROKU'] = False
        assert function()

    def test_tariff_add(self, config, current_user):
        self._test_tariff_edit(config, current_user, perm='add')

    def test_tariff_edit(self, config, current_user):
        self._test_tariff_edit(config, current_user, perm='edit')

    def test_tariff_view(self, current_user):
        @verify_permission('tariff', 'view')
        def function():
            pass

        current_user.has_role.return_value = False
        with pytest.raises(NotFound):
            function()

        current_user.has_role.return_value = True
        function()

    def _test_transaction_source(self, config, current_user, perm):
        @verify_permission('transaction-source', perm)
        def function():
            return True

        current_user.has_role.return_value = False
        config.clear()
        with pytest.raises(NotFound):
            function()

        current_user.has_role.return_value = True
        config['HEROKU'] = True
        assert function()

        current_user.has_role.return_value = True
        config['HEROKU'] = False
        assert function()

    def test_transaction_source_edit(self, config, current_user):
        self._test_transaction_source(config, current_user, perm='edit')

    def test_ground_add(self, config, current_user):
        self._test_transaction_source(config, current_user, perm='add')

    def test_transaction_source_view(self, current_user):
        @verify_permission('transaction-source', 'view')
        def function():
            pass

        current_user.has_role.return_value = False
        with pytest.raises(NotFound):
            function()

        current_user.has_role.return_value = True
        function()
