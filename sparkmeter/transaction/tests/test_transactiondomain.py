# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import datetime
from unittest import mock

import pytest
from dateutil.tz import tzlocal, tzutc
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from sparkmeter.config.configparameter import parameters
from sparkmeter.database.types import Choice
from sparkmeter.exceptions import TransactionError
from sparkmeter.meter.meterstate import MeterState
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (EventFactory, GroundFactory, MeterFactory,
                                                OperatorFactory, SalesAccountFactory,
                                                TransactionFactory, TransactionSourceFactory)
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource, Wallet


class TransactionTest(SparkMeterTestCaseBase):

    def _place_transaction(self, operator_role, meter, amount):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account],
                               roles=[operator_role],
                               grounds=[account.ground])
        source = TransactionSourceFactory()
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=100,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )
        self.session.commit()
        t = Transaction.get_by_id(transaction.id)
        t.process()
        return t

    def test_create_transactions_power(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        source = TransactionSourceFactory()
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )

        assert transaction.state == Transaction.STATE_PENDING
        assert transaction.amount == 40.0
        assert transaction.to_wallet.meter_id == meter.id
        assert transaction.from_wallet.sales_account_id == account.id

    def test_create_transactions_debt(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account, SalesAccount.get_system()],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        source = TransactionSourceFactory()
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=meter,
            to_object=account,
            amount=40,
            wallet_type=Wallet.TYPE_DEBT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )

        assert transaction.state == Transaction.STATE_PENDING
        assert transaction.amount == 40.0
        assert transaction.to_wallet.sales_account_id == account.id
        assert transaction.from_wallet.meter_id == meter.id

    def test_create_transactions_memo(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        source = TransactionSourceFactory()
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
            memo='This is a memo'
        )

        assert transaction.state == Transaction.STATE_PENDING
        assert transaction.amount == 40.0
        assert transaction.to_wallet.meter_id == meter.id
        assert transaction.from_wallet.sales_account_id == account.id
        assert transaction.memo == 'This is a memo'

        no_memo_tx = Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )
        assert no_memo_tx.memo is None

        with pytest.raises(ValueError) as valerr:
            Transaction.create_transactions(
                from_object=account,
                to_object=meter,
                amount=40,
                wallet_type=Wallet.TYPE_CREDIT,
                user=user,
                source=source,
                ground=meter.ground,
                session=self.session,
                memo='x' * 301
            )
        assert 'memos may not be longer than 300 characters' in str(valerr.value)

    def test_create_transactions_bonus(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account, SalesAccount.get_system()],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        self.session.commit()

        source = self.session.query(TransactionSource).filter_by(
            name=TransactionSource.BONUS).one()
        Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            markup=0.1,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )

        transactions = self.session.query(Transaction).all()
        assert len(transactions) == 1

    def test_create_transactions_negative(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account, SalesAccount.get_system()],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        source = TransactionSourceFactory()
        self.session.commit()

        Transaction.create_transactions(
            from_object=SalesAccount.get_system(),
            to_object=meter,
            amount=-40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )

        transactions = self.session.query(Transaction).all()
        assert len(transactions) == 1
        assert transactions[0].amount == -40

    def test_create_transactions_error(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=30)
        self.session.commit()
        user = OperatorFactory(accounts=[account],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200)
        source = TransactionSourceFactory()
        self.session.commit()

        with pytest.raises(TransactionError) as ctx:
            Transaction.create_transactions(
                from_object=account,
                to_object=meter,
                amount=80,
                wallet_type=Wallet.TYPE_CREDIT,
                user=user,
                source=source,
                ground=meter.ground,
                session=self.session,
            )
        assert ctx.value.code == TransactionError.ERROR_NOT_ENOUGH_FUNDS
        assert ctx.value.message == (
            u'sales åccöünt 1 does not have enough credit (30.00) '
            u'to cover a transaction of 80.00')
        assert account.credit_wallet.value == 30
        assert meter.credit_wallet.value == 200

    def test_create_transactions_debt_error(self, operator_role):
        account = SalesAccountFactory(debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account, self.system_sales_account],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(debt_wallet__value=70)
        source = TransactionSourceFactory()
        self.session.commit()

        with pytest.raises(TransactionError) as ctx:
            Transaction.create_transactions(
                from_object=meter,
                to_object=account,
                amount=80,
                wallet_type=Wallet.TYPE_DEBT,
                user=user,
                source=source,
                ground=meter.ground,
                session=self.session
            )
        assert ctx.value.code == TransactionError.ERROR_NOT_ENOUGH_FUNDS
        assert ctx.value.message == (
            u'test micrøgrid 1, Meter SM15R-01-00000001 does not have enough '
            u'debt (70.00) to cover a transaction of 80.00')

        assert account.debt_wallet.value == 0
        assert meter.debt_wallet.value == 70

    def test_create_transactions_negative_non_system_error(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account, SalesAccount.get_system()],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        source = TransactionSourceFactory()
        self.session.commit()

        with pytest.raises(ValueError) as ctx:
            Transaction.create_transactions(
                from_object=account,
                to_object=meter,
                amount=-40,
                wallet_type=Wallet.TYPE_CREDIT,
                user=user,
                source=source,
                ground=meter.ground,
                session=self.session,
            )
        assert str(ctx.value) == "only system sales accounts can create negative transactions"
        transactions = self.session.query(Transaction).all()
        assert len(transactions) == 0

    def test_create_transactions_negative_non_sales_error(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account, SalesAccount.get_system()],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        source = TransactionSourceFactory()
        self.session.commit()

        with pytest.raises(ValueError) as ctx:
            Transaction.create_transactions(
                from_object=meter,
                to_object=account,
                amount=-40,
                wallet_type=Wallet.TYPE_CREDIT,
                user=user,
                source=source,
                ground=meter.ground,
                session=self.session,
            )
        assert str(ctx.value) == "amount must be positive, not -40"
        transactions = self.session.query(Transaction).all()
        assert len(transactions) == 0

    def test_create_transactions_negative_with_markup_error(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account, SalesAccount.get_system()],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        source = TransactionSourceFactory()
        self.session.commit()

        with pytest.raises(ValueError) as ctx:
            Transaction.create_transactions(
                from_object=SalesAccount.get_system(),
                to_object=meter,
                amount=-40,
                wallet_type=Wallet.TYPE_CREDIT,
                user=user,
                source=source,
                ground=meter.ground,
                session=self.session,
                markup=0.05
            )
        assert str(ctx.value) == "negative transactions cannot have markup"
        transactions = self.session.query(Transaction).all()
        assert len(transactions) == 0

    def test_create_transactions_zero_error(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account, SalesAccount.get_system()],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        source = TransactionSourceFactory()
        self.session.commit()

        with pytest.raises(ValueError) as ctx:
            Transaction.create_transactions(
                from_object=SalesAccount.get_system(),
                to_object=meter,
                amount=0,
                wallet_type=Wallet.TYPE_CREDIT,
                user=user,
                source=source,
                ground=meter.ground,
                session=self.session,
            )
        assert str(ctx.value) == "amount cannot be zero"
        transactions = self.session.query(Transaction).all()
        assert len(transactions) == 0

    def test_create_transactions_transfer(self, operator_role):
        ground = GroundFactory.get_default()
        account = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        user = OperatorFactory(accounts=[account, self.system_sales_account],
                               roles=[operator_role],
                               grounds=[account.ground])
        source = self.session.query(TransactionSource).filter_by(name=TransactionSource.CASH).one()
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=self.system_sales_account,
            to_object=account,
            amount=40,
            user=user,
            wallet_type=Wallet.TYPE_CREDIT,
            source=source,
            ground=ground,
            markup=0.05,
            session=self.session,
        )
        self.session.commit()

        assert Transaction.query.count() == 2

        assert transaction.to_wallet.sales_account_id == account.id
        assert transaction.from_wallet.sales_account_id == self.system_sales_account.id
        assert transaction.acct_type == "credit"
        assert transaction.state == Transaction.STATE_PENDING
        assert transaction.amount == 40.0

        bonus_transaction = Transaction.query[1]
        assert bonus_transaction.to_wallet.sales_account_id == account.id
        assert transaction.from_wallet.sales_account_id == self.system_sales_account.id
        assert bonus_transaction.acct_type == "credit"
        assert transaction.state == Transaction.STATE_PENDING
        assert bonus_transaction.amount == 2.0

    def test_create_transactions_transfer_bonus_tuple(self, operator_role):
        ground = GroundFactory.get_default()
        account = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        user = OperatorFactory(accounts=[account, self.system_sales_account],
                               roles=[operator_role],
                               grounds=[account.ground])
        source = self.session.query(TransactionSource).filter_by(name=TransactionSource.CASH).one()
        self.session.commit()

        transaction, bonus = Transaction.create_transactions(
            from_object=self.system_sales_account,
            to_object=account,
            amount=40,
            user=user,
            wallet_type=Wallet.TYPE_CREDIT,
            source=source,
            ground=ground,
            markup=0.05,
            session=self.session,
            return_bonus_tuple=True,
        )
        self.session.commit()

        assert Transaction.query.count() == 2

        assert transaction.to_wallet.sales_account_id == account.id
        assert transaction.from_wallet.sales_account_id == self.system_sales_account.id
        assert transaction.acct_type == "credit"
        assert transaction.state == Transaction.STATE_PENDING
        assert transaction.amount == 40.0

        bonus_transaction = Transaction.query[1]
        assert bonus_transaction.id == bonus.id

    def test_create_transactions_transfer_no_markup(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        ground = GroundFactory.get_default()
        user = OperatorFactory(accounts=[account, self.system_sales_account],
                               roles=[operator_role],
                               grounds=[account.ground])

        source = self.session.query(TransactionSource).filter_by(name=TransactionSource.CASH).one()
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=self.system_sales_account,
            to_object=account,
            amount=40,
            user=user,
            wallet_type=Wallet.TYPE_CREDIT,
            source=source,
            ground=ground,
            markup=0.0,
            session=self.session,
        )

        assert Transaction.query.count() == 1

        assert transaction.to_wallet.sales_account_id == account.id
        assert transaction.from_wallet.sales_account_id == self.system_sales_account.id
        assert transaction.acct_type == "credit"
        assert transaction.state == Transaction.STATE_PENDING
        assert transaction.amount == 40.0

    def test_create_transactions_transfer_no_markup_tuple(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        ground = GroundFactory.get_default()
        user = OperatorFactory(accounts=[account, self.system_sales_account],
                               roles=[operator_role],
                               grounds=[account.ground])

        source = self.session.query(TransactionSource).filter_by(name=TransactionSource.CASH).one()
        self.session.commit()

        transaction, bonus = Transaction.create_transactions(
            from_object=self.system_sales_account,
            to_object=account,
            amount=40,
            user=user,
            wallet_type=Wallet.TYPE_CREDIT,
            source=source,
            ground=ground,
            markup=0.0,
            session=self.session,
            return_bonus_tuple=True,
        )

        assert Transaction.query.count() == 1
        assert transaction is not None
        assert bonus is None

    def test_create_transactions_transfer_invalid_markup(self, operator_role):
        account = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        ground = GroundFactory.get_default()
        user = OperatorFactory(accounts=[account, self.system_sales_account],
                               roles=[operator_role],
                               grounds=[account.ground])

        source = self.session.query(TransactionSource).filter_by(name=TransactionSource.CASH).one()
        self.session.commit()

        with pytest.raises(ValueError) as ctx:
            Transaction.create_transactions(
                from_object=self.system_sales_account,
                to_object=account,
                amount=40,
                user=user,
                wallet_type=Wallet.TYPE_CREDIT,
                source=source,
                ground=ground,
                markup=-0.02,
                session=self.session,
            )

        assert str(ctx.value) == "markup must be between 0 and 1"
        transactions = self.session.query(Transaction).all()
        assert len(transactions) == 0

    def test_get_by_external_id(self):
        TransactionFactory(external_id="external_id")
        self.session.flush()
        t = Transaction.get_by_external_id("external_id")
        assert t.external_id == 'external_id'

    def test_get_by_id_or_external_id(self):
        t1 = TransactionFactory()
        TransactionFactory(external_id="external_id")
        self.session.flush()
        t = Transaction.get_by_id_or_external_id("external_id")
        assert t.external_id == "external_id"
        t = Transaction.get_by_id_or_external_id(t1.id)
        assert t.id == t1.id

    def test_get_by_id_or_external_id_multiple(self):
        TransactionFactory()
        TransactionFactory(external_id="external_id")
        TransactionFactory(external_id="external_id")
        self.session.flush()
        with pytest.raises(MultipleResultsFound):
            Transaction.get_by_id_or_external_id("external_id")

    def test_get_by_id_or_external_id_no_results(self):
        TransactionFactory()
        TransactionFactory(external_id="external_id")
        TransactionFactory(external_id="external_id")
        self.session.flush()
        with pytest.raises(NoResultFound):
            Transaction.get_by_id_or_external_id("different_id")

    def test_status_text(self):
        t = TransactionFactory()
        assert t.status_text == 'Not processed'
        t.state = Transaction.STATE_PROCESSED
        assert t.status_text == 'Processed'
        t.state = Transaction.STATE_ERROR
        assert t.status_text == 'Error'
        t.state = Transaction.STATE_REVERSED
        assert t.status_text == 'Reversed'
        t.state = 'invalid'
        with pytest.raises(NotImplementedError):
            t.status_text

    def test_process_with_reference_id(self, send_set_config):
        t1 = TransactionFactory(state=Transaction.STATE_PROCESSED)
        t1.from_wallet.value = 100
        t2 = self.create_transaction(reference_id=t1.id)
        self.session.commit()
        t2.process()
        t1 = Transaction.get_by_id(t1.id)
        assert t1.state == Transaction.STATE_PROCESSED
        assert send_set_config.mock_calls == []
        assert t2.processed_timestamp is not None

    def test_process_reversal(self, mocker, send_set_config):
        event_create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        event_create.return_value = EventFactory()
        t1 = self.create_transaction(state=Transaction.STATE_PROCESSED)
        t1.from_wallet.value = 100
        t2 = self.create_transaction(origin=Transaction.ORIGIN_REVERSAL,
                                     reference_id=t1.id)
        self.session.commit()
        t2.process()
        t1 = Transaction.get_by_id(t1.id)
        assert t1.state == Transaction.STATE_REVERSED
        assert t1.reversed_timestamp is not None
        assert send_set_config.mock_calls == []
        assert event_create.mock_calls == [
            mock.call('reversal-transaction-processed', obj=t1),
        ]

    def test_process_not_pending(self):
        t = TransactionFactory(state=Transaction.STATE_PROCESSED)
        with pytest.raises(TransactionError) as ctx:
            t.process()
        assert ctx.value.code == TransactionError.ERROR_ALREADY_PROCESSED
        assert ctx.value.message == (
            u'Error processing transaction 00000007-0000-0000-0000-000000000001: '
            u'already processed')

    def test_process_wrong_acct_type(self):
        t = TransactionFactory(acct_type=Choice(code=u'foobar', value='yay'))
        with pytest.raises(TransactionError) as ctx:
            t.process()
        assert ctx.value.code == TransactionError.ERROR_WRONG_TYPE
        assert ctx.value.message == (
            u'Error processing transaction 00000007-0000-0000-0000-000000000001: '
            u'unknown transaction type (foobar)')

    def test_process_not_enough_with_negative_permitted(self):
        t = TransactionFactory()
        t.from_wallet.value = 0
        with pytest.raises(TransactionError) as ctx:
            t.process()
        assert ctx.value.code == TransactionError.ERROR_NOT_ENOUGH_FUNDS
        assert ctx.value.message == (
            u'Sending side does not contain enough funds (0.00) to complete transfer '
            u'of value 100.00.')

    def test_process_already_reversed(self):
        a = TransactionFactory(state=Transaction.STATE_PROCESSED)
        b = TransactionFactory(state=Transaction.STATE_PROCESSED,
                               origin=Transaction.ORIGIN_REVERSAL)
        b.reference_id = a.id
        c = TransactionFactory(state=Transaction.STATE_PENDING,
                               origin=Transaction.ORIGIN_REVERSAL)
        c.reference_id = a.id
        self.session.commit()
        c.from_wallet.value = 100
        with pytest.raises(TransactionError) as ctx:
            c.process()
        assert ctx.value.code == TransactionError.ERROR_ALREADY_REVERSED
        assert ctx.value.message == u'Parent transaction already reversed.'

    def test_reverse(self):
        t = self.create_transaction(state=Transaction.STATE_PROCESSED)
        self.session.commit()
        reverse = t.reverse(t.user)
        assert reverse.amount == -t.amount
        assert reverse.from_wallet == t.from_wallet
        assert reverse.to_wallet == t.to_wallet
        assert reverse.acct_type == t.acct_type
        assert reverse.user.id == t.user.id
        assert reverse.reference_id == t.id
        assert reverse.origin == Transaction.ORIGIN_REVERSAL
        assert reverse.ground == t.ground

    def test_reverse_bad_user(self):
        t = TransactionFactory(state=Transaction.STATE_PROCESSED)
        with pytest.raises(TypeError):
            t.reverse('bad-user-type')

    def test_reverse_not_processed(self):
        t = self.create_transaction(state=Transaction.STATE_PENDING)
        with pytest.raises(TransactionError) as ctx:
            t.reverse(t.user)
        assert ctx.value.code == TransactionError.ERROR_NOT_PROCESSED
        assert ctx.value.message == u'Not processed'

    def test_set_error(self):
        t = TransactionFactory()
        assert t.error is None
        assert t.state == Transaction.STATE_PENDING
        t.set_error('Error')
        assert t.error == 'Error'
        assert t.state == Transaction.STATE_ERROR
        assert t.errored_timestamp is not None
        msg = "This transaction has already an error set."
        with pytest.raises(ValueError, match=msg):
            t.set_error('Error2')
        assert t.error == 'Error'
        assert t.state == Transaction.STATE_ERROR

    def test_get_unprocessed(self):
        m1 = GroundFactory()
        t1 = TransactionFactory(ground=m1)
        m2 = GroundFactory()
        t2 = TransactionFactory(ground=m2)
        m3 = GroundFactory()
        self.session.commit()

        ts1 = list(Transaction.get_unprocessed(m1))
        assert len(ts1) == 1
        assert ts1[0].id == t1.id

        ts2 = list(Transaction.get_unprocessed(m2))
        assert len(ts2) == 1
        assert ts2[0].id == t2.id

        ts3 = list(Transaction.get_unprocessed(m3))
        assert len(ts3) == 0

    def test_transaction_turn_on_meter(self, config, operator_role, send_set_config):
        config['HEROKU'] = False
        meter = MeterFactory(
            credit_wallet__value=-10,
            debt_wallet__value=0,
            system_info__current_state=MeterState.STATE_OFF.id,
            system_info__current_user_power_limit=100,
        )
        self._place_transaction(operator_role, meter, 100)
        meter.system_info.update_from_set_config(
            command='enable',
            application_version='app-ver',
            bootloader_version=u'abc1234',
            power_limit=50.0,
        )
        self.session.commit()

        assert send_set_config.mock_calls == [
            mock.call(subnet=255,
                      current_limit=10000.0,
                      load_limit=50.0,
                      mac=1,
                      command='enable',
                      balance=90.0,
                      low_balance=False,
                      firmware_version=u'abc1234'),
        ]

        send_set_config.reset_mock()
        self._place_transaction(operator_role, meter, 100)
        assert send_set_config.mock_calls == []

    def test_transaction_turn_off_meter(self, config, mocker, operator_role, send_set_config):
        event_create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        event_create.return_value = EventFactory()
        config['HEROKU'] = False
        meter = MeterFactory(
            credit_wallet__value=-50,
            debt_wallet__value=0,
            system_info__current_state=MeterState.STATE_OFF.id,
        )
        transaction = self._place_transaction(operator_role, meter, 100)
        assert send_set_config.mock_calls == [
            mock.call(subnet=255,
                      current_limit=10000.0,
                      load_limit=50.0,
                      mac=1,
                      command='enable',
                      balance=50.0,
                      low_balance=False,
                      firmware_version=u'abc1234'),
        ]
        send_set_config.reset_mock()
        rt = transaction.reverse(transaction.user)
        self.session.add(rt)
        self.session.commit()
        rt.process()
        assert send_set_config.mock_calls == [
            mock.call(subnet=255,
                      current_limit=10000.0,
                      load_limit=50.0,
                      mac=1,
                      command='disable',
                      balance=-50.0,
                      low_balance=True,
                      firmware_version=u'abc1234'),
        ]
        assert event_create.mock_calls == [
            mock.call('reversal-transaction-processed', obj=mock.ANY),
        ]

    def test_convert_to_debt(self, operator_role, mocker):
        event_create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        event_create.return_value = EventFactory()
        parameters.ALLOW_NEGATIVE_BALANCE = False
        event_create.reset_mock()
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account],
                               roles=[operator_role],
                               grounds=[account.ground])
        meter = MeterFactory(credit_wallet__value=0, debt_wallet__value=0)
        source = TransactionSourceFactory()
        self.session.commit()

        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=100,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )
        self.session.commit()
        t = Transaction.get_by_id(transaction.id)
        t.process()
        assert meter.credit_wallet.value == 100.0
        assert meter.debt_wallet.value == 0.0
        assert account.credit_wallet.value == 900.0

        # Consume some energy
        meter.credit_wallet.value -= 20.0
        self.session.add(meter)
        self.session.commit()

        # Revert, which would cause negative balance to be created
        reverse_transaction = t.reverse(user)
        assert meter.credit_wallet.value == 80.0
        assert meter.debt_wallet.value == 0.0
        assert account.credit_wallet.value == 900.0

        self.session.add(reverse_transaction)
        self.session.commit()
        t2 = Transaction.get_by_id(reverse_transaction.id)
        t2.process()
        assert meter.credit_wallet.value == 0.0
        assert meter.debt_wallet.value == 20.0
        assert account.credit_wallet.value == 1000.0
        assert event_create.mock_calls == [
            mock.call('reversal-transaction-processed', obj=mock.ANY),
        ]

    def test_get_processed_by_day(self, config, send_set_config):
        config['HEROKU'] = False
        latency = datetime.timedelta(days=1)
        day1 = datetime.datetime(2018, 1, 13, 9, 0, 0, 0)
        day2 = datetime.datetime(2018, 1, 14, 11, 0, 0, 0)
        day3 = datetime.datetime(2018, 1, 15, 12, 0, 0, 0)

        t1 = TransactionFactory()
        t1.created = day1
        t1.from_wallet.value = 100
        t1.process()

        t2 = self.create_transaction(amount=30)
        t2.created = day2
        t2.from_wallet.value = 30
        t2.process()
        self.session.commit()

        t3 = self.create_transaction(amount=28)
        t3.created = day2
        t3.from_wallet.value = 30
        t3.process()
        t3.processed_timestamp = day2 + latency
        self.session.commit()

        t4 = t2.reverse(t2.user)
        t4.created = day3
        self.session.add(t4)
        self.session.commit()
        t4.process()
        self.session.commit()

        t5 = t3.reverse(t3.user)
        t5.created = day2 + latency
        self.session.add(t5)
        self.session.commit()
        t5.process()
        t5.processed_timestamp = day2 + latency * 2
        self.session.commit()

        date = datetime.datetime.now()
        period_start = datetime.datetime(date.year, date.month, date.day, tzinfo=tzlocal())
        period_start = period_start.astimezone(tzutc()).replace(tzinfo=None)
        period_end = period_start + datetime.timedelta(days=1)
        results = Transaction.get_processed_by_day(self.ground, period_start, period_end).all()
        assert len(results) == 3
        assert results[0].total_processed == 1
        assert results[1].total_processed == 2
        assert results[2].total_processed == 1

        results = Transaction.get_processed_by_day(self.ground, period_start, period_end, day3).all()
        assert len(results) == 2
        assert results[0].total_processed == 1
        assert results[1].total_processed == 2


class WalletTest(SparkMeterTestCaseBase):
    def test_meter(self):
        meter = MeterFactory()
        self.session.commit()
        assert meter.credit_wallet.meter.id == meter.id

    def test_request_zero(self, mocker):
        event_create = mocker.patch('sparkmeter.event.eventdomain.Event.create')
        event_create.return_value = EventFactory()
        meter = MeterFactory()
        self.session.commit()
        wallet = meter.credit_wallet
        wallet.request_zero()
        assert event_create.mock_calls == [
            mock.call('customer-wallet-zero-requested', obj=wallet),
        ]
