# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Base module for unittests."""
from __future__ import print_function

import pytest

from sparkmeter.misc.jsonutils import json_dumps, json_loads
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.test_data_factory import GroundFactory, OperatorFactory, TransactionFactory
from sparkmeter.web.unittestutils import ContentTester, PageTester


class SparkMeterTestCaseBase(object):

    """Sets up all sparkmeter tests."""

    maxDiff = None
    create_ground = True

    @pytest.fixture(autouse=True)
    def _setup_base(self, session):
        """Generic test setup."""
        self.session = session

        if self.create_ground:
            self.ground = GroundFactory.get_default()
            self.session.flush()
            self.system_sales_account = SalesAccount.get_system()

        yield

    def verify_file_content(self, ext, content, variant=None, ignore_values=None, frame=1):
        """Compare the saved file against the disc."""
        page = ContentTester(frame=frame + 1, ext=ext, variant=variant)
        page.add_ignores(ignore_values)
        page.verify(content)

    def verify_json_content(self, content, variant=None, ignore_values=None, frame=1, ignore_regexes=None):
        """Compare the saved json against the current request's response."""
        json_content = json_dumps(json_loads(content),
                                  sort_keys=True,
                                  indent=4,
                                  separators=(',', ': '))
        page = ContentTester(frame=frame + 1, ext='json', variant=variant)
        page.add_ignores(ignore_values)
        page.add_regex_ignores(ignore_regexes)
        page.verify(json_content)

    def verify_response(self, response, variant=None, ignore_values=None, frame=1):
        page = PageTester(frame=frame + 1, ext='page', variant=variant)
        page.add_ignores(ignore_values)
        page.verify_response(response)

    def create_transaction(self, **kwargs):
        """
        Create a new transaction.
        :param kwargs: factory boy transaction parameters, like from_wallet__value.
        :return: the newly created transaction
        :rtype: sparkmeter.transaction.transactiondomain.Transaction
        """
        t = TransactionFactory(**kwargs)
        self.session.flush()
        if t.from_wallet.sales_account not in t.user.accounts:
            t.user.accounts.append(t.from_wallet.sales_account)
        return t


class WebViewTestCaseBase(SparkMeterTestCaseBase):

    """Test case base for the web views."""

    @pytest.fixture(autouse=True)
    def _setup_web(self, client, operator_role):
        """Setup the view tests."""
        self.user = OperatorFactory(roles=[operator_role])
        if self.create_ground:
            self.user.grounds.append(self.ground)
        self.session.commit()

        # login as operator
        client.login_as(self.user)
        yield
        client.logout()
