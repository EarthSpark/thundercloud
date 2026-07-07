# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.

from unittest import mock

import pytest
from testfixtures import LogCapture

from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (GlobalSalesAccountFactory, SalesAccountFactory,
                                                TransactionFactory, UserFactory)
from sparkmeter.transaction.transactiondomain import Wallet
from sparkmeter.user.userdomain import SalesAccountsUsers


@pytest.fixture()
def logger():
    """Logger fixture for sales account."""
    with LogCapture('sparkmeter.salesaccount.salesaccountcommand',
                    'sparkmeter.salesaccount.salesaccountdomain') as logger:
        yield logger


class SalesAccountCommandTest(SparkMeterTestCaseBase):
    def test_list(self, cli, logger):
        global_a = GlobalSalesAccountFactory(name='SalesAccount1')
        global_b = GlobalSalesAccountFactory(name='SalesAccount2')
        global_c = GlobalSalesAccountFactory(name='SalesAccount3')
        global_d = GlobalSalesAccountFactory(name='SalesAccount4')

        self.session.commit()

        UserFactory(username='usera', accounts=[global_a, global_b])
        UserFactory(username='userb', accounts=[global_c, global_d])

        self.session.commit()

        cli('salesaccount', 'list')

        logger.check(
            ('sparkmeter.salesaccount.salesaccountcommand',
             'INFO',
             '                                  ID |                 NAME |                USERS'),
            ('sparkmeter.salesaccount.salesaccountcommand',
             'INFO',
             '====================================================================================='),
            ('sparkmeter.salesaccount.salesaccountcommand',
             'INFO',
             u'0000000a-0001-0000-0000-000000000001 |        SalesAccount1 |                usera'),
            ('sparkmeter.salesaccount.salesaccountcommand',
             'INFO',
             u'0000000a-0001-0000-0000-000000000002 |        SalesAccount2 |                usera'),
            ('sparkmeter.salesaccount.salesaccountcommand',
             'INFO',
             u'0000000a-0001-0000-0000-000000000003 |        SalesAccount3 |                userb'),
            ('sparkmeter.salesaccount.salesaccountcommand',
             'INFO',
             u'0000000a-0001-0000-0000-000000000004 |        SalesAccount4 |                userb')
        )

    def test_delete(self, cli, logger):
        g = GlobalSalesAccountFactory(name='global')
        self.session.commit()

        with mock.patch('sparkmeter.salesaccount.salesaccountcommand.prompt_bool') as prompt_bool:
            prompt_bool.return_value = False
            result = cli('salesaccount', 'delete', '-i', str(g.id))
            assert result.exit_code == 1

        logger.check(
            ('sparkmeter.salesaccount.salesaccountcommand',
             'INFO',
             'sales account delete aborted'),
        )
        logger.clear()

        result = cli('salesaccount', 'delete', '-i', str(g.id), '-y')
        assert result.exit_code == 0

        logger.check(
            ('sparkmeter.salesaccount.salesaccountcommand',
             'INFO',
             u'sales account global was deleted'),
        )

    def test_delete_errors(self, cli, logger):
        result = cli('salesaccount', 'delete', '-i', '12345678123456781234567812345678', '-y')
        assert result.exit_code == 1
        logger.check(
            ('sparkmeter.salesaccount.salesaccountcommand', 'ERROR',
             'sales account 12345678123456781234567812345678 does not exist')
        )
        logger.clear()

    def test_merge(self, cli, logger, api_role):
        global_a = GlobalSalesAccountFactory()
        global_b = GlobalSalesAccountFactory()
        self.session.commit()

        UserFactory(accounts=[global_a])
        api_user = UserFactory(username='api-with-account',
                               roles=[api_role],
                               api_sales_account=global_b,
                               accounts=[global_b])
        self.session.commit()

        global_a.credit_wallet.value = 20
        global_b.credit_wallet.value = 20
        self.session.commit()

        TransactionFactory(_from_wallet_account=global_a, amount=10.5).process()
        TransactionFactory(_from_wallet_account=global_b, amount=11.6).process()
        self.session.commit()

        assert global_a.credit_wallet.id != global_b.credit_wallet.id

        result = cli('salesaccount', 'merge',
                     '-a', str(global_a.id), '-b', str(global_b.id), '-y')
        assert result.exit_code == 0

        wallets_a = Wallet.query.filter_by(sales_account_id=global_a.id)
        wallets_b = Wallet.query.filter_by(sales_account_id=global_b.id)
        account_users_a = SalesAccountsUsers.query.filter_by(sales_account_id=global_a.id)
        account_users_b = SalesAccountsUsers.query.filter_by(sales_account_id=global_b.id)
        account_a = SalesAccount.query.filter_by(id=global_a.id)
        account_b = SalesAccount.query.filter_by(id=global_b.id)

        assert wallets_a.count() == 2
        assert wallets_b.count() == 0
        assert global_a.credit_wallet.value == 17.9
        assert account_users_a.count() == 2
        assert account_users_b.count() == 0
        assert account_a.count() == 1
        assert account_b.count() == 0
        assert api_user.api_sales_account_id == global_a.id

        global_c = GlobalSalesAccountFactory()
        logger.clear()
        self.session.commit()

        with mock.patch('sparkmeter.salesaccount.salesaccountcommand.prompt_bool') as prompt_bool:
            prompt_bool.return_value = False
            result = cli('salesaccount', 'merge',
                         '-a', str(global_a.id), '-b', str(global_c.id))
            assert result.exit_code == 1

        logger.check(('sparkmeter.salesaccount.salesaccountcommand', 'WARNING',
                      ('2 wallets associated with sales account '
                       '0000000a-0001-0000-0000-000000000003')),
                     ('sparkmeter.salesaccount.salesaccountcommand', 'WARNING',
                      '0 users associated with sales account 0000000a-0001-0000-0000-000000000003'),
                     ('sparkmeter.salesaccount.salesaccountcommand', 'WARNING',
                      ('0 transactions associated with sales account '
                       '0000000a-0001-0000-0000-000000000003')),
                     ('sparkmeter.salesaccount.salesaccountcommand', 'INFO',
                      'sales account merge aborted'))

    def test_merge_errors(self, cli, logger):
        global_a = GlobalSalesAccountFactory()
        restricted_a = SalesAccountFactory()
        self.session.commit()

        # 1) when sales account ids are the same
        result = cli('salesaccount', 'merge',
                     '-a', str(global_a.id), '-b', str(global_a.id), '-y')
        assert result.exit_code == 1
        logger.check(('sparkmeter.salesaccount.salesaccountcommand', 'ERROR',
                      'please enter two different sales accounts'))
        logger.clear()

        # 2) when both sales accounts don't exist
        does_not_exist = '12345678123456781234567812345678'
        does_not_exist_either = '12345678123456781234567812345679'
        result = cli('salesaccount', 'merge',
                     '-a', does_not_exist, '-b', does_not_exist_either, '-y')
        assert result.exit_code == 1
        logger.check(('sparkmeter.salesaccount.salesaccountcommand', 'ERROR',
                      'sales account 12345678123456781234567812345678 does not exist'))
        logger.clear()

        # 3) when one sales account doesn't exist
        result = cli('salesaccount', 'merge',
                     '-a', str(global_a.id), '-b', does_not_exist_either, '-y')
        assert result.exit_code == 1
        logger.check(('sparkmeter.salesaccount.salesaccountcommand', 'ERROR',
                      'sales account 12345678123456781234567812345679 does not exist'))
        logger.clear()

        # 4) when one sales account is restricted
        result = cli('salesaccount', 'merge',
                     '-a', str(global_a.id), '-b', str(restricted_a.id), '-y')
        assert result.exit_code == 1
        msg = (u'sales account sales åccöünt 1 with id '
               u'(0000000a-0000-0000-0000-000000000001) is a restricted sales account')
        logger.check(('sparkmeter.salesaccount.salesaccountcommand', 'ERROR', msg),)
        logger.clear()

        result = cli('salesaccount', 'merge',
                     '-a', str(restricted_a.id), '-b', str(global_a.id), '-y')
        assert result.exit_code == 1
        msg = (u'sales account sales åccöünt 1 with id '
               u'(0000000a-0000-0000-0000-000000000001) is a restricted sales account')
        logger.check(('sparkmeter.salesaccount.salesaccountcommand', 'ERROR', msg),)
        logger.clear()
