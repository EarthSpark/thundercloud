# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
from unittest import mock

from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import TransactionFactory
from sparkmeter.transaction.transactiondomain import Transaction


class TransactionCommandTest(SparkMeterTestCaseBase):
    def test_process(self, cli, config, mocker, scoped_session):
        update_meter = mocker.patch("sparkmeter.meter.meterdomain.send_set_config")

        t1 = TransactionFactory()
        t1.from_wallet.value = 200
        t2 = TransactionFactory()
        self.session.commit()

        assert t1.state == Transaction.STATE_PENDING
        assert t2.state == Transaction.STATE_PENDING
        config["HEROKU"] = False
        with mock.patch("sparkmeter.controller.session_scope", scoped_session):
            cli("transaction", "process")
        assert t1.state == Transaction.STATE_PROCESSED
        assert t2.state == Transaction.STATE_PROCESSED
        assert update_meter.called
