# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import datetime

from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.database.alchemy import sql
from sparkmeter.database.database import load_schema
from sparkmeter.database.symmetricdsdomain import (
    Channel,
    Conflict,
    Node,
    NodeGroup,
    NodeGroupLink,
    NodeHost,
    NodeIdentity,
    Router,
    Trigger,
    TriggerRouter,
)
from sparkmeter.database.sync import create_default_policy
from sparkmeter.event.eventdomain import Event, SMSConfig, SMSMessage
from sparkmeter.ground.grounddomain import Ground, GroundPrivate, GroundsAddresses
from sparkmeter.meter.meterdomain import (
    Address,
    Customer,
    Meter,
    MeterBilling,
    MeterConfig,
    MetersTags,
    MeterSystemInfo,
    MeterTag,
    SparkmacNode,
)
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.system.systemdomain import SystemState, SystemVersion
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource, Wallet
from sparkmeter.user.userdomain import Role, RolesUsers, SalesAccountsUsers, User


class SyncViewTest(SparkMeterTestCaseBase):
    trigger_external_selects = {
        Address: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
        GroundsAddresses: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
        GroundPrivate: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
        Wallet: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."grid_id" as uuid)',
        ],
        SalesAccount: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
        Meter: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
        Customer: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground, meter",
            'WHERE meter.id = cast($(curTriggerValue)."meter_id" as uuid) AND meter.ground_id = ground.id',
        ],
        MeterBilling: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground, meter",
            'WHERE meter.id = cast($(curTriggerValue)."meter_id" as uuid) AND meter.ground_id = ground.id',
        ],
        MeterConfig: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground, meter",
            'WHERE meter.id = cast($(curTriggerValue)."meter_id" as uuid) AND meter.ground_id = ground.id',
        ],
        MeterSystemInfo: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground, meter",
            'WHERE meter.id = cast($(curTriggerValue)."meter_id" as uuid) AND meter.ground_id = ground.id',
        ],
        SparkmacNode: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground, meter",
            'WHERE meter.id = cast($(curTriggerValue)."meter_id" as uuid) AND meter.ground_id = ground.id',
        ],
        MetersTags: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground, meter",
            'WHERE meter.id = cast($(curTriggerValue)."meter_id" as uuid) AND meter.ground_id = ground.id',
        ],
        User: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
        RolesUsers: [
            "SELECT ground.serial AS ground_serial",
            'FROM ground, "user"',
            'WHERE "user".id = cast($(curTriggerValue)."user_id" as uuid) AND "user".ground_id = ground.id',
        ],
        SalesAccountsUsers: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground, sales_account",
            'WHERE sales_account.id = cast($(curTriggerValue)."sales_account_id" as uuid) '
            "AND sales_account.ground_id = ground.id",
        ],
        Transaction: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
        Event: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
        SMSMessage: [
            "SELECT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
        DashboardDailyTariffSummary: [
            "SELECT DISTINCT ground.serial AS ground_serial",
            "FROM ground",
            'WHERE ground.id = cast($(curTriggerValue)."ground_id" as uuid)',
        ],
    }

    def importSchema(self):
        tables = [
            NodeGroup,
            Node,
            NodeHost,
            NodeIdentity,
            NodeGroupLink,
            Channel,
            Trigger,
            Conflict,
            Router,
            TriggerRouter,
        ]
        sql.metadata.drop_all(bind=sql.engine, tables=[t.__table__ for t in tables], checkfirst=True)

        load_schema(sql.engine, "symmetricds.sql")

    def test_default_policy(self):
        self.importSchema()
        assert self.session.query(Channel).count() == 7

        create_default_policy(self.session, external_id="cloud")

        groups = self.session.query(NodeGroup).order_by(NodeGroup.node_group_id).all()
        assert len(groups) == 2
        assert groups[0].node_group_id == "cloud-group"
        assert groups[1].node_group_id == "ground-group"

        node = self.session.query(Node).one()
        assert node.node_id == "cloud"
        assert node.node_group_id == "cloud-group"
        assert node.sync_enabled
        assert node.external_id == "cloud"
        assert node.created_at_node_id == "cloud"

        identity = self.session.query(NodeIdentity).one()
        assert identity.node_id == "cloud"

        links = self.session.query(NodeGroupLink).order_by(NodeGroupLink.source_node_group_id).all()
        assert len(links) == 2
        assert links[0].source_node_group_id == "cloud-group"
        assert links[0].target_node_group_id == "ground-group"
        assert links[0].data_event_action == NodeGroupLink.ACTION_WAIT_ON_PULL
        assert links[0].sync_config_enabled
        assert links[1].source_node_group_id == "ground-group"
        assert links[1].target_node_group_id == "cloud-group"
        assert links[1].data_event_action == NodeGroupLink.ACTION_PUSH
        assert links[1].sync_config_enabled

        bundles = [
            ("system", 0, [SystemState, SystemVersion]),
            ("ground", 0, [Ground, GroundPrivate]),
            ("address", 5, [GroundsAddresses, Address]),
            ("wallet", 10, [Wallet]),
            ("sales-account", 20, [SalesAccount]),
            ("tariff", 30, [Tariff]),
            (
                "meter",
                40,
                [
                    MeterTag,
                    Meter,
                    Customer,
                    MeterBilling,
                    MeterConfig,
                    MeterSystemInfo,
                    SparkmacNode,
                    MetersTags,
                ],
            ),
            ("user", 50, [Role, User, RolesUsers, SalesAccountsUsers]),
            ("transaction", 60, [TransactionSource, Transaction]),
            ("event", 70, [Event, SMSConfig, SMSMessage]),
            ("dashboard", 80, [DashboardDailyTariffSummary]),
        ]
        for source in ["cloud", "ground"]:
            for name, processing_order, tables in bundles:
                channel_id = "%s-%s-%s" % (source, name, "channel")
                channel = self.session.query(Channel).filter_by(channel_id=channel_id).scalar()
                if channel is None:
                    self.fail("Channel %s does not exist" % (channel_id,))
                assert channel.description == name
                assert channel.processing_order == processing_order, (source, name)
                assert channel.enabled
                assert channel.batch_algorithm == Channel.BATCH_ALGORITHM_DEFAULT

                for i, table in enumerate(tables):
                    router_id = "%s-%s-%s" % (source, table.__tablename__, "router")
                    router = self.session.query(Router).filter_by(router_id=router_id).scalar()
                    if router is None:
                        self.fail("Router %s does not exist" % (router_id,))
                    has_external_select = False
                    router_expression = ""
                    router_type = Router.TYPE_DEFAULT
                    if source == "cloud":
                        if table == Wallet:
                            router_expression = (
                                "(c.external_id IN ("
                                "SELECT serial FROM ground WHERE id = cast(:GRID_ID as uuid)) OR "
                                "cast(:GRID_ID as uuid) IS NULL)"
                            )
                            router_type = Router.TYPE_SUBSELECT
                        elif table in [Event, SMSMessage, SalesAccount]:
                            router_expression = (
                                "(c.external_id IN ("
                                "SELECT serial FROM ground WHERE id = cast(:GROUND_ID as uuid)) OR "
                                "cast(:GROUND_ID as uuid) IS NULL)"
                            )
                            router_type = Router.TYPE_SUBSELECT
                        elif table not in [
                            Ground,
                            MeterTag,
                            Role,
                            RolesUsers,
                            SMSConfig,
                            Tariff,
                            TransactionSource,
                            User,
                            SalesAccountsUsers,
                            SystemState,
                            SystemVersion,
                        ]:
                            has_external_select = True
                            router_expression = "external_data=:EXTERNAL_ID"
                            router_type = Router.TYPE_COLUMN
                    assert router.router_type == router_type
                    assert router.router_expression == router_expression, (source, table)
                    trigger_id = "%s-%s-%s" % (source, table.__tablename__, "trigger")
                    trigger = self.session.query(Trigger).filter_by(trigger_id=trigger_id).scalar()
                    if trigger is None:
                        self.fail("Trigger %s does not exist" % (trigger_id,))
                    assert trigger.channel_id == channel_id
                    assert trigger.source_table_name == table.__tablename__
                    assert trigger.sync_on_incoming_batch == (source == "cloud")
                    if has_external_select:
                        assert trigger.external_select
                        assert [
                            line.strip() for line in trigger.external_select.split("\n")
                        ] == self.trigger_external_selects[table]
                    else:
                        assert not trigger.external_select

                    trigger_router = (
                        self.session.query(TriggerRouter)
                        .filter_by(trigger_id=trigger_id, router_id=router_id)
                        .scalar()
                    )
                    if trigger_router is None:
                        self.fail("TriggerRouter for %s+%s does not exist" % (trigger_id, router_id))
                    assert trigger_router.trigger_id == trigger_id
                    assert trigger_router.router_id == router_id
                    assert trigger_router.initial_load_order == processing_order

    def test_get_heartbeat_time(self):
        self.importSchema()
        self.session.flush()

        node_host = NodeHost(
            node_id="test-node",
            host_name="hostname",
            create_time=datetime.datetime.now(),
            last_restart_time=datetime.datetime.now(),
            heartbeat_time=datetime.datetime(2009, 1, 1),
        )
        self.session.add(node_host)
        node_host = NodeHost(
            node_id="test-node",
            host_name="another-hostname",
            create_time=datetime.datetime.now(),
            last_restart_time=datetime.datetime.now(),
            heartbeat_time=datetime.datetime(2010, 1, 1),
        )
        self.session.add(node_host)
        self.session.commit()

        dt = NodeHost.get_heartbeat_time(self.session, "test-node")
        assert dt == datetime.datetime(2010, 1, 1)

        assert not NodeHost.get_heartbeat_time(self.session, "does-not-exist")
