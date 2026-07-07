# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.

from unittest import mock

import pytest

from sparkmeter.exceptions import DatabaseLockTimeoutException, TransactionError
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import SalesAccountFactory, TransactionFactory
from sparkmeter.transaction.transactiondomain import Transaction
from sparkmeter.transaction.transactiontasks import process_transactions


class TaskTest(SparkMeterTestCaseBase):

    def test_process_transactions(self, config, send_set_config, scoped_session):
        account = SalesAccountFactory(credit_wallet__value=1000)
        transaction = TransactionFactory(from_wallet=account.credit_wallet)
        self.session.commit()

        config['HEROKU'] = False
        with mock.patch('sparkmeter.controller.session_scope', scoped_session):
            process_transactions()
        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command='enable',
                balance=100.0,
                low_balance=False,
                firmware_version=u'abc1234'),
        ]

        self.session.add(transaction)
        assert transaction.state == Transaction.STATE_PROCESSED

    def test_process_transactions_deadlock(self, config, send_set_config, scoped_session,
                                           sentry_logger):
        account = SalesAccountFactory(credit_wallet__value=1000)
        transaction = TransactionFactory(from_wallet=account.credit_wallet)
        self.session.commit()
        tx_id = transaction.id

        config['HEROKU'] = False
        with mock.patch('sparkmeter.controller.session_scope', scoped_session):
            with mock.patch('sparkmeter.controller.process_transaction',
                            side_effect=DatabaseLockTimeoutException):
                with pytest.raises(DatabaseLockTimeoutException):
                    process_transactions()

        transaction = self.session.query(Transaction).get(tx_id)
        assert len(sentry_logger.records) == 1
        assert ('Transaction {} process lock timeout'.format(tx_id) in sentry_logger.records[0].getMessage())
        assert '\'action\': \'transaction_processing\'' in sentry_logger.records[0].getMessage()
        assert send_set_config.mock_calls == []
        assert transaction.state == Transaction.STATE_PENDING

    def test_process_transactions_error_raised(self, config, send_set_config, scoped_session):
        account = SalesAccountFactory(credit_wallet__value=1000)
        transactions = [
            TransactionFactory(from_wallet=account.credit_wallet),
            TransactionFactory(from_wallet=account.credit_wallet),
        ]
        self.session.commit()
        tx_id = transactions[0].id

        config['HEROKU'] = False
        with mock.patch('sparkmeter.controller.session_scope', scoped_session):
            with mock.patch('sparkmeter.controller.process_transaction',
                            side_effect=TransactionError(TransactionError.ERROR_NOT_ENOUGH_FUNDS, '')
                            ) as process_tx_mock:
                with pytest.raises(TransactionError):
                    process_transactions()

                process_tx_mock.assert_called_once_with(tx_id)
        assert send_set_config.mock_calls == []

    def test_process_transactions_error_skipped(self, config, send_set_config, scoped_session):
        account = SalesAccountFactory(credit_wallet__value=1000)
        transactions = [
            TransactionFactory(from_wallet=account.credit_wallet),
            TransactionFactory(from_wallet=account.credit_wallet),
            TransactionFactory(from_wallet=account.credit_wallet),
            TransactionFactory(from_wallet=account.credit_wallet),
        ]
        self.session.commit()
        ids = [mock.call(tx.id) for tx in transactions]

        config['HEROKU'] = False
        with mock.patch('sparkmeter.controller.session_scope', scoped_session):
            with mock.patch('sparkmeter.controller.process_transaction',
                            side_effect=[
                                TransactionError(TransactionError.ERROR_ALREADY_PROCESSED, ''),
                                TransactionError(TransactionError.ERROR_ALREADY_REVERSED, ''),
                                TransactionError(TransactionError.ERROR_NOT_ENOUGH_FUNDS, ''),
                            ]) as process_tx_mock:
                with pytest.raises(TransactionError):
                    process_transactions()

                assert process_tx_mock.call_count == 3
                process_tx_mock.assert_has_calls([ids[0], ids[1], ids[2]])
        assert send_set_config.mock_calls == []
