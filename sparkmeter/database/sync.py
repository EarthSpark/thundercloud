# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Synchronization configuration and utilities."""

import collections
import logging
from builtins import object, str

from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import func, text

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
from sparkmeter.database.tables import get_table_by_name
from sparkmeter.database.types import UUIDType

logger = logging.getLogger(__name__)

SYNC_CHANNEL_ADDRESS = "address"
SYNC_CHANNEL_CONFIG = "config"
SYNC_CHANNEL_DASHBOARD = "dashboard"
SYNC_CHANNEL_EVENT = "event"
SYNC_CHANNEL_METER = "meter"
SYNC_CHANNEL_GROUND = "ground"
SYNC_CHANNEL_READING = "reading"
SYNC_CHANNEL_SALES_ACCOUNT = "sales-account"
SYNC_CHANNEL_SNAPSHOT = "snapshot"
SYNC_CHANNEL_SYSTEM = "system"
SYNC_CHANNEL_TARIFF = "tariff"
SYNC_CHANNEL_TRANSACTION = "transaction"
SYNC_CHANNEL_USER = "user"
SYNC_CHANNEL_WALLET = "wallet"

SYNC_DIRECTION_BOTH = 0
SYNC_DIRECTION_GROUND_TO_CLOUD = 1

SYNC_GROUP_GROUND = "ground-group"
SYNC_GROUP_CLOUD = "cloud-group"

# channel -> sync options
_sync_channel_classes = collections.OrderedDict()

# This value is used to set the initial load order, and the processing order.
# Order sequence of channels when an initial load is sent to a node.
# If this value is the same for multiple tables, then SymmetricDS will
# attempt to order the tables according to FK constraints. If this value
# is set to a negative number, then the table will be excluded from an
# initial load.
# FIXME: What happens to the processing order if the value is negative.
_sync_channel_order = {
    SYNC_CHANNEL_SYSTEM: 0,
    SYNC_CHANNEL_GROUND: 0,
    SYNC_CHANNEL_CONFIG: 2,
    SYNC_CHANNEL_ADDRESS: 5,
    SYNC_CHANNEL_WALLET: 10,
    SYNC_CHANNEL_SNAPSHOT: 15,
    SYNC_CHANNEL_SALES_ACCOUNT: 20,
    SYNC_CHANNEL_TARIFF: 30,
    SYNC_CHANNEL_METER: 40,
    SYNC_CHANNEL_USER: 50,
    SYNC_CHANNEL_TRANSACTION: 60,
    SYNC_CHANNEL_EVENT: 70,
    SYNC_CHANNEL_DASHBOARD: 80,
    SYNC_CHANNEL_READING: 90,
}


def syncchannel(channel):
    """Decorator for domain classes that sync be synced.

    :param channel: the channel the class belongs to.
    """

    def wrapper(cls):
        _sync_channel_classes.setdefault(channel, []).append(cls)
        return cls

    return wrapper


