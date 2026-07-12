# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import datetime
import urllib.parse
from builtins import str
from unittest import mock

import pytest
from sqlalchemy.orm import load_only

from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import (
    EventFactory,
    GroundFactory,
    MeterFactory,
    OperatorFactory,
    SalesAccountFactory,
    TransactionFactory,
    TransactionSourceFactory,
    VendorFactory,
)
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource


@pytest.fixture(scope="module", autouse=True)
def _setup(app):
    with mock.patch.dict(app.config, dict(HEROKU=False)):
        yield


class TransactionViewTest(WebViewTestCaseBase):
    def _get_ignore_values(self):
        query = self.session.query(TransactionSource).options(load_only(TransactionSource.id))
        return [str(ts.id) for ts in query]

    def test_add(self, client):
        path = "/meter/SM15R-01-00000001/transaction"

        MeterFactory(serial="SM15R-01-00000001", credit_wallet__value=5, debt_wallet__value=1)
        source = TransactionSourceFactory(name=TransactionSource.CASH)
        account = SalesAccountFactory(credit_wallet__value=20, debt_wallet__value=22)
        self.user.accounts = [account, self.system_sales_account]
        self.session.commit()

        response = client.get(path)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

        data = {
            "amount": 10.0,
            "account": account.id,
            "acct_type": "credit",
            "source": source.id,
        }
        response = client.post(path, data=data)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, variant="post", ignore_values=ignore_values)

        transaction = Transaction.query.one()
        assert transaction.amount == 10
        assert transaction.from_wallet.sales_account.id == account.id
        assert transaction.acct_type == "credit"
        assert transaction.source_id == source.id

    def test_add_debt(self, client):
        path = "/meter/SM15R-01-00000001/transaction"

        MeterFactory(serial="SM15R-01-00000001", credit_wallet__value=12, debt_wallet__value=21)
        source = TransactionSourceFactory(name=TransactionSource.CASH)
        account = SalesAccountFactory(credit_wallet__value=20, debt_wallet__value=10)
        self.user.accounts = [account, self.system_sales_account]
        self.session.commit()

        response = client.get(path)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

        data = {
            "amount": 10.0,
            "account": account.id,
            "acct_type": "debt",
            "source": source.id,
        }
        response = client.post(path, data=data)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, variant="post", ignore_values=ignore_values)

        transaction = Transaction.query.one()
        assert transaction.amount == 10
        assert transaction.to_wallet.sales_account_id == account.id
        assert transaction.acct_type == "debt"
        assert transaction.source_id == source.id

    def test_add_debt_error(self, client):
        path = "/meter/SM15R-01-00000001/transaction"

        MeterFactory(serial="SM15R-01-00000001", credit_wallet__value=12, debt_wallet__value=1)
        source = TransactionSourceFactory(name=TransactionSource.CASH)
        account = SalesAccountFactory(credit_wallet__value=20, debt_wallet__value=10)
        self.user.accounts = [account, self.system_sales_account]
        self.session.commit()

        data = {
            "amount": 10.0,
            "account": account.id,
            "acct_type": "debt",
            "source": source.id,
        }
        response = client.post(path, data=data)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

        assert Transaction.query.count() == 0

    def test_add_for_vendor(self, client, vendor_role):
        path = "/meter/SM15R-01-00000001/transaction"

        meter = MeterFactory(serial="SM15R-01-00000001", debt_wallet__value=1)
        source = TransactionSourceFactory(name=TransactionSource.CASH)

        # run tests as a vendor
        account = SalesAccountFactory(credit_wallet__value=20)
        vendor = VendorFactory(roles=[vendor_role], accounts=[account, self.system_sales_account])
        vendor.grounds.append(meter.ground)
        self.session.commit()
        client.login_as(vendor)

        response = client.get(path)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

        data = {
            "amount": 10.0,
            "account": account.id,
            "acct_type": "credit",
            "source": source.id,
        }
        response = client.post(path, data=data)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, variant="post", ignore_values=ignore_values)

        transaction = Transaction.query.one()
        assert transaction.amount == 10
        assert transaction.from_wallet.sales_account_id == account.id
        assert transaction.acct_type == "credit"
        assert transaction.source_id == source.id

    def test_add_meter_not_found(self, client):
        path = "/meter/invalid-meter-serial/transaction"
        response = client.get(path)
        self.verify_response(response)

    def test_add_forbidden(self, client, vendor_role):
        meter = MeterFactory()
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)

        path = "/meter/" + meter.serial + "/transaction"
        response = client.get(path)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

    def test_add_from_disabled_account(self, client, vendor_role):
        path = "/meter/SM15R-01-00000001/transaction"

        MeterFactory(serial="SM15R-01-00000001", credit_wallet__value=5, debt_wallet__value=1)
        source = TransactionSourceFactory(name=TransactionSource.CASH)
        account = SalesAccountFactory(credit_wallet__value=20, debt_wallet__value=22, active=False)
        self.user.accounts = [account, self.system_sales_account]
        self.session.commit()

        response = client.get(path)
        ignore_values = self._get_ignore_values()
        ignore_values.extend(
            [
                str(account.id),
                str(self.system_sales_account.id),
                "ThunderCloud",
                "GroundBolt",
            ]
        )
        self.verify_response(response, ignore_values=ignore_values)

        data = {
            "amount": 10.0,
            "account": account.id,
            "acct_type": "credit",
            "source": source.id,
        }
        response = client.post(path, data=data)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, variant="post", ignore_values=ignore_values)

        assert Transaction.query.count() == 0

    def test_transfer(self, client, vendor_role):
        account = SalesAccountFactory(credit_wallet__value=1000.0)
        source = TransactionSourceFactory(name=TransactionSource.CASH)
        vendor = VendorFactory(
            roles=[vendor_role], accounts=[account, self.system_sales_account], grounds=[self.ground]
        )
        client.login_as(vendor)
        self.session.commit()
        self.system_sales_account.check_can_sell_from(vendor)
        account.check_can_sell_to(vendor)

        url_path = "/sales-account/transfer"
        qs = urllib.parse.urlencode(
            dict(from_account_id=str(self.system_sales_account.id), to_account_id=str(account.id))
        )
        response = client.get(url_path, query_string=qs)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

        data = {
            "acct_type": "credit",
            "source": source.id,
        }
        response = client.post(url_path, data=data, query_string=qs)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, variant="post", ignore_values=ignore_values)

    def test_transfer_from_account_not_found(self, client, vendor_role):
        account = SalesAccountFactory()
        vendor = VendorFactory(roles=[vendor_role], accounts=[account, self.system_sales_account])
        client.login_as(vendor)
        self.session.commit()
        url_path = "/sales-account/transfer"
        qs = urllib.parse.urlencode(
            dict(from_account_id="39a60543-5554-47f5-9107-ae8ea1bf53fe", to_account_id=str(account.id))
        )
        response = client.get(url_path, query_string=qs)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

    def test_transfer_to_account_not_found(self, client, vendor_role):
        vendor = VendorFactory(roles=[vendor_role], accounts=[self.system_sales_account])
        client.login_as(vendor)
        self.session.commit()
        url_path = "/sales-account/transfer"
        qs = urllib.parse.urlencode(
            dict(
                from_account_id=str(self.system_sales_account.id),
                to_account_id="39a60543-5554-47f5-9107-ae8ea1bf53fe",
            )
        )
        response = client.get(url_path, query_string=qs)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

    def test_transfer_debt_error(self, client, vendor_role):
        account = SalesAccountFactory()
        vendor = VendorFactory(
            roles=[vendor_role], accounts=[account, self.system_sales_account], grounds=[self.ground]
        )
        client.login_as(vendor)
        self.session.commit()

        url_path = "/sales-account/transfer"
        qs = urllib.parse.urlencode(
            dict(from_account_id=str(self.system_sales_account.id), to_account_id=str(account.id))
        )
        response = client.get(url_path, query_string=qs)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

        source = TransactionSourceFactory()
        self.session.commit()
        data = {
            "amount": 10.0,
            "acct_type": "debt",
            "source": source.id,
        }
        response = client.post(url_path, data=data, query_string=qs)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(account.id), str(self.system_sales_account.id)])
        self.verify_response(response, variant="post", ignore_values=ignore_values)

    def test_transfer_account_not_found(self, client):
        path = "/sales-account/00000000-0000-0000-0000-000000000000/transaction"
        response = client.get(path)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

    def test_transaction_transfer_forbidden(self, client, vendor_role):
        account = SalesAccountFactory()
        vendor = VendorFactory(roles=[vendor_role])
        self.session.commit()
        client.login_as(vendor)

        path = "/sales-account/transfer"
        qs = urllib.parse.urlencode(
            dict(from_account_id=str(self.system_sales_account.id), to_account_id=str(account.id))
        )
        response = client.get(path, query_string=qs)
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

    def test_reverse(self, client, send_set_config):
        path = "/transaction/%s/reverse"
        transaction = self.create_transaction(user=self.user)
        self.session.flush()
        transaction.from_wallet.value = 100
        transaction.process()
        self.session.commit()

        response = client.get(path % (transaction.id,))
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)
        assert len(Transaction.get_all()) == 2
        assert transaction.state == Transaction.STATE_PROCESSED
        assert len(transaction.children) == 1
        reverse = transaction.children[0]
        assert reverse.state == Transaction.STATE_PENDING
        assert reverse.origin == Transaction.ORIGIN_REVERSAL
        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac="1",
                command="enable",
                balance=100.0,
                low_balance=False,
                firmware_version="abc1234",
            ),
        ]

    def test_reverse_not_found(self, client):
        path = "/transaction/%s/reverse"
        response = client.get(path % ("44769678-0003-4a63-94d8-1be7a417216a",))
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)

    def test_reverse_not_processed(self, client):
        path = "/transaction/%s/reverse"
        transaction = TransactionFactory()
        transaction.from_wallet.value = 100
        self.session.commit()

        response = client.get(path % (transaction.id,))
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)
        assert transaction.state == Transaction.STATE_PENDING
        assert len(transaction.children) == 0

    def test_reverse_already_reversed(self, client, mocker, send_set_config):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        path = "/transaction/%s/reverse"
        transaction = self.create_transaction()
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

        response = client.get(path % (transaction.id,))
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        self.verify_response(response, ignore_values=ignore_values)
        assert transaction.state == Transaction.STATE_REVERSED
        assert len(transaction.children) == 1
        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                mac="1",
                load_limit=50.0,
                command="enable",
                balance=100.0,
                low_balance=False,
                firmware_version="abc1234",
            ),
            mock.call(
                subnet=255,
                current_limit=10000.0,
                mac=1,
                load_limit=50.0,
                command="disable",
                balance=0,
                low_balance=True,
                firmware_version="abc1234",
            ),
        ]
        assert event_create.mock_calls == [
            mock.call("reversal-transaction-processed", obj=mock.ANY),
        ]

    def test_transaction_json(self, client, config, operator_role):
        other = GroundFactory()
        self.session.commit()

        TransactionFactory(
            acct_type="credit",
            created=datetime.datetime(2010, 1, 1),
            from_wallet=self.system_sales_account.credit_wallet,
            memo="credit grid#1",
        )
        TransactionFactory(
            acct_type="debt",
            created=datetime.datetime(2010, 1, 2),
            from_wallet=self.system_sales_account.debt_wallet,
            memo="debt grid#1",
        )

        TransactionFactory(
            acct_type="credit",
            created=datetime.datetime(2012, 2, 1),
            from_wallet=self.system_sales_account.credit_wallet,
            ground=other,
            memo="credit grid#2",
        )
        TransactionFactory(
            acct_type="debt",
            created=datetime.datetime(2012, 2, 2),
            from_wallet=self.system_sales_account.debt_wallet,
            ground=other,
            memo="debt grid#2",
        )
        self.session.commit()

        users = [
            OperatorFactory(roles=[operator_role], username="none", grounds=[]),
            OperatorFactory(roles=[operator_role], username="only-1", grounds=[self.ground]),
            OperatorFactory(roles=[operator_role], username="only-2", grounds=[other]),
            OperatorFactory(roles=[operator_role], username="all", grounds=[self.ground, other]),
        ]
        self.session.commit()
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        for params in [
            dict(HEROKU=True),
            dict(HEROKU=False, SERIAL=self.ground.serial),
            dict(HEROKU=False, SERIAL=other.serial),
        ]:
            if params.get("SERIAL") == self.ground.serial:
                where = "ground1"
            elif params.get("SERIAL") == other.serial:
                where = "ground2"
            else:
                where = "cloud"
            for user in users:
                config.update(**params)
                client.login_as(user)
                path = "/transaction/transactions.json"
                response = client.get(path)
                variant = "%s-%s" % (where, user.username)
                self.verify_response(response, variant=variant, ignore_values=ignore_values)

    def test_transactions_json_datatables_computed_data_field_sort(self, client, config):
        path = "/transaction/transactions.json"
        TransactionFactory(
            acct_type="credit",
            created=datetime.datetime(2010, 1, 1),
            from_wallet=self.system_sales_account.credit_wallet,
            memo="credit",
        )
        TransactionFactory(
            acct_type="debt",
            created=datetime.datetime(2010, 1, 2),
            from_wallet=self.system_sales_account.debt_wallet,
            memo="debt",
        )
        self.session.commit()
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        response = client.get(path + "?order[0][column]=0&columns[0][data]=3")
        self.verify_response(response, ignore_values=ignore_values)

    def test_transactions_json_datatables_bad_sort_column(self, client, config):
        path = "/transaction/transactions.json"
        TransactionFactory(
            acct_type="credit",
            created=datetime.datetime(2010, 1, 1),
            from_wallet=self.system_sales_account.credit_wallet,
            memo="credit",
        )
        TransactionFactory(
            acct_type="debt",
            created=datetime.datetime(2010, 1, 2),
            from_wallet=self.system_sales_account.debt_wallet,
            memo="debt",
        )
        self.session.commit()
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        response = client.get(path + "?order[0][column]=0&columns[0][data]=nonexistentattribute")
        self.verify_response(response, ignore_values=ignore_values)

    def test_transactions_json_datatables_querystring(self, client, config):
        path = "/transaction/transactions.json"
        TransactionFactory(
            acct_type="credit",
            created=datetime.datetime(2010, 1, 1),
            from_wallet=self.system_sales_account.credit_wallet,
            memo="MOTLEY",
        )
        TransactionFactory(
            acct_type="debt",
            created=datetime.datetime(2010, 1, 2),
            from_wallet=self.system_sales_account.debt_wallet,
            memo="LEO",
        )
        self.session.commit()
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        response = client.get(path + "?search[value]=motley&search[regex]=true")
        self.verify_response(response, ignore_values=ignore_values)

    def test_transactions_export(self, client, config):
        path = "/transaction/transactions.csv"
        TransactionFactory(
            acct_type="credit",
            created=datetime.datetime(2010, 1, 1),
            from_wallet=self.system_sales_account.credit_wallet,
            memo="MOTLEY",
        )
        TransactionFactory(
            acct_type="debt",
            created=datetime.datetime(2010, 1, 2),
            from_wallet=self.system_sales_account.debt_wallet,
            memo="LEO",
        )
        self.session.commit()
        ignore_values = self._get_ignore_values()
        ignore_values.extend([str(self.system_sales_account.id)])
        response = client.get(path)
        self.verify_response(response, ignore_values=ignore_values)

    def test_transactions(self, client, config):
        path = "/transaction/transactions"

        TransactionFactory(acct_type="credit", from_wallet=self.system_sales_account.credit_wallet)
        TransactionFactory(acct_type="debt", from_wallet=self.system_sales_account.debt_wallet)
        self.session.commit()
        config["HEROKU"] = False
        response = client.get(path)

        self.verify_response(response)
