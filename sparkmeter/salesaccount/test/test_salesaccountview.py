# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import http.client
from builtins import str
from unittest import mock

import pytest

from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import (GlobalSalesAccountFactory, GroundFactory,
                                                OperatorFactory, SalesAccountFactory,
                                                TransactionFactory, UserFactory, VendorFactory)


@pytest.fixture(scope="module", autouse=True)
def _setup(app):
    with mock.patch.dict(app.config, dict(HEROKU=False)):
        yield


class SalesAccountViewTest(WebViewTestCaseBase):

    def test_index(self, client):
        path = "/sales-account/"

        response = client.get(path)
        self.verify_response(response)

    def test_index_as_vendor(self, client, vendor_role):
        path = "/sales-account/"

        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)

        response = client.get(path)
        self.verify_response(response)

    def test_add_restricted(self, client):
        path = "/sales-account/add/restricted"
        data = {'name': 'Restricted Sales Account',
                'markup': '0.38',
                'active': True,
                'ground': self.ground.id,
                'save_button': 'Save'}
        response = client.post(path, data=data)
        self.verify_response(response)

        account = SalesAccount.query.filter_by(name='Restricted Sales Account').one()
        assert account.markup == 0.38
        assert not account.global_account
        assert not account.negative_permitted
        assert account.active

    def test_add_global(self, client):
        path = "/sales-account/add/global"
        data = {'name': 'Global Sales Account',
                'active': True,
                'save_button': 'Save'}
        response = client.post(path, data=data)
        self.verify_response(response)

        account = self.session.query(SalesAccount).filter_by(name='Global Sales Account').one()
        assert account.markup is None
        assert account.global_account
        assert account.negative_permitted
        assert account.active

    def test_add_invalid(self, client):
        path = "/sales-account/add/invalid"
        data = {'name': 'Global Sales Account',
                'active': True,
                'save_button': 'Save'}
        response = client.post(path, data=data)
        self.verify_response(response)

    def test_add_with_user_account_all_access(self, client):
        vendor1 = VendorFactory(account_all_access=False)
        vendor2 = VendorFactory(account_all_access=True)
        self.session.commit()

        path = "/sales-account/add/restricted"
        data = {'name': 'Sales Account #1',
                'markup': '0.38',
                'active': True,
                'ground': self.ground.id,
                'save_button': 'Save'}
        response = client.post(path, data=data)
        self.verify_response(response)

        account = self.session.query(SalesAccount).filter_by(name='Sales Account #1').one()
        assert [a.id for a in vendor1.accounts] == []
        assert (sorted([a.id for a in vendor2.accounts])
                == sorted([account.id, self.system_sales_account.id]))

    def test_add_missing_name(self, client):
        path = "/sales-account/add/restricted"
        data = {'ground': self.ground.id,
                'save_button': 'Save'}
        response = client.post(path, data=data)
        self.verify_response(response,
                             ignore_values=[str(self.system_sales_account.id)])
        assert 'You must enter a name.' in response.text

    def test_add_duplicated_name(self, client):
        path = "/sales-account/add/restricted"
        account = SalesAccountFactory()
        self.session.commit()
        data = {'name': account.name,
                'ground': self.ground.id,
                'save_button': 'Save'}
        response = client.post(path, data=data)
        self.verify_response(response,
                             ignore_values=[str(self.system_sales_account.id)])
        assert 'This name is already used, please enter another.' in response.text

    def test_add_cloud_get_forbidden(self, client, config, vendor_role):
        path = "/sales-account/add/global"

        config['HEROKU'] = True
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()

        client.login_as(vendor)
        response = client.get(path)
        self.verify_response(response)

    def test_add_cloud_post_forbidden(self, client, config, vendor_role):
        path = "/sales-account/add/global"

        config['HEROKU'] = True
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()

        data = {'name': 'Global Sales Account',
                'active': True,
                'save_button': 'Save'}
        client.login_as(vendor)
        response = client.post(path, data=data)
        self.verify_response(response)

    def test_add_ground_get_forbidden(self, client, config, vendor_role):
        path = "/sales-account/add/global"

        config['HEROKU'] = False
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()

        client.login_as(vendor)
        response = client.get(path)
        self.verify_response(response)

    def test_add_ground_post_forbidden(self, client, config, vendor_role):
        path = "/sales-account/add/global"

        config['HEROKU'] = False
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()

        data = {'name': 'Global Sales Account',
                'active': True,
                'save_button': 'Save'}
        client.login_as(vendor)
        response = client.post(path, data=data)
        self.verify_response(response)

    def test_edit_global(self, client):
        path = "/sales-account/%s/edit"
        account = GlobalSalesAccountFactory()
        self.session.commit()

        response = client.get(path % (account.id, ))
        self.verify_response(response,
                             variant='get',
                             ignore_values=[str(self.system_sales_account.id)])

        response = client.get(path % (account.id, ), follow_redirects=True)
        assert response.status_code == http.client.OK

        data = {'name': 'Global Sales Account #1',
                'active': True,
                'save_button': 'Save'}
        response = client.post(path % (account.id, ), data=data)
        self.verify_response(response, variant='post')

        account = self.session.query(SalesAccount).filter_by(
            name='Global Sales Account #1').one()
        assert account.active

    def test_edit_restricted(self, client):
        path = "/sales-account/%s/edit"
        account = SalesAccountFactory()
        self.session.commit()

        response = client.get(path % (account.id, ))
        self.verify_response(response, ignore_values=[str(self.system_sales_account.id)])

        response = client.get(path % (account.id, ), follow_redirects=True)
        assert response.status_code == http.client.OK

        data = {'name': 'Sales Account #1',
                'markup': '0.38',
                'active': True,
                'save_button': 'Save'}
        response = client.post(path % (account.id, ), data=data)
        account = self.session.query(SalesAccount).filter_by(name='Sales Account #1').one()
        self.verify_response(response, ignore_values=[str(self.system_sales_account.id)],
                             variant='post')
        assert account.markup == 0.38
        assert account.active

    def test_edit_not_found(self, client):
        path = "/sales-account/00000000-0000-0000-0000-000000000000/edit"
        response = client.get(path)
        assert response.status_code == http.client.NOT_FOUND

    def test_edit_system(self, client):
        account = GlobalSalesAccountFactory(system=True)
        self.session.commit()
        path = "/sales-account/%s/edit"
        response = client.post(path % (account.id,))
        self.verify_response(response)

    def test_view_restricted(self, client):
        path = "/sales-account/%s/"
        account = SalesAccountFactory()
        self.user.accounts = [account, self.system_sales_account]
        self.session.commit()

        response = client.get(path % account.id)
        self.verify_response(
            response, ignore_values=[str(self.system_sales_account.id)])

    def test_view_global(self, client):
        path = "/sales-account/%s/"
        account = GlobalSalesAccountFactory()
        self.user.accounts = [account, self.system_sales_account]
        self.session.commit()

        response = client.get(path % account.id)
        self.verify_response(
            response, ignore_values=[str(self.system_sales_account.id)])

    def test_view_no_permissions(self, client):
        path = "/sales-account/%s/"
        account = SalesAccountFactory()
        self.user.grounds = []
        self.user.accounts = []
        self.session.commit()
        response = client.get(path % account.id)
        self.verify_response(response)

    def test_view_not_found(self, client):
        path = "/sales-account/00000000-0000-0000-0000-000000000000/"
        response = client.get(path)
        assert response.status_code == http.client.NOT_FOUND

    def test_transactions(self, client):
        path = '/sales-account/%s/transactions.json'
        account = SalesAccountFactory()
        TransactionFactory(from_wallet=account.credit_wallet)
        self.session.commit()
        response = client.get(path % account.id)
        self.verify_response(response)

    def test_transactions_not_found(self, client):
        path = "/sales-account/00000000-0000-0000-0000-000000000000/transactions.json"
        response = client.get(path)
        assert response.status_code == http.client.NOT_FOUND

    def test_transactions_export(self, client):
        path = '/sales-account/%s/transactions.csv'
        account = SalesAccountFactory()
        TransactionFactory(from_wallet=account.credit_wallet)
        self.session.commit()
        response = client.get(path % account.id)
        self.verify_response(response)

    def test_transactions_export_not_found(self, client):
        path = "/sales-account/00000000-0000-0000-0000-000000000000/transactions.csv"
        response = client.get(path)
        assert response.status_code == http.client.NOT_FOUND

    def _test_sales_account_pages(self, client, where, user, system):
        for page, tmpl in [
            # My Sales Accounts
            ('my', '/user/sales-account/{account_type}.json'),
            # Sales account on the user page
            ('user', '/user/{user}/sales-account/{account_type}.json'),
            # List of all sales accounts in the navbar
            ('all', '/sales-account/{account_type}.json'),
        ]:
            for account_type in ['restricted', 'global']:
                path = tmpl.format(account_type=account_type, user=user.username)
                response = client.get(path)
                variant = '%s-%s-%s-%s' % (page, where, user.username, account_type)
                self.verify_response(response, variant=variant,
                                     ignore_values=[str(system.id)],
                                     frame=2)

    def test_sales_accounts(self, client, config, operator_role, vendor_role):
        other = GroundFactory()
        self.session.commit()
        sr1 = SalesAccountFactory(name='Restricted Ground #1',
                                  ground=self.ground)
        sr2 = SalesAccountFactory(name='Restricted Ground #2',
                                  ground=other)
        sg = GlobalSalesAccountFactory(name='Global')
        users = [
            OperatorFactory(roles=[operator_role],
                            username='operator-none',
                            accounts=[],
                            grounds=[]),
            OperatorFactory(roles=[operator_role],
                            username='operator-only-global',
                            accounts=[sg],
                            grounds=[other]),
            OperatorFactory(roles=[operator_role],
                            username='operator-only-1',
                            accounts=[sr1],
                            grounds=[self.ground]),
            OperatorFactory(roles=[operator_role],
                            username='operator-only-2',
                            accounts=[sr2],
                            grounds=[other]),
            OperatorFactory(roles=[operator_role],
                            username='operator-all',
                            accounts=[sr1, sr2, sg],
                            grounds=[self.ground, other]),
            VendorFactory(roles=[vendor_role],
                          username='vendor-none',
                          accounts=[],
                          grounds=[]),
            VendorFactory(roles=[vendor_role],
                          username='vendor-only-global',
                          accounts=[sg],
                          grounds=[other]),
            VendorFactory(roles=[vendor_role],
                          username='vendor-only-1',
                          accounts=[sr1],
                          grounds=[self.ground]),
            VendorFactory(roles=[vendor_role],
                          username='vendor-only-2',
                          accounts=[sr2],
                          grounds=[other]),
            VendorFactory(roles=[vendor_role],
                          username='vendor-all',
                          accounts=[sr1, sr2, sg],
                          grounds=[self.ground, other]),
        ]
        self.session.commit()
        system = SalesAccount.get_system()
        for params in [dict(HEROKU=True, SERIAL=self.ground.serial),
                       dict(HEROKU=False, SERIAL=self.ground.serial),
                       dict(HEROKU=False, SERIAL=other.serial)]:
            where = 'cloud' if params.get('HEROKU') else 'ground'
            if params['HEROKU']:
                where = 'cloud'
                del params['SERIAL']
            elif params['SERIAL'] == self.ground.serial:
                where = 'ground1'
            elif params['SERIAL'] == other.serial:
                where = 'ground2'
            for user in users:
                config.update(**params)
                client.login_as(user)
                self._test_sales_account_pages(client, where, user, system)

    def test_api_sales_accounts(self, client, config, api_role, operator_role):
        sg = GlobalSalesAccountFactory(name='Global')
        operator = OperatorFactory(roles=[operator_role],
                                   username='operator-only-global',
                                   accounts=[sg],
                                   grounds=[self.ground])
        api_users = [
            UserFactory(roles=[api_role],
                        username='api-with-account',
                        api_sales_account=sg),
            UserFactory(roles=[api_role],
                        username='api'),
        ]
        self.session.commit()
        system = SalesAccount.get_system()
        config['HEROKU'] = True
        client.login_as(operator)
        for user in api_users:
            self._test_sales_account_pages(client, 'cloud', user, system)

    def test_sales_accounts_bad_account_type(self, client):
        path = u"/sales-account/bad-account-type.json"
        response = client.get(path.format(user=self.user))
        self.verify_response(response)
