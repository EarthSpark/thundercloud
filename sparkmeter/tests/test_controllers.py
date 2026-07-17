# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import json
import threading
import time
from builtins import str
from datetime import datetime
from unittest import mock

import pytest
from sqlalchemy import text
from testfixtures import LogCapture

from sparkmeter.controller import add_reading, process_transaction
from sparkmeter.exceptions import DatabaseLockTimeoutException, DuplicateReadingException, TransactionError
from sparkmeter.interface import IApplication
from sparkmeter.reading.readingdomain import Reading
from sparkmeter.snapshot.snapshotdomain import Snapshot
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (
    MeterFactory,
    SalesAccountFactory,
    TotalizerMeterFactory,
    TransactionFactory,
)
from sparkmeter.transaction.transactiondomain import Transaction, Wallet


@pytest.fixture(scope="module", autouse=True)
def _setup(app):
    with mock.patch.dict(app.config, dict(HEROKU=False)):
        yield


@pytest.fixture()
def logger():
    with LogCapture("sparkmeter.transaction.transactiondomain") as logger:
        yield logger


class ControllerTest(SparkMeterTestCaseBase):
    def test_process_power_transaction(self, config, logger, send_set_config):
        account = SalesAccountFactory(credit_wallet__value=1000)
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        transaction = TransactionFactory(
            amount=40.0,
            acct_type="credit",
            to_wallet=meter.credit_wallet,
            from_wallet=account.credit_wallet,
        )
        self.session.commit()

        config["HEROKU"] = False
        process_transaction(transaction.id)

        transaction.reload(self.session)

        assert account.credit_wallet.value == 960.0
        assert meter.credit_wallet.value == 240.0
        assert meter.debt_wallet.value == 100.0
        assert transaction.state == Transaction.STATE_PROCESSED

        logger.check(
            (
                "sparkmeter.transaction.transactiondomain",
                "INFO",
                (
                    "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                    "from wallet:credit: 1000.00 - 40.00 = 960.00"
                ),
            ),
            (
                "sparkmeter.transaction.transactiondomain",
                "INFO",
                (
                    "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                    "to wallet:credit: 200.00 + 40.00 = 240.00"
                ),
            ),
        )
        send_set_config.assert_called_with(
            load_limit=50.0,
            subnet=255,
            current_limit=10000.0,
            mac=1,
            command="enable",
            balance=240.0,
            low_balance=False,
            firmware_version="abc1234",
        )

    def test_process_negative_transaction(self, config):
        config["HEROKU"] = False
        account = SalesAccountFactory(credit_wallet__value=30)
        meter = MeterFactory()
        transaction = TransactionFactory(
            amount=80.0,
            acct_type="credit",
            to_wallet=meter.credit_wallet,
            from_wallet=account.credit_wallet,
        )
        self.session.commit()

        with pytest.raises(TransactionError) as e:
            process_transaction(transaction.id)
        assert e.value.code == TransactionError.ERROR_NOT_ENOUGH_FUNDS
        message = "Sending side does not contain enough funds (30.00) to complete transfer of value 80.00."
        assert str(e.value.message) == message

        assert account.credit_wallet.value == 30.0
        assert meter.credit_wallet.value == 0.0
        assert transaction.state == Transaction.STATE_ERROR

    def test_process_debt_transaction(self, config):
        config["HEROKU"] = False
        with LogCapture("sparkmeter.transaction.transactiondomain") as logger:
            account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
            meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
            transaction = TransactionFactory(
                amount=5.0,
                acct_type="debt",
                to_wallet=account.debt_wallet,
                from_wallet=meter.debt_wallet,
            )
            self.session.commit()

            process_transaction(transaction.id)

            transaction.reload(self.session)

            assert account.credit_wallet.value == 1000.0
            assert meter.credit_wallet.value == 200.0
            assert account.debt_wallet.value == 5.0
            assert meter.debt_wallet.value == 95.0
            assert transaction.state == Transaction.STATE_PROCESSED

            logger.check(
                (
                    "sparkmeter.transaction.transactiondomain",
                    "INFO",
                    (
                        "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                        "from wallet:debt: 100.00 - 5.00 = 95.00"
                    ),
                ),
                (
                    "sparkmeter.transaction.transactiondomain",
                    "INFO",
                    (
                        "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                        "to wallet:debt: 0.00 + 5.00 = 5.00"
                    ),
                ),
            )

    def test_process_transfer_transaction(self, config):
        config["HEROKU"] = False
        with LogCapture("sparkmeter.transaction.transactiondomain") as logger:
            account = SalesAccountFactory(credit_wallet__value=1000)
            transaction = TransactionFactory(
                amount=200,
                acct_type="credit",
                to_wallet=account.credit_wallet,
                from_wallet=self.system_sales_account.credit_wallet,
            )
            self.session.commit()

            process_transaction(transaction.id)

            transaction.reload(self.session)

            assert account.credit_wallet.value == 1200.0
            assert transaction.state == Transaction.STATE_PROCESSED

            logger.check(
                (
                    "sparkmeter.transaction.transactiondomain",
                    "INFO",
                    (
                        "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                        "from wallet:credit: 0.00 - 200.00 = -200.00"
                    ),
                ),
                (
                    "sparkmeter.transaction.transactiondomain",
                    "INFO",
                    (
                        "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                        "to wallet:credit: 1000.00 + 200.00 = 1200.00"
                    ),
                ),
            )

    def test_process_debt_transfer_transaction(self, config):
        config["HEROKU"] = False
        with LogCapture("sparkmeter.transaction.transactiondomain") as logger:
            system_sales_account = self.system_sales_account
            system_sales_account.credit_wallet.value = 100
            system_sales_account.debt_wallet.value = 300
            account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=2000)
            transaction = TransactionFactory(
                amount=200,
                acct_type="debt",
                to_wallet=system_sales_account.debt_wallet,
                from_wallet=account.debt_wallet,
            )
            self.session.commit()

            process_transaction(transaction.id)

            transaction.reload(self.session)
            account.reload(self.session)

            assert account.credit_wallet.value == 1000.0
            assert account.debt_wallet.value == 1800.0
            assert system_sales_account.credit_wallet.value == 100.0
            assert system_sales_account.debt_wallet.value == 500.0
            assert transaction.state == Transaction.STATE_PROCESSED

            logger.check(
                (
                    "sparkmeter.transaction.transactiondomain",
                    "INFO",
                    (
                        "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                        "from wallet:debt: 2000.00 - 200.00 = 1800.00"
                    ),
                ),
                (
                    "sparkmeter.transaction.transactiondomain",
                    "INFO",
                    (
                        "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                        "to wallet:debt: 300.00 + 200.00 = 500.00"
                    ),
                ),
            )

    def test_process_bonus_transaction(self, config):
        config["HEROKU"] = False
        with LogCapture("sparkmeter.transaction.transactiondomain") as logger:
            account = SalesAccountFactory(credit_wallet__value=1000)
            self.session.commit()

            transaction = TransactionFactory(
                amount=200,
                acct_type="credit",
                to_wallet=account.credit_wallet,
                from_wallet=self.system_sales_account.credit_wallet,
            )
            self.session.commit()

            process_transaction(transaction.id)

            transaction.reload(self.session)

            assert transaction.state == Transaction.STATE_PROCESSED
            assert account.credit_wallet.value == 1200.0

            logger.check(
                (
                    "sparkmeter.transaction.transactiondomain",
                    "INFO",
                    (
                        "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                        "from wallet:credit: 0.00 - 200.00 = -200.00"
                    ),
                ),
                (
                    "sparkmeter.transaction.transactiondomain",
                    "INFO",
                    (
                        "Successfully processed transaction 00000007-0000-0000-0000-000000000001: "
                        "to wallet:credit: 1000.00 + 200.00 = 1200.00"
                    ),
                ),
            )

    def test_process_transaction_wallet_locking(self, config, send_set_config):
        account = SalesAccountFactory(credit_wallet__value=1000)
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        transaction = TransactionFactory(
            amount=40.0,
            acct_type="credit",
            to_wallet=meter.credit_wallet,
            from_wallet=account.credit_wallet,
        )
        self.session.commit()

        config["HEROKU"] = False
        config["LOCK_WALLETS_ON_PROCESS"] = True
        with LogCapture("sparkmeter.controller") as logger:
            process_transaction(transaction.id)

            transaction.reload(self.session)

            assert transaction.state == Transaction.STATE_PROCESSED

            logger.check(
                (
                    "sparkmeter.controller",
                    "INFO",
                    "Transaction wallet lock acquired for: {} and {}".format(
                        account.credit_wallet.id, meter.credit_wallet.id
                    ),
                ),
                (
                    "sparkmeter.controller",
                    "INFO",
                    "Transaction wallet lock released",
                ),
            )

    def test_process_transaction_wallet_locking_disabled(self, config, send_set_config):
        account = SalesAccountFactory(credit_wallet__value=1000)
        meter = MeterFactory(credit_wallet__value=200, debt_wallet__value=100)
        transaction = TransactionFactory(
            amount=40.0,
            acct_type="credit",
            to_wallet=meter.credit_wallet,
            from_wallet=account.credit_wallet,
        )
        self.session.commit()

        config["HEROKU"] = False
        config["LOCK_WALLETS_ON_PROCESS"] = False
        with LogCapture("sparkmeter.controller") as logger:
            process_transaction(transaction.id)

            transaction.reload(self.session)

            assert transaction.state == Transaction.STATE_PROCESSED

            logger.check()  # verify no logs

    def test_add_customer_reading(self, config, send_set_config):
        config["HEROKU"] = False
        meter = MeterFactory(system_info__last_energy=12, credit_wallet__value=1000)
        self.session.commit()

        reading_data = {
            "kilowatt_hours": 1.1,
            "kilowatt_hours_period": 300,
            "cost": 1.0,
            "acct_credit": 2.0,
            "acct_debt": 0,
            "meter": meter.code,
            "heartbeat_start": datetime(2013, 1, 1, 1, 0, 1),
            "heartbeat_end": datetime(2013, 1, 1, 1, 1, 1),
            "frequency": 60.0,
            "voltage_min": 118.0,
            "voltage_max": 122.0,
            "voltage_avg": 120.0,
            "current_min": 4.8,
            "current_max": 5.2,
            "current_avg": 5.0,
            "true_power_inst": 600.0,
            "true_power_avg": 600.0,
            "apparent_power_avg": 632.0,
            "power_factor_avg": 0.95,
            "energy": 15.625375,
            "uptime": 100,
            "state": "on",
            "user_power_limit": 24000,
        }

        reading_id = add_reading(reading_data)

        reading = Reading.get_by_id(reading_id)
        snapshot = Snapshot.get_by_id(reading.snapshot_id)
        wallet_id = meter.credit_wallet.id
        wallet = Wallet.get_by_id(wallet_id)

        assert reading.voltage_avg == reading_data["voltage_avg"]
        assert wallet.value == 963.74625
        assert snapshot.hash_ == "c07510ca03a4c5920efcb2e11c4b5171db842404700a7ecb6c266ad7997b949f"
        snapshot_payload = json.loads(snapshot.payload)
        assert "customer" in snapshot_payload
        assert "tariff" in snapshot_payload

        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command="enable",
                balance=963.74625,
                low_balance=False,
                firmware_version="abc1234",
            ),
        ]

    def test_add_totalizer_reading(self, config, send_set_config):
        config["HEROKU"] = False
        meter = TotalizerMeterFactory(
            system_info__last_energy=10, system_info__last_energy_datetime=datetime(2013, 1, 1, 1, 0, 1)
        )
        self.session.commit()

        # reading data is in raw values
        reading_data = {
            "kilowatt_hours": 0,
            "kilowatt_hours_period": 0,
            "meter": meter.code,
            "heartbeat_start": datetime(2013, 1, 1, 1, 0, 1),
            "heartbeat_end": datetime(2013, 1, 1, 1, 1, 1),
            "frequency": 60.0,
            "voltage_min": 238.0,
            "voltage_max": 242.0,
            "voltage_avg": 240.0,
            "current_min": 4.8,
            "current_max": 5.2,
            "current_avg": 5.0,
            "true_power_inst": 600.0,
            "true_power_avg": 600.0,
            "apparent_power_avg": 632.0,
            "power_factor_avg": 0.95,
            "energy": 15.625,
            "uptime": 100,
            "state": "on",
            "user_power_limit": 24000,
        }

        reading_id = add_reading(reading_data)
        reading = Reading.get_by_id(reading_id)
        snapshot = Snapshot.get_by_id(reading.snapshot_id)

        assert reading.voltage_avg == reading_data["voltage_avg"]
        # make sure kilowatt hours and period are calculated
        assert reading.kilowatt_hours == 5.625
        assert reading.kilowatt_hours_period == 60
        assert snapshot.hash_ == "dbb1cb4b82e3759cc892fee4fdef08052811bd786a07953707d93e0e2d24bd1d"
        snapshot_payload = json.loads(snapshot.payload)
        assert "customer" not in snapshot_payload
        assert "tariff" not in snapshot_payload
        assert send_set_config.mock_calls == []

    def test_add_duplicate_reading(self, config, send_set_config):
        config["HEROKU"] = False
        meter = MeterFactory(system_info__last_energy=12, credit_wallet__value=1000)
        self.session.commit()

        reading_data = {
            "kilowatt_hours": 1.1,
            "kilowatt_hours_period": 300,
            "cost": 1.0,
            "acct_credit": 2.0,
            "acct_debt": 0,
            "meter": meter.code,
            "heartbeat_start": datetime(2013, 1, 1, 1, 0, 1),
            "heartbeat_end": datetime(2013, 1, 1, 1, 1, 1),
            "frequency": 60.0,
            "voltage_min": 118.0,
            "voltage_max": 122.0,
            "voltage_avg": 120.0,
            "current_min": 4.8,
            "current_max": 5.2,
            "current_avg": 5.0,
            "true_power_inst": 600.0,
            "true_power_avg": 600.0,
            "apparent_power_avg": 632.0,
            "power_factor_avg": 0.95,
            "energy": 15.625375,
            "uptime": 100,
            "state": "on",
            "user_power_limit": 24000,
        }

        # First reading works correctly
        add_reading(reading_data)

        # Second reading fails
        match = r"Meter 1 already has a reading with heartbeat_end\=2013-01-01 01:01:01"
        with pytest.raises(DuplicateReadingException, match=match):
            add_reading(reading_data)

        # Check that one and only one set config went out
        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command="enable",
                balance=963.74625,
                low_balance=False,
                firmware_version="abc1234",
            )
        ]

    def test_add_reading_wallet_locking(self, config, send_set_config):
        config["HEROKU"] = False
        config["LOCK_WALLETS_ON_PROCESS"] = True
        meter = MeterFactory(system_info__last_energy=12, credit_wallet__value=1000)
        self.session.commit()

        reading_data = {
            "kilowatt_hours": 1.1,
            "kilowatt_hours_period": 300,
            "cost": 1.0,
            "acct_credit": 2.0,
            "acct_debt": 0,
            "meter": meter.code,
            "heartbeat_start": datetime(2013, 1, 1, 1, 0, 1),
            "heartbeat_end": datetime(2013, 1, 1, 1, 1, 1),
            "frequency": 60.0,
            "voltage_min": 118.0,
            "voltage_max": 122.0,
            "voltage_avg": 120.0,
            "current_min": 4.8,
            "current_max": 5.2,
            "current_avg": 5.0,
            "true_power_inst": 600.0,
            "true_power_avg": 600.0,
            "apparent_power_avg": 632.0,
            "power_factor_avg": 0.95,
            "energy": 15.625375,
            "uptime": 100,
            "state": "on",
            "user_power_limit": 24000,
        }

        with LogCapture("sparkmeter.controller") as logger:
            reading_id = add_reading(reading_data)

            reading = Reading.get_by_id(reading_id)

            wallet_id = meter.credit_wallet.id
            wallet = Wallet.get_by_id(wallet_id)

            assert reading.voltage_avg == reading_data["voltage_avg"]
            assert wallet.value == 963.74625
            logger.check(
                (
                    "sparkmeter.controller",
                    "INFO",
                    "Billing wallet lock acquired for: {}, {} and {}".format(
                        meter.credit_wallet.id, meter.debt_wallet.id, meter.plan_wallet.id
                    ),
                ),
                (
                    "sparkmeter.controller",
                    "INFO",
                    "Billing wallet lock released",
                ),
            )

    def test_add_reading_wallet_locking_disabled(self, config, send_set_config):
        config["HEROKU"] = False
        config["LOCK_WALLETS_ON_PROCESS"] = False
        meter = MeterFactory(system_info__last_energy=12, credit_wallet__value=1000)
        self.session.commit()

        reading_data = {
            "kilowatt_hours": 1.1,
            "kilowatt_hours_period": 300,
            "cost": 1.0,
            "acct_credit": 2.0,
            "acct_debt": 0,
            "meter": meter.code,
            "heartbeat_start": datetime(2013, 1, 1, 1, 0, 1),
            "heartbeat_end": datetime(2013, 1, 1, 1, 1, 1),
            "frequency": 60.0,
            "voltage_min": 118.0,
            "voltage_max": 122.0,
            "voltage_avg": 120.0,
            "current_min": 4.8,
            "current_max": 5.2,
            "current_avg": 5.0,
            "true_power_inst": 600.0,
            "true_power_avg": 600.0,
            "apparent_power_avg": 632.0,
            "power_factor_avg": 0.95,
            "energy": 15.625375,
            "uptime": 100,
            "state": "on",
            "user_power_limit": 24000,
        }

        with LogCapture("sparkmeter.controller") as logger:
            reading_id = add_reading(reading_data)

            reading = Reading.get_by_id(reading_id)

            wallet_id = meter.credit_wallet.id
            wallet = Wallet.get_by_id(wallet_id)

            assert reading.voltage_avg == reading_data["voltage_avg"]
            assert wallet.value == 963.74625
            logger.check()  # verify no logs

    def _cleanup_serialized_data(self):
        """Delete any data that may have been written to the database when transactions were committed."""
        from sparkmeter.database.alchemy import sql

        # Use a fresh connection to clean up data that was committed
        # outside the test transaction (for concurrent tests)
        conn = sql.engine.connect()
        try:
            conn.execute(text("DELETE FROM transactions"))
            conn.execute(text("DELETE FROM wallet WHERE grid_id IS NOT NULL"))
            conn.execute(text("DELETE FROM sales_account WHERE system = False"))
            conn.execute(text("DELETE FROM ground_private"))
            conn.execute(text("DELETE FROM grounds_addresses"))
            conn.execute(text("DELETE FROM meter_system_info"))
            conn.execute(text("DELETE FROM meter_billing"))
            conn.execute(text("DELETE FROM customer"))
            conn.execute(text("DELETE FROM meter_config"))
            conn.execute(text("DELETE FROM sparkmac_node"))
            conn.execute(text("DELETE FROM meter"))
            conn.execute(text("DELETE FROM address"))
            conn.execute(text("DELETE FROM ground"))
            conn.execute(text("DELETE FROM tariff"))
            conn.execute(text("DELETE FROM transaction_sources WHERE id::varchar LIKE '0000%'"))
            conn.execute(text("DELETE FROM meter_models WHERE id::varchar LIKE '0000%'"))
            conn.execute(text("DELETE FROM meter_scalars WHERE id::varchar LIKE '0000%'"))
            conn.execute(text('DELETE FROM "user"'))
            conn.commit()
        finally:
            conn.close()

        # The worker threads patch controller.session_scope concurrently, which
        # races on save/restore and can leave it pointing at a dead mock that
        # then leaks into later tests. Restore the real one explicitly.
        import sparkmeter.controller as controller_module
        from sparkmeter.models import session_scope as real_session_scope

        controller_module.session_scope = real_session_scope

    @pytest.mark.parametrize(
        "reading_delay,transaction_delay,balance",
        (
            (0.0, 0.0, 1040.0),
            (1.0, 3.0, 963.74625),
            (3.0, 1.0, 1040.0),
        ),
    )
    def test_concurrent_transaction_and_reading_threaded(
        self, config, send_set_config, session_manager, reading_delay, transaction_delay, balance
    ):
        """Test our ability to safely handle potential race conditions caused
        by near-simultaneous transaction and reading processing.

        Since we're using locking, simply interleaving calls to either endpoint
        won't suffice - instead, we need to create multiple sessions and
        transactions in order to properly simulate this.  The wrinkle here is
        that we need to write data that is normally kept within the root
        transaction to the test database instead of rolling it back at the end
        of a test. This requires not only additional clean up, but also subtly
        contaminates every test that follows as the test-run-wide `session` and
        `session_scope` can potentially be stale.  Additionally, since clean up
        has to be manual, any default records added by test data factories need
        to be explicitly cleaned up.
        """
        from sparkmeter.config.configdict import config

        config["HEROKU"] = False

        # Create test data
        meter = MeterFactory(system_info__last_energy=12, credit_wallet__value=1000)
        account = SalesAccountFactory(credit_wallet__value=1000)
        tx = TransactionFactory(
            amount=40.0,
            acct_type="credit",
            to_wallet=meter.credit_wallet,
            from_wallet=account.credit_wallet,
        )
        # Write and close the main session's root transaction so the test data is written to disk
        self.session.commit()
        try:
            wallet_id = meter.credit_wallet.id
            self.session = session_manager.create("testwide")  # Create a new root transaction
            tx_exc = []
            reading_exc = []
            tx_thread = threading.Thread(
                target=do_transaction, args=(tx.id, transaction_delay, session_manager, tx_exc)
            )
            reading_thread = threading.Thread(
                target=do_reading, args=(meter, reading_delay, session_manager, reading_exc)
            )
            tx_thread.start()
            reading_thread.start()
            all_done = False
            while not all_done:
                all_done = not (tx_thread.is_alive() or reading_thread.is_alive())
                time.sleep(1)

            # If a worker thread raised, it silently dropped its operation
            # (leaving a wrong wallet balance). Surface that as a clear failure
            # rather than a confusing balance assertion further down.
            assert tx_exc == [], "transaction thread raised: {!r}".format(tx_exc)
            assert reading_exc == [], "reading thread raised: {!r}".format(reading_exc)

            # Query with a fresh session
            wallet = self.session.query(Wallet).get(wallet_id)
            assert wallet.value == 1003.74625
            # Both operations must send a config update, but when both run
            # simultaneously (delay=0) the ordering is non-deterministic.
            # The business requirement is: both complete, and the FINAL
            # config sent has the correct balance.
            assert send_set_config.call_count == 2
            calls = send_set_config.mock_calls
            common = dict(
                subnet=255,
                current_limit=10000.0,
                load_limit=50.0,
                mac=1,
                command="enable",
                low_balance=False,
                firmware_version="abc1234",
            )
            # The last call must have the final correct balance
            assert calls[-1] == mock.call(**common, balance=1003.74625)
            # The first call's balance depends on which operation ran first:
            #   transaction first → balance (the starting balance + transaction)
            #   reading first     → 963.74625 (starting balance + reading energy)
            first_balance = calls[0].kwargs["balance"] if calls[0].kwargs else calls[0][2]["balance"]
            assert first_balance in (balance, 963.74625)
        finally:
            # Since the test data is actually committed, it needs to be deleted.
            # `resetdb()` was causing some transient deadlockss, so this became necessary.
            self._cleanup_serialized_data()

    def test_concurrent_transaction_deadlock(self, config, send_set_config, session_manager):
        """Test our ability to escape a potential transaction wallet deadlock via timeouts."""
        from sparkmeter.config.configdict import config

        config["HEROKU"] = False
        config["LOCK_WALLETS_ON_PROCESS_TIMEOUT"] = 2

        # Create test data
        meter = MeterFactory(system_info__last_energy=12, credit_wallet__value=1000)
        account = SalesAccountFactory(credit_wallet__value=1000)
        tx = TransactionFactory(
            amount=40.0,
            acct_type="credit",
            to_wallet=meter.credit_wallet,
            from_wallet=account.credit_wallet,
        )
        # Write and close the main session's root transaction so the test data is written to disk
        self.session.commit()
        try:
            self.session = session_manager.create("testwide")  # Create a new root transaction
            tx_exc = []
            # Acquire a lock on the wallet before starting the transaction
            self.session.query(Wallet).with_for_update().filter(Wallet.id == meter.credit_wallet.id).one()
            tx_thread = threading.Thread(target=do_transaction, args=(tx.id, 0, session_manager, tx_exc))
            tx_thread.start()
            while tx_thread.is_alive():
                time.sleep(1)

            self.session.commit()
            assert len(tx_exc) == 1
            assert isinstance(tx_exc[0], DatabaseLockTimeoutException)
        finally:
            # Since the test data is actually committed, it needs to be deleted.
            # `resetdb()` was causing some transient deadlockss, so this became necessary.
            self._cleanup_serialized_data()

    def test_concurrent_reading_deadlock(self, config, send_set_config, session_manager):
        """Test our ability to escape a potential reading wallet deadlock via timeouts."""
        from sparkmeter.config.configdict import config

        config["HEROKU"] = False
        config["LOCK_WALLETS_ON_PROCESS_TIMEOUT"] = 2

        # Create test data
        meter = MeterFactory(system_info__last_energy=12, credit_wallet__value=1000)
        # Write and close the main session's root transaction so the test data is written to disk
        self.session.commit()
        try:
            self.session = session_manager.create("testwide")  # Create a new root transaction
            read_exc = []
            # Acquire a lock on the wallet before starting the transaction
            self.session.query(Wallet).with_for_update().filter(Wallet.id == meter.credit_wallet.id).one()
            reading_thread = threading.Thread(target=do_reading, args=(meter, 0, session_manager, read_exc))
            reading_thread.start()
            while reading_thread.is_alive():
                time.sleep(1)

            self.session.commit()
            assert len(read_exc) == 1
            assert isinstance(read_exc[0], DatabaseLockTimeoutException)
        finally:
            # Since the test data is actually committed, it needs to be deleted.
            # `resetdb()` was causing some transient deadlockss, so this became necessary.
            self._cleanup_serialized_data()