class SyncGroup(object):
    """
    SyncGroup: a Symmetricds domain class helper.

     - Router: filter data going between groups
     - Trigger: collect data for a table
     - TriggerRouter: map a trigger to a router
     - Conflict: defines conflict detection and resolution
    """

    def __init__(self, channel, table_name, source, node_link):
        """
        Create a new sync group helper.

        :param channel: the channel for this group
        :param table_name: table name this group
        :param source: prefix for ids (cloud/ground)
        :param node_link: the node link this channel applies to
        """
        self.channel = channel
        self.table_name = table_name
        self.source = source
        self.node_link = node_link
        self.trigger = None
        self.router = None
        self.trigger_router = None
        self.conflicts = []

    def _configure_router(self):
        """Create a new router configuration for this sync group.

        :returns: a sym router instance
        """
        router_id = "%s-%s-%s" % (self.source, self.table_name, "router")
        created, router = Router.get_one_or_create(session=self.channel.session, router_id=router_id)
        if created:
            router.router_type = Router.TYPE_DEFAULT
            router.router_expression = ""
            router.create_time = func.current_timestamp()
        router.source_node_group_id = self.node_link.source_node_group_id
        router.target_node_group_id = self.node_link.target_node_group_id
        router.last_update_time = func.current_timestamp()
        return router

    def _configure_trigger(self):
        """Create a new trigger configuration for this sync group.

        :returns: a sym trigger instance
        """
        trigger_id = "%s-%s-%s" % (self.source, self.table_name, "trigger")
        if self.node_link.source_node_group_id == SYNC_GROUP_CLOUD:
            sync_on_incoming_batch = 1
        else:
            sync_on_incoming_batch = 0
        created, trigger = Trigger.get_one_or_create(session=self.channel.session, trigger_id=trigger_id)
        if created:
            trigger.create_time = func.current_timestamp()

        trigger.source_table_name = self.table_name
        trigger.channel = self.channel
        trigger.last_update_time = func.current_timestamp()
        trigger.sync_on_incoming_batch = sync_on_incoming_batch
        return trigger

    def _configure_trigger_router(self):
        trigger_router = (
            self.channel.session.query(TriggerRouter)
            .filter_by(trigger=self.trigger, router=self.router)
            .scalar()
        )
        if trigger_router is None:
            trigger_router = self.trigger.map_router(self.router)
        trigger_router.initial_load_order = _sync_channel_order[self.channel.description]
        self.channel.session.add(trigger_router)
        return trigger_router

    def initialize_domain_class(self, domain_class):
        """Initialize a domain class.

        Creates a router, trigger and trigger router and calls sync_init on the
        domain class for customized initialization.

        :param domain_class: the domain class to init
        """
        self.router = self._configure_router()
        self.trigger = self._configure_trigger()
        self.trigger_router = self._configure_trigger_router()

        domain_class.sync_init(self)

    def is_cloud(self):
        """If this config is valid for cloud.

        :returns: ``True`` if this config applies to cloud, otherwise ``False``.
        """
        return self.node_link.source_node_group_id == SYNC_GROUP_CLOUD

    def format_trigger_attr(self, attr):
        """Format a column attribute for usage within a trigger."""
        value = '$(curTriggerValue)."%s"' % (attr.expr.name,)
        if isinstance(attr.property.columns[0].type, UUIDType):
            value = "cast(%s as uuid)" % (value,)
        return text(value)

    def set_column_router(self, expression):
        """Attach a column router to this config.

        :param expression: column expression.
        """
        self.router.router_type = Router.TYPE_COLUMN
        self.router.router_expression = expression

    def set_subselect_router(self, expression):
        """Attach a subselect router to this config.

        :param expression: subselect expression.
        """
        self.router.router_type = Router.TYPE_SUBSELECT
        self.router.router_expression = expression

    def set_external_select(self, *args, **kwargs):
        """Provide an external select for this sync group.

        This function should return a string containing an SQL statement that
        will run inside the triggers of SymmetricDS which are running after the triggers
        are run (see AFTER INSERT/UPDATE/DELETE in PostgreSQL doc).

        Use $(curTriggerValue) to access the value the new values in INSERT/UPDATE triggers
        and the old values in DELETE triggers.

        Since this is running after deletions, it will no longer be possible to query the table,
        you you have to use the removed values in $(curTriggerValue) to figure out references
        that are needed to determine the external_id.

        Constructs a query that should be used to find the external_id, which currently
        is the ground serial. That can later be referenced as external_data in a
        column router.

        :param args: arguments passed in to query.filter()

        """
        ground_t = get_table_by_name("ground")
        query = Query(ground_t.c.serial)
        distinct = kwargs.pop("distinct", None)
        if distinct is not None:
            query = query.distinct()
        for arg in args:
            query = query.filter(arg)
        self.trigger.external_select = str(query)

    def set_key_columns(self, *attrs):
        """Configure sync key names for this config.

        :param attrs: list of column attributes for this class.
        """
        self.trigger.sync_key_names = ",".join([attr.expr.name for attr in attrs])

    def set_conflict_winner(self, conflict_winner):
        """Create a new conflict configuration.

        :param conflict_winner: the conflict winner node group id
        :returns: a list of conflicts
        """
        if conflict_winner == self.node_link.source_node_group_id:
            resolve_type = Conflict.RESOLVE_TYPE_FALLBACK
        else:
            resolve_type = Conflict.RESOLVE_TYPE_IGNORE
        conflict_id = "%s-%s-%s" % (self.source, self.table_name, "conflict")
        created, conflict = Conflict.get_one_or_create(session=self.channel.session, conflict_id=conflict_id)
        conflict.source_node_group_id = self.node_link.source_node_group_id
        conflict.target_node_group_id = self.node_link.target_node_group_id
        conflict.target_table_name = (self.table_name,)
        conflict.detect_type = Conflict.DETECT_TYPE_USE_CHANGED_DATA
        conflict.resolve_type = resolve_type
        conflict.ping_back = Conflict.PING_BACK_REMAINING_ROWS
        conflict.resolve_changes_only = True
        conflict.resolve_row_only = False
        self.conflicts.append(conflict)


