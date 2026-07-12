# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.

from unittest import mock

import pytest
import sqlalchemy
from sqlalchemy import text
from testfixtures import LogCapture

from sparkmeter.database.alchemy import sql
from sparkmeter.database.databasecommand import (
    clean_tables,
    cloud_finish_merge,
    cloud_start_merge,
    force_table_reload,
)
from sparkmeter.database.symmetricdsdomain import (
    Channel,
    Conflict,
    Node,
    NodeGroup,
    NodeGroupLink,
    NodeIdentity,
    Router,
    Trigger,
    TriggerRouter,
)
from sparkmeter.event.eventdomain import Event
from sparkmeter.interface import IApplication
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (
    EventFactory,
    GroundFactory,
    MeterFactory,
    OperatorFactory,
    SalesAccountFactory,
    SMSMessageFactory,
    UserFactory,
)
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource, Wallet


@pytest.fixture()
def logger():
    with LogCapture(("sparkmeter.database.database", "sparkmeter.database.databasecommand")) as logger:
        yield logger


@pytest.fixture()
def getUtility(mocker):
    yield mocker.patch("sparkmeter.database.databasecommand.getUtility", autospec=True, spec_set=True)


@pytest.fixture()
def create_default_policy(mocker):
    yield mocker.patch("sparkmeter.database.sync.create_default_policy", autospec=True, spec_set=True)


@pytest.fixture()
def force_table_reload_mock(mocker):
    yield mocker.patch("sparkmeter.database.sync.force_table_reload", autospec=True, spec_set=True)


@pytest.fixture()
def resetdb(mocker):
    yield mocker.patch("sparkmeter.controller.resetdb", autospec=True, spec_set=True)


@pytest.fixture()
def DemoExamples(mocker):
    yield mocker.patch("sparkmeter.database.demodata.DemoExamples", autospec=True, spec_set=True)