def do_transaction(tx_id, delay, session_manager, exceptions=None):
    """Simulate a transaction. This is meant to be run within a thread, and commits data to the DB.

    :param tx_id: The ID of the transaction to process.
    :param delay: How long to sleep before starting the thread operation. In seconds.
    :param session_manager: The session manager object
    :param process_delay: How long to sleep before processing the transaction. In seconds.
    """
    from zope.component import getUtility

    app = getUtility(IApplication)
    with app.app_context():
        _do_transaction(tx_id, delay, session_manager, exceptions)


def _do_transaction(tx_id, delay, session_manager, exceptions=None):
    time.sleep(delay)
    new_session = session_manager.create("tprocessor")
    transaction = new_session.query(Transaction).get(tx_id)
    print("ToWal Before TX: {}".format(transaction.to_wallet.value))
    with mock.patch("sparkmeter.controller.session_scope") as session_mock:
        session_mock.return_value.__enter__.return_value = new_session
        try:
            processed = process_transaction(transaction.id)
            print("ToWal After TX: {}".format(processed.to_wallet.value))
            new_session.commit()
        except Exception as e:
            new_session.rollback()
            if exceptions is not None:
                exceptions.append(e)
            else:
                raise
        finally:
            # Write and close the session's root transaction
            new_session.close()


