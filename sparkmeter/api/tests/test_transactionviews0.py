# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.

import http.client
from unittest import mock

import pytest

from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.exceptions import TransactionError
from sparkmeter.tests.test_data_factory import (EventFactory, MeterFactory, SalesAccountFactory,
                                                TransactionFactory)
from sparkmeter.transaction.transactiondomain import Transaction


class TransactionAddTest(APIView0TestCaseBase):

    path = "v0/transaction/"

    @pytest.fixture(autouse=True)
    def _setup_transaction(self):
        self.meter = MeterFactory(serial='SM15R-01-00000001',
                                  credit_wallet__value=5, debt_wallet__value=1)
        self.session.commit()
        yield

    def _test_post_common(self, response):
        r = response.json()
        t_id = r['transaction_id']
        self.verify_response(response, ignore_values=[t_id], frame=2)
        t = Transaction.get_by_id(t_id)
        assert t.from_wallet_id == self.account.credit_wallet.id
        assert t.to_wallet_id == self.meter.credit_wallet.id
        assert t.user_id == self.user.id
        assert t.amount == 40
        assert t.source.name == 'cash'
        assert t.external_id == 'abc123'
        assert t.memo is None

    def test_post_form(self):
        data = {
            'customer_id': self.meter.customer.id,
            'amount': 40,
            'source': 'cash',
            'external_id': 'abc123'
        }
        response = self.post(self.path, data=data)
        self._test_post_common(response)

    def test_post_json(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': 40,
            'source': 'cash',
            'external_id': 'abc123'
        }
        response = self.post(self.path, json=data)
        self._test_post_common(response)

    def test_post_memo(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': 40,
            'source': 'cash',
            'external_id': 'abc123',
            'memo': 'This is a memo',
        }
        response = self.post(self.path, json=data)
        r = response.json()
        t_id = r['transaction_id']
        self.verify_response(response, ignore_values=[t_id])
        t = Transaction.get_by_id(t_id)
        assert t.from_wallet_id == self.account.credit_wallet.id
        assert t.to_wallet_id == self.meter.credit_wallet.id
        assert t.user_id == self.user.id
        assert t.amount == 40
        assert t.source.name == 'cash'
        assert t.external_id == 'abc123'
        assert t.memo == 'This is a memo'

    def test_missing_sales_account(self):
        self.user.api_sales_account = None
        self.session.commit()
        response = self.post(self.path, data={})
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_customer_id_missing_parameter(self):
        response = self.post(self.path, data={})
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_customer_id_cannot_be_empty(self):
        response = self.post(self.path, data={'customer_id': ''})
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_customer_id_must_be_uuid(self):
        response = self.post(self.path, data={'customer_id': '123'})
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_amount_missing_parameter(self):
        data = {
            'customer_id': str(self.meter.customer.id),
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_amount_cannot_be_empty(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': '',
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_amount_must_be_number(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': 'abc',
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_negative_transaction_non_system(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': '-1',
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_negative_transactions(self):
        self.account.system = True
        self.session.commit()
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': '-40',
        }
        response = self.post(self.path, data=data)
        r = response.json()
        t_id = r['transaction_id']
        self.verify_response(response, ignore_values=[t_id])
        assert Transaction.query.count() == 1

    def test_source_cannot_be_empty(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': '1',
            'source': '',
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_external_id_cannot_be_empty(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': '1',
            'source': 'cash',
            'external_id': '',
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_no_such_customer(self):
        data = {
            'customer_id': '7390109f-7103-4777-84f0-89e7deff382a',
            'amount': '1',
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_no_such_source(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': '1',
            'source': 'invalid-source',
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_not_enough_funds(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': '15000',
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_transaction_already_exists(self):
        TransactionFactory(external_id="external_id")
        self.session.commit()
        assert Transaction.query.count() == 1
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': '1',
            'external_id': 'external_id',
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 1

    def test_account_disabled(self):
        self.account.active = False
        self.session.commit()
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': 40,
            'source': 'cash',
            'external_id': 'abc123'
        }
        response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0

    def test_transaction_generic_error(self):
        data = {
            'customer_id': str(self.meter.customer.id),
            'amount': '1',
        }
        with mock.patch.object(Transaction, 'create_transactions') as t:
            t.side_effect = TransactionError('generic', u'message')
            response = self.post(self.path, data=data)
        self.verify_response(response)
        assert Transaction.query.count() == 0


class TransactionViewTest(APIView0TestCaseBase):

    path = "v0/transaction/{id}"

    def _test_sales_account(self, account, account_type):
        t = TransactionFactory(from_wallet=account.credit_wallet)
        self.session.commit()
        response = self.get(self.path.format(id=t.id))
        self.verify_response(response,
                             variant='view-' + account_type,
                             ignore_values=[str(account.id)],
                             frame=2)

    def test_get(self):
        t = TransactionFactory()
        self.session.commit()
        response = self.get(self.path.format(id=t.id))
        self.verify_response(response)

    def test_get_by_external_id(self):
        t = TransactionFactory(external_id='foobar')
        self.session.commit()
        response = self.get(self.path.format(id=t.external_id))
        self.verify_response(response)

    def test_get_by_external_id_uuid(self):
        t = TransactionFactory(external_id='a6b794be-d1aa-41f3-b920-546260a6068e')
        self.session.commit()
        response = self.get(self.path.format(id=t.external_id))
        self.verify_response(response)

    def test_get_by_external_id_uuid_multiple(self):
        t = TransactionFactory(external_id='a6b794be-d1aa-41f3-b920-546260a6068e')
        TransactionFactory(external_id='a6b794be-d1aa-41f3-b920-546260a6068e')
        self.session.commit()
        response = self.get(self.path.format(id=t.external_id))
        self.verify_response(response)

    def test_get_error(self):
        t = TransactionFactory(error='transaction-error',
                               state=Transaction.STATE_ERROR)
        self.session.commit()
        response = self.get(self.path.format(id=t.id))
        self.verify_response(response)

    def test_get_reversed(self):
        t = TransactionFactory(state=Transaction.STATE_REVERSED)
        self.session.commit()
        response = self.get(self.path.format(id=t.id))
        self.verify_response(response)

    def test_get_processed(self):
        t = TransactionFactory(state=Transaction.STATE_PROCESSED)
        self.session.commit()
        response = self.get(self.path.format(id=t.id))
        self.verify_response(response)

    def test_get_memo(self):
        t = TransactionFactory()
        t.memo = 'This is a memo'
        self.session.commit()
        response = self.get(self.path.format(id=t.id))
        self.verify_response(response)

    def test_get_system(self):
        account = SalesAccountFactory(system=True, credit_wallet__value=1000)
        self._test_sales_account(account, 'system')

    def test_get_global(self):
        account = SalesAccountFactory(global_account=True, credit_wallet__value=1000)
        self._test_sales_account(account, 'global')

    def test_get_restricted(self):
        account = SalesAccountFactory(global_account=False, credit_wallet__value=1000)
        self._test_sales_account(account, 'restricted')

    def test_get_ground(self):
        t = TransactionFactory(from_wallet=self.system_sales_account.credit_wallet)
        self.session.commit()

        response = self.get(self.path.format(id=t.id))
        self.verify_response(response,
                             ignore_values=[str(self.system_sales_account.id)])

    def test_no_such_transaction(self):
        response = self.get(self.path.format(id='7390109f-7103-4777-84f0-89e7deff382a'))
        self.verify_response(response)


class TransactionReverseTest(APIView0TestCaseBase):

    path = "v0/transaction/{id}/reverse"

    def _post_and_verify(self, object_id, variant=None,
                         status_code=http.client.CREATED):
        path = self.path.format(id=object_id)
        response = super(TransactionReverseTest, self).post(path)
        value = response.json()
        ignore_values = []
        if status_code == http.client.CREATED:
            ignore_values = [value['transaction_id']]
        self.verify_response(response,
                             ignore_values=ignore_values,
                             variant=variant,
                             frame=2)
        if status_code == http.client.CREATED:
            assert 'transaction_id' in value, response.data
            transaction = Transaction.get_by_id(value['transaction_id'])
            assert transaction.state == Transaction.STATE_PENDING
            assert transaction.origin == Transaction.ORIGIN_REVERSAL
            return transaction
        return value

    def test_post(self):
        transaction = TransactionFactory(user=self.user)
        transaction.from_wallet.value = 100
        transaction.process()
        self.session.commit()
        self._post_and_verify(transaction.id)

    def test_post_external_id(self):
        transaction = TransactionFactory(user=self.user, external_id='external-id')
        transaction.from_wallet.value = 100
        transaction.process()
        self.session.commit()
        self._post_and_verify('external-id', variant='external-id')

    def test_post_external_id_uuid(self):
        transaction = TransactionFactory(user=self.user,
                                         external_id='a6b794be-d1aa-41f3-b920-546260a6068e')
        transaction.from_wallet.value = 100
        transaction.process()
        self.session.commit()
        self._post_and_verify('a6b794be-d1aa-41f3-b920-546260a6068e', variant='external-id-uuid')

    def test_post_error_not_found(self):
        self._post_and_verify('7390109f-7103-4777-84f0-89e7deff382a',
                              variant='no-such-transaction-bad-uuid',
                              status_code=http.client.NOT_FOUND)
        self._post_and_verify('invalid-external-id',
                              variant='no-such-transaction-external-id',
                              status_code=http.client.NOT_FOUND)

    def test_post_error_pending(self):
        transaction = TransactionFactory(
            user=self.user,
            state=Transaction.STATE_PENDING)
        self.session.commit()
        self._post_and_verify(transaction.id, variant='pending',
                              status_code=http.client.UNPROCESSABLE_ENTITY)

    def test_post_error_reversed(self):
        transaction = TransactionFactory(
            user=self.user,
            state=Transaction.STATE_REVERSED)
        self.session.commit()
        self._post_and_verify(transaction.id, variant='reversed',
                              status_code=http.client.UNPROCESSABLE_ENTITY)

    def test_post_error_reversal(self):
        transaction = TransactionFactory(
            user=self.user,
            state=Transaction.STATE_PROCESSED,
            origin=Transaction.ORIGIN_REVERSAL)
        self.session.commit()
        self._post_and_verify(transaction.id, variant='reversal',
                              status_code=http.client.UNPROCESSABLE_ENTITY)

    @mock.patch('sparkmeter.event.eventdomain.Event.create')
    def test_post_error_already_reversed(self, create):
        create.return_value = EventFactory()
        transaction = TransactionFactory(user=self.user)
        transaction.from_wallet.value = 100
        transaction.process()
        self.session.commit()

        reverse = transaction.reverse(transaction.user)
        self.session.add(reverse)
        self.session.commit()
        reverse.process()
        self.session.commit()
        assert transaction.has_been_reversed()
        assert len(transaction.children) == 1

        self._post_and_verify(transaction.id, variant='already-reversed',
                              status_code=http.client.UNPROCESSABLE_ENTITY)

    def test_post_error_generic(self):
        transaction = TransactionFactory(user=self.user)
        transaction.from_wallet.value = 100
        transaction.process()
        self.session.commit()
        with mock.patch.object(Transaction, 'reverse') as reverse:
            reverse.side_effect = TransactionError(TransactionError.ERROR_WRONG_TYPE,
                                                   u'unhandled error')
            self._post_and_verify(transaction.id,
                                  variant='generic-error',
                                  status_code=http.client.BAD_REQUEST)
            assert reverse.mock_calls == [mock.call(mock.ANY)]