class SyncChannelHelper(object):
    """
    SymmetricDS channel configuration helper.

    SyncChannelHelper is a helper to setup the configuration for each way, it consists of
    - NodeGroupLink: link between two node groups
    - Channel: a category of data that can be synced independently, currently one per table
    """

    def __init__(self, source, node_link):
        """Create a new sync configuration group.

        :param source: short name of the group
        :param node_link: the node link for this channel
        """
        self.source = source
        self.node_link = node_link

    def _should_sync(self, class_direction, source_node):
        if class_direction == SYNC_DIRECTION_BOTH:
            return True

        return class_direction == SYNC_DIRECTION_GROUND_TO_CLOUD and source_node == SYNC_GROUP_GROUND

    def configure_channel(self, session, channel_name):
        """Create a new channel configuration for this sync group.

        :param session: a database session
        :param channel_name: name of the channel to create
        :returns: a sym channel instance
        """
        channel_id = "%s-%s-%s" % (self.source, channel_name, "channel")
        channel = Channel.get_one_or_create(session, channel_id=channel_id).object
        channel.processing_order = _sync_channel_order[channel_name]
        channel.max_batch_size = 1000
        channel.max_batch_to_send = 10
        channel.extract_period_millis = 0
        channel.batch_algorithm = Channel.BATCH_ALGORITHM_DEFAULT
        channel.enabled = 1
        channel.description = channel_name
        return channel

    def configure_domain_class(self, channel, domain_class):
        """Configure this channel.

        :param channel: channel
        :param domain_class: domain class for this channel
        """
        if self._should_sync(domain_class.sync_direction, self.node_link.source_node_group_id):
            group = SyncGroup(
                channel=channel,
                table_name=domain_class.__tablename__,
                source=self.source,
                node_link=self.node_link,
            )
            group.initialize_domain_class(domain_class)


def create_default_policy(session, external_id):
    """
    Create the default sync policy.

    This is only needed for the cloud/master node.

    :param session: a database session
    :param external_id: the external id of this node.
    """
    # Root/Master node of the SymmetricDS sync group
    master_node_id = "cloud"

    # Multigrid syncing will initially be composed of two node groups,
    # one for ground and one for cloud. That way we can have multiple grounds
    # connecting to a single cloud using the same synchronization mechanism, eg
    # readings is one way, meters is only for one ground
    cloud_group = NodeGroup.get_one_or_create(
        session, node_group_id=SYNC_GROUP_CLOUD, description="A ThunderCloud node"
    ).object
    session.add(cloud_group)

    ground_group = NodeGroup.get_one_or_create(
        session, node_group_id=SYNC_GROUP_GROUND, description="A Groundbolt node"
    ).object
    session.add(ground_group)

    # Configure the cloud node instance, which is the first node and master node for the
    # whole synchronization system. Additional nodes will be added automatically upon
    # registration.
    cloud_node = Node.get_one_or_create(
        session,
        node_id=master_node_id,
        node_group=cloud_group,
        external_id=external_id,
        sync_enabled=1,
        created_at_node_id=master_node_id,
    ).object
    session.add(cloud_node)

    session.flush()

    cloud_identity = NodeIdentity.get_one_or_create(session, node_id=master_node_id).object
    session.add(cloud_identity)

    ground_to_cloud = NodeGroupLink.query.filter_by(
        source_node_group_id=ground_group.node_group_id, target_node_group_id=cloud_group.node_group_id
    ).scalar()
    if ground_to_cloud is None:
        ground_to_cloud = ground_group.link(cloud_group, NodeGroupLink.ACTION_PUSH)
        session.add(ground_to_cloud)

    cloud_to_ground = NodeGroupLink.query.filter_by(
        source_node_group_id=cloud_group.node_group_id, target_node_group_id=ground_group.node_group_id
    ).scalar()
    if cloud_to_ground is None:
        cloud_to_ground = cloud_group.link(ground_group, NodeGroupLink.ACTION_WAIT_ON_PULL)
        session.add(cloud_to_ground)

    session.flush()

    channel_helpers = [
        SyncChannelHelper("ground", ground_to_cloud),
        SyncChannelHelper("cloud", cloud_to_ground),
    ]

    configure_domain_sync_channels(session, channel_helpers, _sync_channel_classes)
    session.commit()


def configure_domain_sync_channels(session, channel_helpers, sync_channel_classes):
    """Set up sync channels for each registered domain.

    This requires a commit on the provided session object.

    :param session: The DB session to use.
    :param channel_helpers: The collection of SyncChannelHelpers for each environment.
    :param sync_channel_classes: A dict of channel names with collections of
        the domain classes that are in the channel
    """
    for channel_name, domain_classes in sync_channel_classes.items():
        for helper in channel_helpers:
            channel = helper.configure_channel(session, channel_name)
            for domain_class in domain_classes:
                helper.configure_domain_class(channel, domain_class)


def force_table_reload(table, dest_node_id, channel, session):
    """Force symmetricds to reload data from the local table to the corresponding table on the
    destination node.

    :param table: The name of the table to reload.
    :param dest_node_id: The node ID of the target database.
    :param channel: The SymDS channel to sync over.
    :param session: The SQL session to use.
    """
    logger.info('Forcing table "%s" to reload to node "%s" over channel "%s"', table, dest_node_id, channel)
    session.execute(
        text(
            """
        INSERT INTO sym_data (
            table_name,
            event_type,
            row_data,
            trigger_hist_id,
            channel_id,
            create_time,
            node_list
        )
        SELECT
          '{table}',
          'R',
          '1=1',
          COALESCE(max(trigger_hist_id), 1),
          '{channel}',
          current_timestamp,
          '{dest_node_id}'
        FROM sym_trigger_hist""".format(table=table, channel=channel, dest_node_id=dest_node_id)
        )
    )
