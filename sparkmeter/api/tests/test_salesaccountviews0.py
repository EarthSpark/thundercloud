# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.test_data_factory import GlobalSalesAccountFactory, SalesAccountFactory
from sparkmeter.transaction.transactiondomain import Transaction


class SalesAccountListTest(APIView0TestCaseBase):
    path = "v0/sales-accounts"

    def test_get(self):
        response = self.get(self.path)
        self.verify_response(response)

    def test_get_restricted(self):
        response = self.get(self.path + "?type=restricted")
        self.verify_response(response)

    def test_get_global(self):
        response = self.get(self.path + "?type=global")
        self.verify_response(response)

    def test_get_invalid_type(self):
        response = self.get(self.path + "?type=wealthy")
        self.verify_response(response)


class SalesAccountGetTest(APIView0TestCaseBase):
    path = "v0/sales-accounts/{}"

    def test_get_restricted(self):
        acct = SalesAccountFactory()
        self.session.commit()
        response = self.get(self.path.format(acct.id))
        self.verify_response(response, ignore_values=[str(acct.id)])

    def test_get_global(self):
        acct = GlobalSalesAccountFactory(name="Captain Planet")
        self.session.commit()
        response = self.get(self.path.format(acct.id))
        self.verify_response(response, ignore_values=[str(acct.id)])

    def test_get_missing(self):
        response = self.get(self.path.format("ffffffff-ffff-ffff-ffff-ffffffffffff"))
        self.verify_response(response)


