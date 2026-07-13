# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.

from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import SalesAccountFactory
from sparkmeter.transaction.transactiondomain import Wallet


class ModelsTest(SparkMeterTestCaseBase):
    def test_get_one_or_create(self):
        account = SalesAccountFactory()
        created, w = Wallet.get_one_or_create(
            session=self.session,
            wallet_type="acct_credit",
            sales_account_id=account.id,
            grid_id=account.ground.id,
        )
        w.value = 0.0
        self.session.add(w)
        self.session.commit()
        result = Wallet.get_one_or_create(
            session=self.session,
            wallet_type="acct_credit",
            sales_account_id=account.id,
            grid_id=account.ground.id,
        )
        created2 = result.created
        w2 = result.object
        w2.value = 0.0
        self.session.add(w2)
        self.session.commit()

        assert created
        assert not created2
        assert w == w2