class DatabaseCommandTest(SparkMeterTestCaseBase):
    def test_reset(self, cli, resetdb, getUtility):
        cli("database", "reset")

        assert getUtility.mock_calls == [
            mock.call(IApplication),
            mock.call().setup_databases(),
        ]
        assert resetdb.mock_calls == [mock.call(resetschema=True, force=False, empty=False)]

    def test_reset_demo(self, cli, config, DemoExamples, resetdb, getUtility):
        config.clear()
        config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        cli("database", "reset-demo")
        # When ENABLE_DEMO_RESET is not set, nothing happens
        assert resetdb.mock_calls == []

        config["ENABLE_DEMO_RESET"] = True
        cli("database", "reset-demo", "--serial", "serial", "--sparkcloud-api-key", "secret-key")
        assert getUtility.mock_calls == [
            mock.call(IApplication),
            mock.call().setup_databases(),
        ]
        assert resetdb.mock_calls == [mock.call(force=True, resetschema=True)]
        assert DemoExamples.mock_calls == [
            mock.call(mock.ANY),
            mock.call().create_ground(secret_key="secret-key", serial="serial", name=None),
            mock.call().create_all(),
        ]

    def test_init_sync(self, cli, create_default_policy, config, getUtility):
        config["SERIAL"] = "serial"
        cli("database", "init-sync")
        assert getUtility.mock_calls == [
            mock.call(IApplication),
            mock.call().setup_databases(),
        ]
        assert create_default_policy.mock_calls == [mock.call(mock.ANY, external_id="serial")]

    def test_init_sync_external_id(self, cli, create_default_policy, getUtility):
        cli("database", "init-sync", "--external-id", "external_id")
        assert getUtility.mock_calls == [
            mock.call(IApplication),
            mock.call().setup_databases(),
        ]
        assert create_default_policy.mock_calls == [mock.call(mock.ANY, external_id="external_id")]

    def test_force_table_reload(self, force_table_reload_mock, getUtility):
        force_table_reload("my_table", "my_channel", "my node id")
        assert getUtility.mock_calls == [
            mock.call(IApplication),
            mock.call().setup_databases(),
        ]
        assert force_table_reload_mock.mock_calls == [
            mock.call("my_table", "my node id", "my_channel", mock.ANY)
        ]
        assert isinstance(force_table_reload_mock.call_args[0][3], sqlalchemy.orm.scoped_session)

    def test_clean_tables(self, logger, getUtility):
        clean_tables(force=True, keep_ground=None, keep_user=None)

        assert getUtility.mock_calls == [mock.call(IApplication), mock.call().setup_databases()]
        logger.check(
            ("sparkmeter.database.databasecommand", "INFO", "Cleaned up database tables"),
        )
        logger.clear()
        getUtility.reset_mock()

        clean_tables(force=True, keep_ground=None, keep_user=None)

        assert getUtility.mock_calls == [mock.call(IApplication), mock.call().setup_databases()]
        logger.check(("sparkmeter.database.databasecommand", "INFO", "Cleaned up database tables"))

    def test_clean_tables_no_force(self, logger):
        clean_tables(force=False, keep_ground=None, keep_user=None)
        logger.check(
            (
                "sparkmeter.database.databasecommand",
                "WARNING",
                "This is a dangerous command to run, pass in --force if you know what you are doing",
            ),
        )

    def test_clean_tables_keep_user(self, logger):
        UserFactory()
        self.session.commit()

        patch = "sparkmeter.database.databasecommand.getUtility"
        with mock.patch(patch) as getUtility:
            clean_tables(force=True, keep_user="user@domain.tld")

        assert getUtility.mock_calls == [
            mock.call(IApplication),
            mock.call().setup_databases(),
        ]

        logger.check(("sparkmeter.database.databasecommand", "INFO", "Cleaned up database tables"))

    def test_clean_tables_keep_ground(self, getUtility, logger, operator_role):
        g2 = GroundFactory()
        self.session.commit()

        SalesAccount(ground=g2)
        SalesAccount(ground=None, global_account=True)
        meter = MeterFactory(ground=g2)
        SMSMessageFactory()
        self.session.commit()

        event = EventFactory()
        self.session.add(event)
        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(roles=[operator_role], accounts=[account], grounds=[account.ground])
        meter = MeterFactory(
            credit_wallet__value=200,
            debt_wallet__value=100,
            system_info__last_energy=2972.3873,
            billing__total_cycle_energy=28045.12345,
        )
        source = TransactionSource.get_by_name(TransactionSource.BONUS)
        self.session.commit()

        Transaction.create_transactions(
            from_object=account,
            to_object=meter,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=meter.ground,
            session=self.session,
        )
        self.session.commit()

        clean_tables(force=True, keep_ground=self.ground.serial)

        assert Event.query.count() == 0

        assert getUtility.mock_calls == [
            mock.call(IApplication),
            mock.call().setup_databases(),
        ]

        logger.check(("sparkmeter.database.databasecommand", "INFO", "Cleaned up database tables"))

    def test_cloud_merge(self):
        for cls in [
            NodeGroup,
            Node,
            NodeIdentity,
            NodeGroupLink,
            Channel,
            Trigger,
            Conflict,
            Router,
            TriggerRouter,
        ]:
            cls.__table__.create(sql.engine, checkfirst=True)

        reload_channel = Channel(channel_id="reload", description="reload channel")
        channel = Channel(channel_id="user-channel", description="foo")
        trigger = Trigger(
            trigger_id="cloud-test-trigger",
            source_table_name="user",
            channel=channel,
            reload_channel=reload_channel,
            sync_on_incoming_batch=True,
        )
        self.session.add(trigger)
        source = NodeGroup(node_group_id="source_group_id")
        self.session.add(source)
        target = NodeGroup(node_group_id="target_group_id")
        self.session.add(target)
        self.session.flush()
        node_link = source.link(target)
        self.session.add(node_link)
        self.session.flush()
        conflict = Conflict(
            conflict_id="test-conflict",
            source_node_group_id=source.node_group_id,
            target_node_group_id=target.node_group_id,
        )
        self.session.add(conflict)
        self.session.commit()

        cloud_start_merge()

        assert not trigger.sync_on_incoming_batch
        assert list(
            self.session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.constraint_table_usage "
                    "WHERE constraint_name = 'transactions_reference_id_fkey';"
                )
            )
        ) == [(0,)]
        assert list(
            self.session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.constraint_table_usage "
                    "WHERE constraint_name = 'sms_message_in_reply_to_id_fkey';"
                )
            )
        ) == [(0,)]
        assert self.session.query(Conflict).count() == 0

        user = UserFactory(ground_all_access=True, account_all_access=True)
        ground = GroundFactory()
        sales_account = SalesAccountFactory(global_account=True)
        self.session.commit()
        cloud_finish_merge()

        assert list(
            self.session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.constraint_table_usage "
                    "WHERE constraint_name = 'transactions_reference_id_fkey';"
                )
            )
        ) == [(1,)]
        assert list(
            self.session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.constraint_table_usage "
                    "WHERE constraint_name = 'sms_message_in_reply_to_id_fkey';"
                )
            )
        ) == [(1,)]
        assert self.session.query(Conflict).count() != 0
        assert trigger.sync_on_incoming_batch

        assert ground.id in [m.id for m in user.grounds]
        assert sales_account.id in [a.id for a in user.accounts]

    def test_upgrade(self, cli, mocker, getUtility, logger):
        mocker.patch("sparkmeter.alembic.migrationhelper.command")
        cli("database", "upgrade", "head")

        getUtility.assert_called_once_with(IApplication)
        getUtility.return_value.setup_databases.assert_called_once()
        logger.check(
            ("sparkmeter.database.database", "INFO", "Disabling triggers for tables: []"),
            ("sparkmeter.database.database", "INFO", "Re-enabling triggers for tables []"),
            ("sparkmeter.database.database", "INFO", "Loading schema meterschema.sql"),
            ("sparkmeter.database.database", "INFO", "Loading schema transactionschema.sql"),
            ("sparkmeter.database.databasecommand", "INFO", "Finished upgrading to head"),
        )

    def test_downgrade(self, cli, mocker, getUtility, logger):
        mocker.patch("sparkmeter.alembic.migrationhelper.command")
        cli("database", "downgrade", "head")

        getUtility.assert_called_once_with(IApplication)
        getUtility.return_value.setup_databases.assert_called_once()
        logger.check(
            ("sparkmeter.database.database", "INFO", "Disabling triggers for tables: []"),
            ("sparkmeter.database.database", "INFO", "Re-enabling triggers for tables []"),
            ("sparkmeter.database.database", "INFO", "Loading schema meterschema.sql"),
            ("sparkmeter.database.database", "INFO", "Loading schema transactionschema.sql"),
            ("sparkmeter.database.databasecommand", "INFO", "Finished downgrading to head"),
        )

    def test_new_revision(self, cli, mocker, getUtility):
        revision = mocker.patch("alembic.command.revision")

        cli("database", "new-revision", "new patch")

        assert getUtility.mock_calls == [
            mock.call(IApplication),
            mock.call().setup_databases(),
        ]
        assert revision.mock_calls == [
            mock.call(mock.ANY, message="new patch", autogenerate=True, rev_id=mock.ANY),
        ]