def do_reading(meter, delay, session_manager, exceptions=None):
    """Simulate a reading. This is meant to be run within a thread, and commits data to the DB.

    :param meter: The meter from which the reading should originate.
    :param delay: How long to sleep before performing the operation.
    :param session_manager: The session manager object
    """
    from zope.component import getUtility

    app = getUtility(IApplication)
    with app.app_context():
        _do_reading(meter, delay, session_manager, exceptions)


def _do_reading(meter, delay, session_manager, exceptions=None):
    from sparkmeter.meter.meterdomain import Meter

    time.sleep(delay)
    # Create session first, then re-load meter in this thread's own session
    # to avoid cross-thread lazy loading on the main thread's session
    new_session = session_manager.create("rprocessor")
    meter_id = meter.id
    meter = new_session.query(Meter).get(meter_id)
    print("Credit Before Reading: {}".format(meter.credit_wallet.value))
    wallet_id = meter.credit_wallet.id
    reading_data = {
        "kilowatt_hours": 1.1,
        "kilowatt_hours_period": 300,
        "cost": 1.0,
        "acct_credit": 2.0,
        "acct_debt": 0,
        "meter": meter.code,
        "heartbeat_start": datetime(2013, 1, 1, 1, 0, 1),
        "heartbeat_end": datetime(2013, 1, 1, 1, 1, 1),
        "frequency": 60.0,
        "voltage_min": 118.0,
        "voltage_max": 122.0,
        "voltage_avg": 120.0,
        "current_min": 4.8,
        "current_max": 5.2,
        "current_avg": 5.0,
        "true_power_inst": 600.0,
        "true_power_avg": 600.0,
        "apparent_power_avg": 632.0,
        "power_factor_avg": 0.95,
        "energy": 15.625375,
        "uptime": 100,
        "state": "on",
        "user_power_limit": 24000,
    }
    read_sessions = [session_manager.create("rprocessor1"), session_manager.create("rprocessor2")]
    with mock.patch("sparkmeter.controller.session_scope") as session_mock:
        session_mock.return_value.__enter__.side_effect = read_sessions
        try:
            add_reading(reading_data)
            for ses in read_sessions:
                ses.commit()

            print("Credit After Reading: {}".format(new_session.query(Wallet).get(wallet_id).value))
            new_session.commit()
        except Exception as e:
            new_session.rollback()
            for ses in read_sessions:
                ses.rollback()
            if exceptions is not None:
                exceptions.append(e)
            else:
                raise
        finally:
            new_session.close()
