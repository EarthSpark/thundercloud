# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
from builtins import str

import pytest

from sparkmeter.exceptions import TransactionError
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (
    GroundFactory,
    OperatorFactory,
    SalesAccountFactory,
    UserFactory,
    VendorFactory,
)


class SalesAccountTest(SparkMeterTestCaseBase):
    def test_add_wallet_no_id(self):
        account = SalesAccount()
        account.ground = self.ground
        self.session.add(account)
        assert not account.id
        account.add_wallets()
        assert account.id

    def test_check_can_sell_from_api(self, api_role):
        account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        wrong_account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        user = UserFactory(roles=[api_role])
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_from(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell from sales account 'sales åccöünt 1': "
            "api user is not allowed to sell electricity."
        )
        user.api_sales_account = wrong_account
        self.session.commit()

        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_from(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell from sales account 'sales åccöünt 1': "
            "api user can only sell to 'sales åccöünt 2'."
        )
        user.api_sales_account = account
        self.session.commit()

        account.check_can_sell_from(user)

    def test_check_can_sell_from_operator_cloud_global(self, config, operator_role):
        # Global sales account does not need explicit ground permission
        # Cloud should always allow, no explicit ground access needed
        account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        user = OperatorFactory(grounds=[self.ground], roles=[operator_role])
        self.session.commit()
        config.update(HEROKU=True, SERIAL="")
        account.check_can_sell_from(user)

    def test_check_can_sell_from_operator_cloud_restricted(self, config, operator_role):
        # Global sales account does not need explicit ground permission
        account = SalesAccountFactory(global_account=False)  # type: SalesAccount
        user = OperatorFactory(grounds=[self.ground], roles=[operator_role])
        self.session.commit()
        config.update(HEROKU=True, SERIAL="")
        account.check_can_sell_from(user)

    def test_check_can_sell_from_operator_ground_global(self, config, operator_role):
        # Global sales account does not need explicit ground permission
        account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        user = OperatorFactory(grounds=[self.ground], roles=[operator_role])
        self.session.commit()
        config.update(HEROKU=False, SERIAL=self.ground.serial)
        account.check_can_sell_from(user)

    def test_check_can_sell_from_operator_ground_restricted(self, config, operator_role):
        config.update(HEROKU=False, SERIAL=self.ground.serial)

        # Global sales account does not need explicit ground permission
        account = SalesAccountFactory(global_account=False)  # type: SalesAccount
        user = OperatorFactory(grounds=[self.ground], roles=[operator_role])
        self.session.commit()
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_from(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell from sales account 'sales åccöünt 1': "
            "user is not associated with sales account 'sales åccöünt 1'."
        )

        user.accounts.append(account)
        self.session.commit()

        account.check_can_sell_from(user)

    def test_check_can_sell_from_vendor_cloud_global(self, config, vendor_role):
        # Global sales account does not need explicit ground permission
        # Cloud should always allow, no explicit ground access needed
        account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        user = VendorFactory(grounds=[self.ground], roles=[vendor_role])
        self.session.commit()
        config.update(HEROKU=True, SERIAL="")
        account.check_can_sell_from(user)

    def test_check_can_sell_from_vendor_cloud_restricted(self, config, vendor_role):
        # Cloud should always allow, no explicit ground access needed
        ground = GroundFactory()
        self.session.commit()
        account = SalesAccountFactory(global_account=False, ground=ground)  # type: SalesAccount
        user = VendorFactory(grounds=[], roles=[vendor_role])
        self.session.commit()

        config.update(HEROKU=True, SERIAL="")
        account.check_can_sell_from(user)

    def test_check_can_sell_from_vendor_ground_global(self, config, vendor_role):
        # Global sales account does not need explicit ground permission
        ground = GroundFactory()
        self.session.commit()
        account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        user = VendorFactory(grounds=[], roles=[vendor_role])
        self.session.commit()

        config.update(HEROKU=False, SERIAL=ground.serial)
        account.check_can_sell_from(user)

    def test_check_can_sell_from_vendor_ground_restricted(self, config, vendor_role):
        ground = GroundFactory()
        self.session.commit()
        account = SalesAccountFactory(global_account=False, ground=ground)  # type: SalesAccount
        user = VendorFactory(grounds=[], roles=[vendor_role])
        self.session.commit()

        # Restricted sales accounts needs explicit user access
        config.update(HEROKU=False, SERIAL="some-other-bad-ground")
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_from(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell from sales account 'sales åccöünt 1': "
            "transactions for this sales account can only be placed on ground 'test micrøgrid 2'."
        )

        # Restricted sales accounts needs explicit user access
        config.update(HEROKU=False, SERIAL=ground.serial)
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_from(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell from sales account 'sales åccöünt 1': "
            "user is not associated with sales account 'sales åccöünt 1'."
        )

        user.accounts.append(account)
        self.session.commit()

        # Restricted sales accounts needs explicit ground access
        config.update(HEROKU=False, SERIAL=ground.serial)
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_from(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell from sales account 'sales åccöünt 1': "
            "user is not associated with ground 'test micrøgrid 2'."
        )
        user.grounds.append(ground)
        self.session.commit()

        account.check_can_sell_from(user)

    def test_check_can_sell_to_api(self, api_role):
        account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        user = UserFactory(roles=[api_role], api_sales_account=account)
        self.session.commit()
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "selling to global sales accounts is not permitted."
        )

    def test_check_can_sell_to_api_no_global(self, api_role):
        account = SalesAccountFactory(global_account=False)  # type: SalesAccount
        user = UserFactory(roles=[api_role], api_sales_account=account)
        self.session.commit()
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "API user is not associated with a global sales account."
        )

    def test_check_can_sell_to_global(self, operator_role):
        account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        user = OperatorFactory(roles=[operator_role])
        self.session.commit()
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "selling to global sales accounts is not permitted."
        )

    def test_check_can_sell_to_operator_cloud_restricted(self, config, operator_role):
        ground = GroundFactory()
        self.session.commit()
        account = SalesAccountFactory(global_account=False, ground=ground)  # type: SalesAccount
        user = OperatorFactory(roles=[operator_role])
        self.session.commit()

        config.update(HEROKU=True, SERIAL="")
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with system sales account."
        )
        user.accounts.append(self.system_sales_account)
        self.session.commit()

        account.check_can_sell_to(user)

    def test_check_can_sell_to_operator_ground_restricted(self, config, operator_role):
        ground = GroundFactory()
        self.session.commit()
        account = SalesAccountFactory(global_account=False, ground=ground)  # type: SalesAccount
        user = OperatorFactory(roles=[operator_role])
        self.session.commit()

        # Restricted sales accounts needs explicit user access
        config.update(HEROKU=False, SERIAL="some-other-bad-ground")
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "transactions for this sales account can only be placed on ground 'test micrøgrid 2'."
        )

        # Restricted sales accounts needs explicit user access
        config.update(HEROKU=False, SERIAL=ground.serial)
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with system sales account."
        )

        user.accounts.append(self.system_sales_account)
        self.session.commit()

        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with sales account 'sales åccöünt 1'."
        )

        user.accounts.append(account)
        self.session.commit()

        # Restricted sales accounts needs explicit ground access
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with ground 'test micrøgrid 2'."
        )

        user.grounds.append(ground)
        self.session.commit()

        account.check_can_sell_to(user)

    def test_check_can_sell_to_vendor_cloud_restricted(self, config, vendor_role):
        ground = GroundFactory()
        self.session.commit()
        account = SalesAccountFactory(global_account=False, ground=ground)  # type: SalesAccount
        user = VendorFactory(grounds=[], roles=[vendor_role])
        self.session.commit()

        config.update(HEROKU=True, SERIAL="")
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with system sales account."
        )

        user.accounts.append(self.system_sales_account)
        self.session.commit()

        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with sales account 'sales åccöünt 1'."
        )

        user.accounts.append(account)
        self.session.commit()

        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with ground 'test micrøgrid 2'."
        )

        user.grounds.append(ground)
        self.session.commit()

        account.check_can_sell_to(user)

    def test_check_can_sell_to_vendor_ground_restricted(self, config, vendor_role):
        ground = GroundFactory()
        self.session.commit()
        account = SalesAccountFactory(global_account=False, ground=ground)  # type: SalesAccount
        user = VendorFactory(grounds=[], roles=[vendor_role])
        self.session.commit()

        # Restricted sales accounts needs explicit user access
        config.update(HEROKU=False, SERIAL="some-other-bad-ground")
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "transactions for this sales account can only be placed on ground 'test micrøgrid 2'."
        )

        # Restricted sales accounts needs explicit user access
        config.update(HEROKU=False, SERIAL=ground.serial)
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with system sales account."
        )

        user.accounts.append(self.system_sales_account)
        self.session.commit()

        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with sales account 'sales åccöünt 1'."
        )

        user.accounts.append(account)
        self.session.commit()

        # Restricted sales accounts needs explicit ground access
        with pytest.raises(TransactionError) as exc_info:
            account.check_can_sell_to(user)
        assert str(exc_info.value) == (
            "user 'testüser-001' cannot sell to sales account 'sales åccöünt 1': "
            "user is not associated with ground 'test micrøgrid 2'."
        )

        user.grounds.append(ground)
        self.session.commit()

        account.check_can_sell_to(user)

    def test_remove(self, api_role):
        account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        self.session.commit()
        account.remove()
        self.session.commit()

        account = SalesAccountFactory(global_account=True)  # type: SalesAccount
        self.session.commit()
        user = UserFactory(roles=[api_role])
        user.api_sales_account = account
        self.session.commit()
        account.remove()
        self.session.commit()
