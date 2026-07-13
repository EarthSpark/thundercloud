# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
import uuid
from builtins import str

from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import SalesAccountFactory, UserFactory, VendorFactory
from sparkmeter.user.userdomain import user_datastore


class UserTest(SparkMeterTestCaseBase):
    def test_generate_password(self, vendor_role):
        user = VendorFactory(roles=[vendor_role], password=None)
        assert not user.password
        user.generate_password()
        assert len(user.password) == 60

    def test_unicode(self):
        user = VendorFactory()
        assert str(user) == "testüser-001"

    def test_transaction_permission(self, api_role):
        account = SalesAccountFactory()
        api = UserFactory(roles=[api_role])

        assert not api.transaction_permission
        api.api_sales_account = account
        assert api.transaction_permission
        api.transaction_permission = False
        assert not api.api_sales_account

    def test_api_sales_account(self, api_role):
        account1 = SalesAccountFactory()
        account2 = SalesAccountFactory()
        api = UserFactory(roles=[api_role])

        # None
        assert api.api_sales_account is None

        # None -> account 1
        api.api_sales_account = account1
        assert api.api_sales_account == account1

        # accounts 1 -> account 2
        api.api_sales_account = account2
        assert api.api_sales_account == account2

        # account 2 -> None
        api.api_sales_account = None
        assert api.api_sales_account is None


class DatastoreTest(SparkMeterTestCaseBase):
    def test_find_existing_user(self):
        acct = UserFactory()
        self.session.commit()
        user = user_datastore.find_user(id=str(acct.id))
        assert user == acct

    def test_find_missing_user(self):
        acct = UserFactory()
        user = user_datastore.find_user(id=str(acct.id))
        assert user is None

    def test_find_existing_portal_id(self):
        acct = UserFactory(portal_id=uuid.uuid4())
        self.session.commit()
        user = user_datastore.find_user(id="$" + str(acct.portal_id))
        assert user == acct

    def test_find_missing_portal_id(self):
        acct = UserFactory(portal_id=None)
        user = user_datastore.find_user(id="$" + str(acct.id))
        assert user is None