class SalesAccountPaymentTest(APIView0TestCaseBase):
    path = "v0/sales-accounts/{}/payment"

    def test_successful_transaction_no_markup(self):
        account = GlobalSalesAccountFactory(name="System 2")
        self.user.api_sales_account = account
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        response = self.post(
            self.path.format(recipient.id),
            json={
                "amount": 10,
                "source": "cash",
                "markup": 0,
            },
        )
        response_data = response.json()
        self.verify_response(response, ignore_values=[response_data["transaction_id"]])
        t = Transaction.get_by_id(response_data["transaction_id"])
        assert t.amount == 10
        assert t.source.name == "cash"
        t.process()
        self.session.commit()
        assert recipient.credit_wallet.value == 1010

    def test_successful_transaction_defined_markup(self):
        account = GlobalSalesAccountFactory(name="System 2")
        self.user.api_sales_account = account
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        response = self.post(
            self.path.format(recipient.id),
            json={
                "amount": 10,
                "source": "cash",
                "markup": 0.5,
            },
        )
        response_data = response.json()
        assert response_data.get("bonus_transaction_id") is not None
        self.verify_response(
            response,
            ignore_values=[
                response_data["transaction_id"],
                response_data["bonus_transaction_id"],
            ],
        )
        t = Transaction.get_by_id(response_data["transaction_id"])
        b = Transaction.get_by_id(response_data["bonus_transaction_id"])
        assert b.amount == 5
        assert b.reference_id == t.id
        t.process()
        b.process()
        self.session.commit()
        assert recipient.credit_wallet.value == 1015

    def test_successful_transaction_default_markup(self):
        account = GlobalSalesAccountFactory(name="System 2")
        self.user.api_sales_account = account
        recipient = SalesAccountFactory(markup=0.8, credit_wallet__value=1000)
        self.session.commit()
        response = self.post(
            self.path.format(recipient.id),
            json={
                "amount": 10,
                "source": "cash",
            },
        )
        response_data = response.json()
        assert response_data.get("bonus_transaction_id") is not None
        self.verify_response(
            response,
            ignore_values=[
                response_data["transaction_id"],
                response_data["bonus_transaction_id"],
            ],
        )
        t = Transaction.get_by_id(response_data["transaction_id"])
        b = Transaction.get_by_id(response_data["bonus_transaction_id"])
        assert b.amount == 8
        assert b.reference_id == t.id
        t.process()
        b.process()
        self.session.commit()
        assert recipient.credit_wallet.value == 1018

    def test_successful_transaction_using_bonus(self):
        account = GlobalSalesAccountFactory(name="System 2")
        self.user.api_sales_account = account
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        response = self.post(
            self.path.format(recipient.id),
            json={
                "amount": 10,
                "source": "bonus",
            },
        )
        response_data = response.json()
        assert response_data.get("bonus_transaction_id") is None
        self.verify_response(response, ignore_values=[response_data["transaction_id"]])
        t = Transaction.get_by_id(response_data["transaction_id"])
        assert t.amount == 10
        assert t.source.name == "bonus"
        t.process()
        self.session.commit()
        assert recipient.credit_wallet.value == 1010

    def test_successful_transaction_with_all_parameters(self):
        account = GlobalSalesAccountFactory(name="System 2")
        self.user.api_sales_account = account
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        response = self.post(
            self.path.format(recipient.id),
            json={
                "amount": 10,
                "source": "cash",
                "external_id": "123A",
                "memo": "Note to self",
                "markup": 0,
            },
        )
        response_data = response.json()
        assert response_data.get("bonus_transaction_id") is None
        self.verify_response(response, ignore_values=[response_data["transaction_id"]])
        t = Transaction.get_by_id(response_data["transaction_id"])
        assert t.amount == 10
        assert t.source.name == "cash"
        assert t.external_id == "123A"
        assert t.memo == "Note to self"
        assert t.user == self.user
        assert t.acct_type == "credit"

    def test_negative_payments_no_bonus(self):
        account = SalesAccount.get_system()
        self.user.api_sales_account = account
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        response = self.post(
            self.path.format(recipient.id),
            json={
                "amount": -10,
                "source": "cash",
                "markup": 0,
            },
        )
        response_data = response.json()
        assert response_data.get("bonus_transaction_id") is None
        self.verify_response(response, ignore_values=[response_data["transaction_id"]])
        t = Transaction.get_by_id(response_data["transaction_id"])
        assert t.amount == -10
        assert t.source.name == "cash"
        t.process()
        self.session.commit()
        assert recipient.credit_wallet.value == 990

    def test_invalid_permissions(self):
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.user.api_sales_account.active = False
        self.session.commit()
        path = self.path.format(recipient.id)

        response = self.post(path, json={})
        self.verify_response(response, variant="inactive-sales-account")

        self.user.api_sales_account = None
        self.session.commit()
        response = self.post(path, json={})
        self.verify_response(response, variant="no-sales-account")

    def test_missing_recipient(self):
        response = self.post(self.path.format("ffffffff-ffff-ffff-ffff-ffffffffffff"))
        self.verify_response(response)

    def test_missing_amount(self):
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        response = self.post(self.path.format(recipient.id), json={"source": "cash"})
        self.verify_response(response)

    def test_invalid_amount_types(self):
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        path = self.path.format(recipient.id)

        response = self.post(path, json={"amount": "banana"})
        self.verify_response(response, variant="string")

        response = self.post(path, json={"amount": None})
        self.verify_response(response, variant="null")

        response = self.post(path, json={"amount": ""})
        self.verify_response(response, variant="empty-string")

    def test_missing_source(self):
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        response = self.post(self.path.format(recipient.id), json={"amount": 12})
        self.verify_response(response)

    def test_invalid_source_name(self):
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        response = self.post(self.path.format(recipient.id), json={"amount": 12, "source": "plastic"})
        self.verify_response(response)

    def test_invalid_markup_types(self):
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        path = self.path.format(recipient.id)

        response = self.post(path, json={"amount": 2, "source": "cash", "markup": "banana"})
        self.verify_response(response, variant="string")

        response = self.post(path, json={"amount": 2, "source": "cash", "markup": None})
        self.verify_response(response, variant="null")

        response = self.post(path, json={"amount": 2, "source": "cash", "markup": ""})
        self.verify_response(response, variant="empty-string")

    def test_disallow_targeting_global_accounts(self):
        account = GlobalSalesAccountFactory(name="System 2")
        self.user.api_sales_account = account
        self.session.commit()
        recipient = SalesAccount.get_system()
        response = self.post(
            self.path.format(recipient.id),
            json={
                "amount": 10,
                "source": "cash",
            },
        )
        self.verify_response(response)

    def test_handle_transaction_errors(self):
        account = SalesAccount.get_system()
        self.user.api_sales_account = account
        recipient = SalesAccountFactory(credit_wallet__value=1000)
        self.session.commit()
        response = self.post(
            self.path.format(recipient.id),
            json={
                "amount": 10,
                "source": "cash",
                "markup": 2,
            },
        )
        self.verify_response(response, variant="markup-out-of-range")
        response = self.post(
            self.path.format(recipient.id),
            json={
                "amount": -10,
                "source": "cash",
                "markup": 0.3,
            },
        )
        self.verify_response(response, variant="markup-with-negative-tx")
