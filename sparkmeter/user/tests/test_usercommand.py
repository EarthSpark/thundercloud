# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
from unittest import mock

from testfixtures import LogCapture

from sparkmeter.controller import create_default_roles
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import SalesAccountFactory, TransactionFactory, UserFactory
from sparkmeter.transaction.transactiondomain import Transaction
from sparkmeter.user import usercommand
from sparkmeter.user.userdomain import User


class TestManageCommands(SparkMeterTestCaseBase):

    def test_create_user_vendor(self, cli, scoped_session):
        with LogCapture('sparkmeter.user.usercommand') as logger:
            with mock.patch('sparkmeter.controller.session_scope', scoped_session):
                create_default_roles()
            result = cli('user', 'create',
                         '-e', 'test@sparkmeter.io',
                         '-p', 'pass',
                         '-u', 'testuser',
                         '-r', 'vendor')
            assert result.exit_code == 0

            user = User.query.filter_by(email='test@sparkmeter.io').one()
            assert user.email == 'test@sparkmeter.io'
            assert user.username == 'testuser'
            assert user.is_vendor()
            assert not user.is_operator()
            assert not user.account_all_access
            assert not user.ground_all_access
            assert user.accounts == []
            assert len(user.grounds) == 1
            assert user.grounds[0].id == self.ground.id

            logger.check(('sparkmeter.user.usercommand', 'INFO', 'user created'))

    def test_create_user_operator(self, cli, scoped_session):
        with LogCapture('sparkmeter.user.usercommand') as logger:
            with mock.patch('sparkmeter.controller.session_scope', scoped_session):
                create_default_roles()
            result = cli('user', 'create',
                         '-e', 'test@sparkmeter.io',
                         '-p', 'pass',
                         '-u', 'testuser',
                         '-r', 'operator')
            assert result.exit_code == 0

            user = User.query.filter_by(email='test@sparkmeter.io').one()
            assert user.email == 'test@sparkmeter.io'
            assert user.username == 'testuser'
            assert user.is_operator()
            assert not user.is_vendor()
            assert user.account_all_access
            assert user.ground_all_access
            assert user.accounts == [self.system_sales_account]
            assert len(user.grounds) == 1
            assert user.grounds[0].id == self.ground.id

            logger.check(('sparkmeter.user.usercommand', 'INFO', 'user created'))

    def test_create_user_interactive(self, cli, scoped_session):
        with LogCapture('sparkmeter.user.usercommand') as logger:
            with mock.patch('sparkmeter.controller.session_scope', scoped_session):
                create_default_roles()
            prompt = mock.Mock()
            prompt.return_value = 'prompt'
            prompt_choices = mock.Mock()
            prompt_choices.return_value = 'vendor'
            with mock.patch.multiple(usercommand, prompt=prompt, prompt_choices=prompt_choices):
                result = cli('user', 'create')
                assert result.exit_code == 0

            user = User.query.filter_by(email='prompt').one()
            assert user.email == 'prompt'
            assert user.username == 'prompt'
            assert user.is_vendor()
            assert not user.is_operator()

            logger.check(('sparkmeter.user.usercommand', 'INFO', 'user created'))

    def test_create_user_interactive_error(self, cli, scoped_session):
        with LogCapture('sparkmeter.user.usercommand') as logger:
            with mock.patch('sparkmeter.controller.session_scope', scoped_session):
                create_default_roles()
            prompt = mock.Mock()
            prompt.return_value = 'prompt'
            prompt_choices = mock.Mock()
            prompt_choices.return_value = 'does-not-exist'
            with mock.patch.multiple(usercommand, prompt=prompt, prompt_choices=prompt_choices):
                result = cli('user', 'create')
                assert result.exit_code == 1

            logger.check(
                ('sparkmeter.user.usercommand',
                 'ERROR',
                 "an error occurred: NoResultFound('No row was found when one was required'), try again")
            )

    def test_create_api_user(self, cli, scoped_session):
        with LogCapture('sparkmeter.user.usercommand') as logger:
            with mock.patch('sparkmeter.controller.session_scope', scoped_session):
                create_default_roles()
            prompt = mock.Mock()
            prompt.return_value = ''
            with mock.patch.multiple(usercommand, prompt=prompt):
                result = cli('user', 'create', '-u', 'api-user', '-r', 'api')
            assert result.exit_code == 0

            user = User.get_by_name('api-user')
            assert user.username == 'api-user'
            assert user.is_api()
            assert len(user.password) == 60
            assert not user.accounts

            logger.check(('sparkmeter.user.usercommand', 'INFO', 'user created'))

    def test_create_api_user_vendor(self, cli, scoped_session):
        with LogCapture('sparkmeter.user.usercommand') as logger:
            account = SalesAccountFactory()
            with mock.patch('sparkmeter.controller.session_scope', scoped_session):
                create_default_roles()
            result = cli('user', 'create',
                         '-u', 'api-user', '-r', 'api', '-a', account.name)
            assert result.exit_code == 0

            user = User.get_by_name('api-user')
            assert user.username == 'api-user'
            assert user.is_api()
            assert len(user.password) == 60
            assert user.accounts[0].id == account.id

            logger.check(('sparkmeter.user.usercommand', 'INFO', 'user created'))

    def test_list_users(self, cli):
        with LogCapture('sparkmeter.user.usercommand') as logger:
            UserFactory(username='user-a', email='usera@sparkmeter.io')
            UserFactory(username='user-b', email='userb@sparkmeter.io')

            self.session.commit()

            cli('user', 'list')

            logger.check(('sparkmeter.user.usercommand', 'INFO',
                          ('                                  ID |             USERNAME |'
                           '                          EMAIL')),
                         ('sparkmeter.user.usercommand', 'INFO',
                          ('=============================================================='
                           '==============================')),
                         ('sparkmeter.user.usercommand', 'INFO',
                          ('00000009-0000-0000-0000-000000000001 |               user-a |'
                           '            usera@sparkmeter.io')),
                         ('sparkmeter.user.usercommand', 'INFO',
                          ('00000009-0000-0000-0000-000000000002 |               user-b |'
                           '            userb@sparkmeter.io')))

    def test_merge_user(self, cli, scoped_session):
        accounta = SalesAccountFactory()
        accountb = SalesAccountFactory()

        usera = UserFactory(username='user-a', password='password-a',
                            grounds=[self.ground],
                            accounts=[accounta])
        userb = UserFactory(username='user-b', password='password-b',
                            grounds=[self.ground],
                            accounts=[accountb])
        transaction = TransactionFactory(user=userb)
        transaction.from_wallet.value = 100
        transaction.process()
        with mock.patch('sparkmeter.controller.session_scope', scoped_session):
            create_default_roles()
        self.session.commit()
        t = Transaction.query.one()
        assert t.user == userb

        with mock.patch('sparkmeter.user.usercommand.prompt_bool') as prompt_bool:
            prompt_bool.side_effect = [False, True]
            result = cli('user', 'merge',
                         '-a', str(usera.id), '-b', str(userb.id))
            assert result.exit_code == 0

        u = User.get_by_name('user-a')
        assert u
        assert u.password == 'password-b'
        assert not User.get_by_name('user-b')
        t = Transaction.query.one()
        assert t.user == u
        assert len(u.grounds) == 1
        assert u.grounds[0].id == self.ground.id
        assert len(u.accounts) == 2
        assert u.accounts[0].id == accounta.id
        assert u.accounts[1].id == accountb.id

    def test_merge_user_errors(self, cli, scoped_session):
        with LogCapture('sparkmeter.user.usercommand') as logger:
            usera = UserFactory(username='user-a')
            userb = UserFactory(username='user-b')

            self.session.commit()
            with mock.patch('sparkmeter.controller.session_scope', scoped_session):
                create_default_roles()

            does_not_exist = '12345678123456781234567812345678'
            does_not_exist_either = '12345678123456781234567812345679'

            result = cli('user', 'merge',
                         '-a', does_not_exist, '-b', does_not_exist_either, '-y')
            assert result.exit_code == 1
            logger.check(('sparkmeter.user.usercommand', 'ERROR',
                          'user 12345678123456781234567812345678 does not exist'))
            logger.clear()

            result = cli('user', 'merge',
                         '-a', str(usera.id), '-b', does_not_exist_either, '-y')
            assert result.exit_code == 1
            logger.check(('sparkmeter.user.usercommand', 'ERROR',
                          'user 12345678123456781234567812345679 does not exist'))
            logger.clear()

            with mock.patch('sparkmeter.user.usercommand.prompt_bool') as prompt_bool:
                prompt_bool.side_effect = [False, False]
                result = cli('user', 'merge',
                             '-a', str(usera.id), '-b', str(userb.id))
                assert result.exit_code == 1

            logger.check(('sparkmeter.user.usercommand', 'WARNING',
                          '0 transactions are associated with user user-b'),
                         ('sparkmeter.user.usercommand', 'INFO', 'user b password used'),
                         ('sparkmeter.user.usercommand', 'INFO', 'user merge aborted'))
