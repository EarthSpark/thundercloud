# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Unittest for demo example creation."""

from builtins import str
from unittest import mock

import pytest

from sparkmeter.database.demodata import DemoExamples
from sparkmeter.exceptions import MeterError
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterdomain import Address, Meter
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource
from sparkmeter.user.userdomain import SalesAccountsUsers, User


class DemoExamplesTest(SparkMeterTestCaseBase):
    def test_examples(self, config):
        d = DemoExamples(self.session)
        d.create_ground(name="name", serial="serial", secret_key="secret-key")
        config.update(DEMO_METERS=[dict(serial="SM15R-01-00000000", name="customer name", amount=10)])
        d.create_all()

        assert Address.query.count() == 3
        assert Meter.query.count() == 1
        m = Meter.query.one()
        assert m.customer.name == "customer name"
        assert Ground.query.count() == 2
        ms = Ground.get_all()
        assert ms[1].name == "name"
        assert ms[1].serial == "serial"
        assert ms[1].private.secret_key == "secret-key"
        assert SalesAccount.query.count() == 4
        assert SalesAccountsUsers.query.count() == 6
        assert Tariff.query.count() == 4
        # There are 3 transactions that have been processed when
        # creating 3 sales accounts. The transactions that have
        # been placed with meters have not been processed
        # and therefore are not counted here.
        assert Transaction.query.count() == 3
        assert TransactionSource.query.count() == 2
        assert User.query.count() == 4

    def test_create_meter_with_code(self, config):
        d = DemoExamples(self.session)
        d.ground = self.ground
        config.update(DEMO_METERS=[dict(code=123), dict(code=1509)])
        d.create_all()

        ms = Meter.query.order_by(Meter.serial)
        assert ms[0].serial == "SM15R-01-0000007B"
        assert ms[0].code == 123
        assert ms[1].serial == "SM20R-01-000005E5"
        assert ms[1].code == 1509

    def test_create_meter_with_address(self, config):
        d = DemoExamples(self.session)
        d.ground = self.ground
        config.update(
            DEMO_METERS=[
                dict(
                    serial="SM15R-01-00000000",
                    address=["street1", "street2", "city", "state", "country", "postalcode", "coords"],
                )
            ]
        )
        d.create_all()
        ms = Meter.query.order_by(Meter.serial)
        assert ms[0].serial == "SM15R-01-00000000"
        assert ms[0].address.street1 == "street1"
        assert ms[0].address.street2 == "street2"
        assert ms[0].address.city == "city"
        assert ms[0].address.state == "state"
        assert ms[0].address.country == "country"
        assert ms[0].address.postalcode == "postalcode"
        assert ms[0].address.coords == "coords"

    def test_examples_bad_demo_meters(self, config):
        d = DemoExamples(self.session)
        d.ground = self.ground
        config.update(DEMO_METERS=[{}])
        with pytest.raises(TypeError) as ctx:
            d.create_all()
        assert str(ctx.value) == "Must provide a serial or code"

    def test_examples_invalid_meter_serial(self, config):
        d = DemoExamples(self.session)
        d.ground = self.ground
        config.update(DEMO_METERS=[dict(serial="invalid-serial")])
        with pytest.raises(MeterError) as ctx:
            d.create_all()
        assert str(ctx.value) == "serial invalid-serial is not a valid meter serial"

    def test_examples_duplicated_meters(self, config):
        d = DemoExamples(self.session)
        d.ground = self.ground
        config.update(DEMO_METERS=[dict(serial="SM15R-01-00000000"), dict(serial="SM15R-01-00000000")])
        with pytest.raises(MeterError) as ctx:
            d.create_all()
        assert ctx.value.message == "meter with serial SM15R-01-00000000 already exists"

    def test_examples_with_password(self, config, mocker):
        hash_password = mocker.patch("sparkmeter.database.demodata.hash_password")
        hash_password.return_value = "encrypted"
        d = DemoExamples(self.session)
        d.ground = self.ground
        config.update(DEMO_PASSWORD="foobar", DEMO_METERS=[])
        d.create_all()
        u = User.get_by_name("api")
        assert u.password == "encrypted"
        assert hash_password.mock_calls == [mock.call("foobar")] * 4
