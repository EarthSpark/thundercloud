# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import http.client
from builtins import str
from unittest import mock

import pytest
from freezegun import freeze_time

from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import (
    GlobalSalesAccountFactory,
    GroundFactory,
    OperatorFactory,
    SalesAccountFactory,
    UserFactory,
    VendorFactory,
)
from sparkmeter.user.userdomain import Role, User


@pytest.fixture(scope="module", autouse=True)
def _setup(app):
    with mock.patch.dict(app.config, dict(HEROKU=False)):
        yield


class UserViewTest(WebViewTestCaseBase):
    def test_list(self, client):
        path = "/user/"

        response = client.get(path)
        self.verify_response(response)

        # Test vendor redirect
        with mock.patch("sparkmeter.user.userview.get_current_user") as current_user:
            current_user().is_vendor.return_value = True
            current_user().username = "username"
            response = client.get(path)
        self.verify_response(response, variant="vendor")

    def test_bad_username(self, client, vendor_role):
        path = "/user/"

        VendorFactory(
            username="<script>alert('test');</script>",
            roles=[vendor_role],
        )
        self.session.commit()

        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2013-01-01T01:01:01")
    def test_view(self, client, vendor_role):
        path = "/user/%s/"

        response = client.get(path % (self.user.username))

        # test the normal user page
        self.verify_response(response)

        # run tests as a vendor
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)

        # make sure the vendor can't view other users pages
        response = client.get(path % (self.user.username))
        self.verify_response(response, variant="unauthorized")

        # make sure the vendor can view his own page
        response = client.get(path % (vendor.username))
        self.verify_response(response, variant="vendor")

    @freeze_time("2013-01-01T01:01:01")
    def test_view_unknown_user(self, client):
        path = "/user/%s/"
        response = client.get(path % ("bad-user"))
        self.verify_response(response)

    @freeze_time("2013-01-01T01:01:01")
    def test_view_api(self, client):
        account = SalesAccountFactory(credit_wallet__value=1000)
        self.user = UserFactory(roles=[Role.get_by_name("api")], api_sales_account=account)
        self.session.commit()

        path = "/user/%s/"
        response = client.get(path % (self.user.username))
        self.verify_response(response)

    def test_user_add_api(self, client):
        account = SalesAccountFactory(global_account=True)
        self.session.commit()

        # Empty form
        path = "/user/add/api"

        response = client.get(path)
        self.verify_response(response, variant="empty", ignore_values=[str(self.system_sales_account.id)])

        # With permission to place a transaction
        data = {
            "username": "api",
            "api_sales_account": account.id,
            "transaction_permission": "y",
            "save_button": "Save",
        }
        response = client.post(path, data=data)
        self.verify_response(response)

        user = self.session.query(User).filter_by(username="api").one()
        assert user.api_sales_account.name == account.name
        assert user.api_sales_account.id == account.id
        assert user.password

        # Without permission to place a transaction
        data = {"username": "api-2", "save_button": "Save"}
        response = client.post(path, data=data)
        self.verify_response(response, variant="no-transaction-permission")

        user = self.session.query(User).filter_by(username="api-2").one()
        assert user.accounts == []
        assert user.password

    def test_add_operator(self, client):
        path = "/user/add/operator"

        # Empty form
        data = {"save_button": "Save"}
        response = client.post(path, data=data)
        self.verify_response(response, variant="empty", ignore_values=[str(self.system_sales_account.id)])

        data = {
            "email": "foo@bar.com",
            "password": "foobar",
            "confirm": "foobar",
            "username": "username",
            "save_button": "Save",
        }
        response = client.post(path, data=data)
        self.verify_response(response)

        user = self.session.query(User).filter_by(username="username").one()
        assert user.accounts == []

    def test_add_vendor(self, client):
        path = "/user/add/vendor"

        # Empty form
        data = {"save_button": "Save"}
        response = client.post(
            path,
            data=data,
        )
        self.verify_response(response, variant="empty", ignore_values=[str(self.system_sales_account.id)])

        data = {
            "email": "foo@bar.com",
            "password": "foobar",
            "confirm": "foobar",
            "username": "username",
            "save_button": "Save",
        }
        response = client.post(path, data=data)
        self.verify_response(response)

        user = self.session.query(User).filter_by(username="username").one()
        assert user.accounts == []

    def test_add_errors(self, client):
        # Wrong role
        response = client.post("/user/add/bad-role-name")
        self.verify_response(response)

    def test_add_missing_email(self, client):
        path = "/user/add/operator"
        data = {"save_button": "Save"}
        response = client.post(path, data=data)
        self.verify_response(response, variant="empty", ignore_values=[str(self.system_sales_account.id)])
        assert "You must enter an email." in response.text

    def test_add_account_all_access(self, client):
        account1 = SalesAccountFactory()
        account2 = SalesAccountFactory()
        self.session.commit()

        path = "/user/add/operator"

        # Empty form
        data = {"save_button": "Save"}
        response = client.post(path, data=data)
        self.verify_response(response, variant="empty", ignore_values=[str(self.system_sales_account.id)])

        data = {
            "email": "foo@bar.com",
            "account_all_access": "1",
            "password": "foobar",
            "confirm": "foobar",
            "username": "username",
            "save_button": "Save",
        }
        response = client.post(path, data=data)
        self.verify_response(response)

        user = self.session.query(User).filter_by(username="username").one()
        assert data["password"] != user.password  # Verify password has been encrypted
        assert [a.id for a in user.accounts] == [self.system_sales_account.id, account1.id, account2.id]

    def test_add_cloud_forbidden(self, client, config, vendor_role):
        path = "/user/add/operator"

        config["HEROKU"] = True
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()

        data = {
            "email": "foo@bar.com",
            "account_all_access": "1",
            "password": "foobar",
            "confirm": "foobar",
            "username": "username",
            "save_button": "Save",
        }
        client.login_as(vendor)
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)

    def test_add_ground_forbidden(self, client, config, vendor_role):
        path = "/user/add/operator"

        config["HEROKU"] = False
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()

        data = {
            "email": "foo@bar.com",
            "account_all_access": "1",
            "password": "foobar",
            "confirm": "foobar",
            "username": "username",
            "save_button": "Save",
        }
        client.login_as(vendor)
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)

    def test_add_ground_all_access(self, client):
        ground2 = GroundFactory(name="ground 2")
        self.session.commit()

        path = "/user/add/operator"

        # Empty form
        data = {"save_button": "Save"}
        response = client.post(path, data=data)
        self.verify_response(response, variant="empty", ignore_values=[str(self.system_sales_account.id)])

        data = {
            "email": "foo@bar.com",
            "ground_all_access": "1",
            "password": "foobar",
            "confirm": "foobar",
            "username": "username",
            "save_button": "Save",
        }
        response = client.post(path, data=data)
        self.verify_response(response)

        user = self.session.query(User).filter_by(username="username").one()
        assert data["password"] != user.password  # Verify password has been encrypted
        assert sorted([a.id for a in user.grounds]) == sorted([self.ground.id, ground2.id])

    def test_add_duplicate_email(self, client):
        path = "/user/add/operator"
        data = {"email": self.user.email}
        response = client.post(path, data=data)
        self.verify_response(response, ignore_values=[str(self.system_sales_account.id)])
        assert "This email is already used, please enter another." in response.text

    def test_add_duplicate_username(self, client):
        path = "/user/add/operator"
        data = {"username": self.user.username}
        response = client.post(path, data=data)
        self.verify_response(response, ignore_values=[str(self.system_sales_account.id)])
        assert "This username is already used, please enter another." in response.text

    def test_add_missing_username(self, client):
        path = "/user/add/operator"
        data = {"username": ""}
        response = client.post(path, data=data)
        self.verify_response(response, ignore_values=[str(self.system_sales_account.id)])
        assert "You must enter a username." in response.text

    def test_add_missing_passwords(self, client):
        path = "/user/add/operator"
        data = {"username": "username", "save_button": "Save"}
        response = client.post(path, data=data)
        self.verify_response(response, ignore_values=[str(self.system_sales_account.id)])
        assert "Password(s) cannot be empty." in response.text

    def test_add_mismatching_passwords(self, client):
        path = "/user/add/operator"
        data = {"username": "username", "password": "foobar", "confirm": "", "save_button": "Save"}
        response = client.post(path, data=data)
        self.verify_response(response, ignore_values=[str(self.system_sales_account.id)])
        assert "Passwords must match." in response.text

    def test_edit(self, client, vendor_role):
        path = "/user/%s/edit"
        assert self.user

        response = client.get(path % (self.user.username))
        self.verify_response(response, ignore_values=[str(self.system_sales_account.id)])

        response = client.get(path % (self.user.username), follow_redirects=True)
        self.verify_response(
            response, variant="redirected", ignore_values=[str(self.system_sales_account.id)]
        )

        data = {"email": "foo@example.com", "username": self.user.username, "save_button": "Save"}
        response = client.post(path % (self.user.username), data=data)
        self.verify_response(response, variant="post")

        # run tests as a vendor
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)

        # make sure the vendor can't view other users edit pages
        response = client.get(path % (self.user.username), follow_redirects=True)
        self.verify_response(response, variant="vendor")

        # run tests as a operator, viewing vendor
        client.login_as(self.user)
        response = client.get(path % (vendor.username))
        self.verify_response(response, variant="operator", ignore_values=[str(self.system_sales_account.id)])

    def test_edit_unknown_user(self, client):
        path = "/user/%s/edit"
        response = client.get(path % ("bad-user"))
        self.verify_response(response)

    def test_update_locale(self, client):
        assert self.user.locale == "en_US"

        path = "/user/%s/fr_FR"
        response = client.get(path % (self.user.username))
        self.verify_response(response)

        self.user.reload(self.session)
        assert self.user.locale == "fr_FR"

        response = client.get(path % ("not-current"))
        self.verify_response(response, variant="unauthorized")

        response = client.get("/user/%s/no-such-a-locale" % (self.user.username,))
        self.verify_response(response, variant="not-found")

    def test_update_locale_honors_same_host_referer(self, client):
        path = "/user/%s/fr_FR" % self.user.username
        response = client.get(path, headers={"Referer": "http://localhost/meter/SM15R/"})
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/meter/SM15R/")

    def test_update_locale_rejects_external_referer(self, client):
        path = "/user/%s/en_US" % self.user.username
        response = client.get(path, headers={"Referer": "http://evil.example.com/phish"})
        assert response.status_code == 302
        assert "evil.example.com" not in response.headers["Location"]

    def test_reset_credentials(self, client):
        assert self.user

        path = "/user/%s/reset-credentials.json"
        response = client.post(path % (self.user.username))
        self.verify_response(response)

    def test_reset_credentials_unknown_user(self, client):
        assert self.user

        path = "/user/%s/reset-credentials.json"
        response = client.post(path % ("bad-user"))
        self.verify_response(response)

    def test_reset_credentials_forbidden_for_vendor(self, client, vendor_role):
        """A vendor must not be able to reset another user's credentials."""
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)

        path = "/user/%s/reset-credentials.json"
        response = client.post(path % (self.user.username))
        assert response.status_code == http.client.FORBIDDEN

    def test_user_json_operator(self, client, operator_role):
        UserFactory(username="operator-without-accounts", roles=[operator_role])
        UserFactory(
            username="operator-with-accounts",
            roles=[operator_role],
            accounts=[SalesAccountFactory(), SalesAccountFactory()],
        )
        self.session.commit()
        path = "/users.json?role=operator"
        response = client.get(path)
        self.verify_response(response)

    def test_user_json_vendor(self, client, vendor_role):
        UserFactory(username="vendor-without-accounts", roles=[vendor_role])
        UserFactory(
            username="vendor-with-accounts",
            roles=[vendor_role],
            accounts=[SalesAccountFactory(), SalesAccountFactory()],
        )
        self.session.commit()
        path = "/users.json?role=vendor"
        response = client.get(path)
        self.verify_response(response)

    def test_user_json_api(self, client, api_role):
        UserFactory(
            username="api-with-account", roles=[api_role], api_sales_account=GlobalSalesAccountFactory()
        )
        UserFactory(username="api-without-account", roles=[api_role])
        self.session.commit()
        path = "/users.json?role=api"
        response = client.get(path)
        self.verify_response(response)

    def test_user_json_bad_role(self, client):
        path = "/users.json?role=invalid"
        response = client.get(path)
        self.verify_response(response)

    def test_sales_accounts_global(self, client):
        account = GlobalSalesAccountFactory(name="Global")
        self.user.accounts.append(account)
        self.session.commit()

        path = "/user/{user.username}/sales-account/global.json"
        response = client.get(path.format(user=self.user))
        self.verify_response(response)

    def test_sales_accounts_restricted(self, client):
        account = SalesAccountFactory(name="Restricted", ground=self.ground)
        self.user.accounts.append(account)
        self.session.commit()

        path = "/user/{user.username}/sales-account/restricted.json"
        response = client.get(path.format(user=self.user))
        self.verify_response(response)

    def test_user_sales_accounts_bad_account_type(self, client):
        path = "/user/{user.username}/sales-account/bad-account-type.json"
        response = client.get(path.format(user=self.user))
        self.verify_response(response)

    def test_user_sales_accounts_invalid_user(self, client):
        path = "/user/{username}/sales-account/restricted.json"
        response = client.get(path.format(username="invalid-user"))
        self.verify_response(response)

    def test_sales_accounts_vendor_forbidden(self, client, vendor_role):
        """A vendor must not read another user's sales accounts."""
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)

        path = "/user/%s/sales-account/global.json" % (self.user.username,)
        response = client.get(path)
        assert response.status_code == http.client.UNAUTHORIZED

    def test_sales_accounts_vendor_own_allowed(self, client, vendor_role):
        """A vendor may read their own sales accounts (guard fires only for others)."""
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)

        path = "/user/%s/sales-account/global.json" % (vendor.username,)
        response = client.get(path)
        assert response.status_code == http.client.OK

    def test_sales_accounts_operator_cross_user_allowed(self, client, vendor_role):
        """An operator may read another user's sales accounts (guard fires only for vendors)."""
        other = VendorFactory(roles=[vendor_role])
        self.session.commit()
        # the default logged-in user (self.user) is an operator

        path = "/user/%s/sales-account/global.json" % (other.username,)
        response = client.get(path)
        assert response.status_code == http.client.OK

    def test_my_sales_accounts_bad_account_type(self, client):
        path = "/user/sales-account/bad-account-type.json"
        response = client.get(path.format(user=self.user))
        self.verify_response(response)

    def test_cloud_grounds(self, client, config, operator_role, vendor_role):
        other = GroundFactory()
        self.session.commit()
        users = [
            OperatorFactory(roles=[operator_role], username="operator-none", grounds=[]),
            OperatorFactory(roles=[operator_role], username="operator-only-1", grounds=[self.ground]),
            OperatorFactory(roles=[operator_role], username="operator-only-2", grounds=[other]),
            OperatorFactory(roles=[operator_role], username="operator-all", grounds=[self.ground, other]),
            VendorFactory(roles=[vendor_role], username="vendor-none", grounds=[]),
            VendorFactory(roles=[vendor_role], username="vendor-only-1", grounds=[self.ground]),
            VendorFactory(roles=[vendor_role], username="vendor-only-2", grounds=[other]),
            VendorFactory(roles=[vendor_role], username="vendor-all", grounds=[self.ground, other]),
        ]
        self.session.commit()

        for user in users:
            config["HEROKU"] = False
            client.login_as(user)
            path = "/user/grounds.json"
            response = client.get(path)
            self.verify_response(response, variant=user.username)

    def test_token(self, client):
        path = "/user/token.json"
        response = client.get(path)
        self.verify_response(response, ignore_values=[self.user.get_auth_token()])
