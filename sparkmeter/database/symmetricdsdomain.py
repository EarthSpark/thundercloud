# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.

"""SymmetricDS domain classess."""

from sqlalchemy import (BigInteger, Column, DateTime, ForeignKey, ForeignKeyConstraint, Integer,
                        String)
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import func

from sparkmeter.database.columns import IntBoolean
from sparkmeter.database.ormobject import ORMObject

SCHEMA_NAME = "public"


def sym_table(name):
    """Helper to generate the table name."""
    return "sym_" + name


class SymmetricDSBaseDomain(ORMObject):

    """Base class for all SymmetricDS domain objects."""

    __abstract__ = True


class SymmetricDSTrackUpdatesDomain(SymmetricDSBaseDomain):

    """Base class for all SymmetricDS domain objects that track updates."""

    __abstract__ = True

    #: Timestamp when this entry was created.
    create_time = Column(DateTime, default=func.current_timestamp(),
                         nullable=True)

    #: The user who last updated this entry.
    last_update_by = Column(String(50), nullable=True)

    #: Timestamp when a user last updated this entry.
    last_update_time = Column(DateTime, default=func.current_timestamp(),
                              nullable=True)


class NodeGroup(SymmetricDSTrackUpdatesDomain):

    """
    Node Group.

    A category of Nodes that synchronizes data with one or more NodeGroups.
    A common use of NodeGroup is to describe a level in a hierarchy of
    data synchronization.
    """

    __tablename__ = sym_table("node_group")
    __table_args__ = {'schema': SCHEMA_NAME}

    #: Unique identifier for a node group, usually named something meaningful,
    #: like 'store' or 'warehouse'.
    node_group_id = Column(String, primary_key=True)

    #: A description of this node group.
    description = Column(String(255), nullable=True)

    def link(self, target, action=None):
        """Link two node groups together."""
        if action is None:
            action = NodeGroupLink.ACTION_PUSH
        return NodeGroupLink(source_node_group_id=self.node_group_id,
                             target_node_group_id=target.node_group_id,
                             data_event_action=action)


class Node(SymmetricDSBaseDomain):

    """
    Node.

    Representation of an instance of SymmetricDS that synchronizes data with
    one or more additional nodes. Each node has a unique identifier (nodeId)
    that is used when communicating, as well as a domain-specific identifier
    (externalId) that provides context within the local system.
    """

    __tablename__ = sym_table("node")
    __table_args__ = {'schema': SCHEMA_NAME}

    #: A unique identifier for a node.
    node_id = Column(String(50), primary_key=True)

    #: The node group that this node belongs to, such as 'store'.
    node_group_id = Column(String(50), ForeignKey(NodeGroup.node_group_id), nullable=False)

    #: A domain-specific identifier for context within the local system.
    #: For example, the retail store number.
    external_id = Column(String(255), nullable=False)

    #: Indicates whether this node should be sent synchronization. Disabled nodes
    #: are ignored by the triggers, so no entries are made in data_event for the node.
    sync_enabled = Column(IntBoolean, default=False)

    #: The URL to contact the node for synchronization.
    sync_url = Column(String(255), nullable=True)

    #: The version of the database schema this node manages. Useful for specifying
    #: synchronization by version.
    schema_version = Column(String(50), nullable=True)

    #: The version of SymmetricDS running at this node.
    symmetric_version = Column(String(50), nullable=True)

    #: The database product name at this node as reported by JDBC.
    database_type = Column(String(50), nullable=True)

    #: The database product version at this node as reported by JDBC.
    database_version = Column(String(50), nullable=True)

    #: The number of outgoing batches that have not yet been sent. This field is updated
    #: as part of the heartbeat job if the heartbeat.update.node.with.batch.status property
    #: is set to true.
    batch_to_send_count = Column(IntBoolean, default=False)

    #: The number of outgoing batches that are in error at this node. This field is updated
    #: as part of the heartbeat job if the heartbeat.update.node.with.batch.status property
    #: is set to true.
    batch_in_error_count = Column(IntBoolean, default=False)

    #: The node_id of the node where this node was created. This is typically filled
    #: automatically with the node_id found in node_identity where registration was opened
    #: for the node.
    created_at_node_id = Column(String(50), nullable=True)

    #: An indicator as to the type of SymmetricDS software that is running. Possible values
    #: are, but not limited to: engine, standalone, war, professional, mobile
    deployment_type = Column(String(50), nullable=True)

    #: Deprecated. Use node_host.heartbeat_time instead.
    heartbeat_time = Column(DateTime, nullable=True)

    #: Deprecated. Use node_host.timezone_offset instead.
    timezone_offset = Column(String(6), nullable=True)

    node_group = relationship('NodeGroup')


class NodeIdentity(SymmetricDSBaseDomain):

    """
    Node Identity.

    After registration, this table will have one row representing the identity
    of the node. For a root node, the row is entered by the user.
    """

    __tablename__ = sym_table("node_identity")
    __table_args__ = {'schema': SCHEMA_NAME}

    #: Unique identifier for a node.
    node_id = Column(String(50), primary_key=True)


class NodeGroupLink(SymmetricDSTrackUpdatesDomain):

    """
    Node Group Link.

    A source node_group sends its data updates to a target NodeGroup
    using a pull, push, or custom technique.
    """

    __tablename__ = sym_table("node_group_link")
    __table_args__ = {'schema': SCHEMA_NAME}

    ACTION_WAIT_ON_PULL = 'W'
    ACTION_PUSH = 'P'
    ACTION_ROUTE_ONLY = 'R'

    #: The node group where data changes should be captured
    source_node_group_id = Column(String(50),
                                  ForeignKey(NodeGroup.node_group_id),
                                  primary_key=True)

    #: The node group where data changes will be sent.
    target_node_group_id = Column(String(50),
                                  ForeignKey(NodeGroup.node_group_id),
                                  primary_key=True)

    #: The notification scheme used to send data changes to the target node group.
    data_event_action = Column(String, nullable=False)

    #: Indicates whether configuration that has changed should be synchronized to
    #: target nodes on this link
    sync_config_enabled = Column(IntBoolean, default=True)


class Channel(SymmetricDSTrackUpdatesDomain):

    """
    Channel.

    This table represents a category of data that can be synchronized independently
    of other channels. Channels allow control over the type of data flowing and
    prevents one type of synchronization from contending with another.
    """

    __tablename__ = sym_table("channel")
    __table_args__ = {'schema': SCHEMA_NAME}

    BATCH_ALGORITHM_DEFAULT = 'default'
    BATCH_ALGORITHM_TRANSACTIONAL = 'transactional'
    BATCH_ALGORITHM_NONTRANSACTIONAL = 'nontransactional'

    #: A unique identifer, usually named something meaningful, like 'sales' or 'inventory'.
    channel_id = Column(String(128), primary_key=True)

    #: Order of sequence to process channel data.
    processing_order = Column(Integer, default=0, nullable=False)

    #: The maximum number of Data Events to process within a batch for this channel.
    max_batch_size = Column(Integer, default=1000, nullable=False)

    #: The maximum number of batches to send during a 'synchronization' between two nodes.
    #: A 'synchronization' is equivalent to a push or a pull. If there are 12 batches ready
    #: to be sent for a channel and max_batch_to_send is equal to 10, then only the first
    #: 10 batches will be sent.
    max_batch_to_send = Column(Integer, default=60, nullable=False)

    #: The maximum number of data rows to route for a channel at a time.
    max_data_to_route = Column(Integer, default=100000, nullable=False)

    #: The minimum number of milliseconds allowed between attempts to extract data for
    #: targeted at a node_id.
    extract_period_millis = Column(Integer, default=0, nullable=False)

    #: Indicates whether channel is enabled or not.
    enabled = Column(IntBoolean, default=True)

    #: Indicates whether to read the old data during routing.
    use_old_data_to_route = Column(IntBoolean, default=True)

    #: Indicates whether to read the row data during routing.
    use_row_data_to_route = Column(IntBoolean, default=True)

    #: Indicates whether to read the pk data during routing.
    use_pk_data_to_route = Column(IntBoolean, default=True)

    #: Indicates that this channel is used for reloads.
    reload_flag = Column(IntBoolean, default=False)

    #: Indicates that this channel is used for file sync.
    file_sync_flag = Column(IntBoolean, default=False)

    #: Provides SymmetricDS a hint on how to treat captured data. Currently
    #: only supported by Oracle, Interbase and Firebird. If set to '0', then selects
    #: for routing and data extraction will be more efficient and lobs will be truncated
    #: at 4k in the trigger text. When it is set to '0' there is a 4k limit on the total
    #: size of a row and on the size of a LOB column. Note, when switching this value
    #: back and forth triggers need to be forced to regenerate.
    contains_big_lob = Column(IntBoolean, default=False)

    #: The algorithm to use when batching data on this channel. Possible values are:
    #: 'default', 'transactional', and 'nontransactional'
    batch_algorithm = Column(String(50), default=BATCH_ALGORITHM_DEFAULT, nullable=False)

    #: Identify the type of data loader this channel should use. Allows for the default
    #: dataloader to be swapped out via configuration for more efficient platform
    #: specific data loaders.
    data_loader_type = Column(String(50), default='default', nullable=False)

    #: Description on the type of data carried in this channel.
    description = Column(String(255), nullable=False)


class Router(SymmetricDSTrackUpdatesDomain):

    """
    Router.

    Configure a type of router from one node group to another. Note that routers
    are mapped to triggers through trigger_routers.
    """

    __tablename__ = sym_table("router")
    __table_args__ = (
        ForeignKeyConstraint(['source_node_group_id', 'target_node_group_id'],
                             [NodeGroupLink.source_node_group_id,
                              NodeGroupLink.target_node_group_id]),
        {'schema': SCHEMA_NAME},
    )

    #: A router that inserts into an automatically created audit table. It records
    #: captured changes to tables that it is linked to.
    #: See http://www.symmetricds.org/doc/3.7/html/user-guide.html#_audit_table_router
    TYPE_AUDIT = 'audit'

    #: A router that executes a Bean Shell script expression in order to select
    #: nodes to route to. The script can use the old and new column values
    #: See http://www.symmetricds.org/doc/3.7/html/user-guide.html#_beanshell_router
    TYPE_BSH = 'bsh'

    #: A router that compares old or new column values in a captured data
    #: row to a constant value or the value of a target node’s external id or
    #: node id.
    #: See http://www.symmetricds.org/doc/3.7/html/user-guide.html#_column_match_router
    TYPE_COLUMN = 'column'

    #: A router that sends all captured data to all nodes that belong to
    #: the target node group defined in the router.
    #: See: http://www.symmetricds.org/doc/3.7/html/user-guide.html#_default_router
    TYPE_DEFAULT = 'default'

    #: A router that executes a Java expression in order to select nodes to route to.
    #: The script can use the old and new column values.
    #: See http://www.symmetricds.org/doc/3.7/html/user-guide.html#Java Router
    TYPE_JAVA = 'java'

    #: A router which can be configured to determine routing based on an existing or
    #: ancillary table specifically for the purpose of routing data.
    #: See http://www.symmetricds.org/doc/3.7/html/user-guide.html#_lookup_table_router
    TYPE_LOOKUPTABLE = 'lookuptable'

    #: A router that executes a SQL expression against the database to select
    #: nodes to route to. This SQL expression can be passed values of old and
    #: new column values.
    #: See http://www.symmetricds.org/doc/3.7/html/user-guide.html#_subselect_router
    TYPE_SUBSELECT = 'subselect'

    #: Unique description of a specific router
    router_id = Column(String(50), primary_key=True, nullable=False)

    #: Optional name of catalog where a target table is located. If this field
    #: is unspecified, the catalog will be either the default catalog at the
    #: target node or the source_catalog_name from the trigger, depending on how
    #: use_source_catalog_schema is set on the router. Variables are substituted
    #: for $(sourceNodeId), $(sourceExternalId), $(sourceNodeGroupId),
    #: $(targetNodeId), $(targetExternalId), $(targetNodeGroupId), and $(none).
    target_catalog_name = Column(String(255))

    #: Optional name of schema where a target table is located. If this field
    #: is unspecified, the catalog will be either the default catalog at the
    #: target node or the source_catalog_name from the trigger, depending on how
    #: use_source_catalog_schema is set on the router. Variables are substituted
    #: for $(sourceNodeId), $(sourceExternalId), $(sourceNodeGroupId),
    #: $(targetNodeId), $(targetExternalId), $(targetNodeGroupId), and $(none).
    target_schema_name = Column(String(255))

    #: Optional name for a target table. Only use this if the target table name is
    #: different than the source.
    target_table_name = Column(String(255))

    #: Routers with this node_group_id will install triggers that are mapped to this router.
    source_node_group_id = Column(String(50), nullable=False)

    #: The node_group_id for nodes to route data to. Note that routing can
    #: be further narrowed down by the configured router_type and router_expression.
    target_node_group_id = Column(String(50), nullable=False)

    # The name of a specific type of router. Out of the box routers are 'default','column','bsh',
    #: 'subselect' and 'audit.' Custom routers can be configured as extension points.
    router_type = Column(String(50), default=TYPE_DEFAULT)

    #: An expression that is specific to the type of router that is configured
    #: in router_type. See the documentation for each router for more details.
    router_expression = Column(String)

    #: Flag that indicates that this router should route updates.
    sync_on_update = Column(IntBoolean, default=True)

    #: Flag that indicates that this router should route inserts.
    sync_on_insert = Column(IntBoolean, default=True)

    #: Flag that indicates that this router should route deletes.
    sync_on_delete = Column(IntBoolean, default=True)

    #: Whether or not to assume that the target catalog/schema name should be the same as
    #: the source catalog/schema name. The target catalog or schema name will still
    #: override if not blank.
    use_source_catalog_schema = Column(IntBoolean, default=True)


class Trigger(SymmetricDSTrackUpdatesDomain):

    u"""
    Trigger.

    Configures database triggers that capture changes in the database.
    Configuration of which triggers are generated for which tables is
    stored here. Triggers are created in a node’s database if the
    source_node_group_id of a router is mapped to a row in this table.
    """

    __tablename__ = sym_table("trigger")
    __table_args__ = {'schema': SCHEMA_NAME}

    #: Unique identifier for a trigger.
    trigger_id = Column(String(128), primary_key=True, nullable=False)

    #: Optional name for the catalog the configured table is in. If the name includes *
    #: then a wildcard match on the table name will be attempted. Wildcard names can
    #: include a list of names that are comma separated. The ! symbol may be used to
    #: indicate a NOT match condition.
    source_catalog_name = Column(String(255), nullable=True)

    #: Optional name for the schema a configured table is in. If the name includes *
    #: then a wildcard match on the table name will be attempted. Wildcard names can
    #: include a list of names that are comma separated. The ! symbol may be used to
    #: indicate a NOT match condition.
    source_schema_name = Column(String(255), nullable=True)

    #: The name of the source table that will have a trigger installed to watch
    #: for data changes. If the name includes * then a wildcard match on the
    #: table name will be attempted. Wildcard names can include a list of names
    #: that are comma separated. The ! symbol may be used to indicate a NOT match condition.
    source_table_name = Column(String(255), nullable=False)

    #: The channel_id of the channel that data changes will flow through.
    channel_id = Column(String(128), ForeignKey(Channel.channel_id),
                        nullable=False)

    #: The channel_id of the channel that will be used for reloads.
    reload_channel_id = Column(String(128), ForeignKey(Channel.channel_id),
                               nullable=False, default='reload')

    #: Whether or not to install an update trigger.
    sync_on_update = Column(IntBoolean, default=True, nullable=False)

    #: Whether or not to install an insert trigger.
    sync_on_insert = Column(IntBoolean, default=True, nullable=False)

    #: Whether or not to install an delete trigger.
    sync_on_delete = Column(IntBoolean, default=True, nullable=False)

    #: Whether or not an incoming batch that loads data into this table should
    #: cause the triggers to capture data_events. Be careful turning this on,
    #: because an update loop is possible.
    sync_on_incoming_batch = Column(IntBoolean, default=False, nullable=False)

    #: Override the default generated name for the update trigger.
    name_for_update_trigger = Column(String(255), nullable=True)

    #: Override the default generated name for the insert trigger.
    name_for_insert_trigger = Column(String(255), nullable=True)

    #: Override the default generated name for the delete trigger.
    name_for_delete_trigger = Column(String(255), nullable=True)

    #: Specify a condition for the update trigger firing using an expression
    #: specific to the database.
    sync_on_update_condition = Column(String, nullable=True)

    #: Specify a condition for the insert trigger firing using an expression
    #: specific to the database.
    sync_on_insert_condition = Column(String, nullable=True)

    #: Specify a condition for the delete trigger firing using an expression
    #: specific to the database.
    sync_on_delete_condition = Column(String, nullable=True)

    #: Specify update trigger text to execute after the SymmetricDS
    #: trigger text runs. This field is not applicable for H2,
    #: HSQLDB 1.x or Apachy Derby.
    custom_on_update_text = Column(String, nullable=True)

    #: Specify insert trigger text to execute after the SymmetricDS
    #: trigger text runs. This field is not applicable for H2,
    #: HSQLDB 1.x or Apachy Derby.
    custom_on_insert_text = Column(String, nullable=True)

    #: Specify delete trigger text to execute after the SymmetricDS
    #: trigger text runs. This field is not applicable for H2,
    #: HSQLDB 1.x or Apachy Derby.
    custom_on_update_text = Column(String, nullable=True)

    #: Specify a SQL select statement that returns a single result. It will
    #: be used in the generated database trigger to populate the EXTERNAL_DATA
    #: field on the data table.
    external_select = Column(String, nullable=True)

    #: Override the default expression for the transaction identifier that groups
    #: the data changes that were committed together.
    tx_id_expression = Column(String, nullable=True)

    #: An expression that will be used to capture the channel id in the trigger.
    #: This expression will only be used if the channel_id is set to 'dynamic.'
    channel_expression = Column(String, nullable=True)

    #: Specify a comma-delimited list of columns that should not be synchronized
    #: from this table. Note that if a primary key is found in this list,
    #: it will be ignored.
    excluded_column_names = Column(String, nullable=True)

    #: Specify a comma-delimited list of columns that should be used as the key
    #: for synchronization operations. By default, if not specified, then the
    #: primary key of the table will be used.
    sync_key_names = Column(String, nullable=True)

    #: Specifies whether to capture lob data as the trigger is firing or to
    #: stream lob columns from the source tables using callbacks during
    #: extraction. A value of 1 indicates to stream from the source via
    #: callback; a value of 0, lob data is captured by the trigger.
    use_stream_lobs = Column(IntBoolean, default=False, nullable=False)

    #: Provides a hint as to whether this trigger will capture big lobs data.
    #: If set to 1 every effort will be made during data capture in trigger and
    #: during data selection for initial load to use lob facilities to extract
    #: and store data in the database. On Oracle, this may need to be set
    #: to 1 to get around 4k concatenation errors during data capture and
    #: during initial load.
    use_capture_lobs = Column(IntBoolean, default=False, nullable=False)

    #: Indicates whether this trigger should capture and send the
    #: old data (previous state of the row before the change).
    use_capture_old_data = Column(IntBoolean, default=True, nullable=False)

    #: Indicates whether this trigger should capture and send the old data
    #: (previous state of the row before the change).
    use_handle_key_updates = Column(IntBoolean, default=False, nullable=False)

    channel = relationship('Channel', foreign_keys=[channel_id])

    reload_channel = relationship('Channel', foreign_keys=[reload_channel_id])

    def map_router(self, router, initial_load_order=1):
        """Map this trigger to a router.

        :param router: the router
        :param initial_load_order: initial load order
        :returns: a TriggerRouter.
        """
        return TriggerRouter(trigger=self,
                             router=router,
                             initial_load_order=initial_load_order)


class TriggerRouter(SymmetricDSTrackUpdatesDomain):

    """Trigger Router.

    Map a trigger to a router.
    """

    __tablename__ = sym_table("trigger_router")
    __table_args__ = {'schema': SCHEMA_NAME}

    #: The id of a trigger.
    trigger_id = Column(String(128), ForeignKey(Trigger.trigger_id),
                        primary_key=True, nullable=False)

    #: The id of a router.
    router_id = Column(String(50), ForeignKey(Router.router_id),
                       primary_key=True, nullable=False)

    #: Indicates whether this trigger router is enabled or not.
    enabled = Column(IntBoolean, default=True, nullable=False)

    #: Order sequence of this table when an initial load is sent to a node.
    #: If this value is the same for multiple tables, then SymmetricDS will
    #: attempt to order the tables according to FK constraints. If this value
    #: is set to a negative number, then the table will be excluded from an
    #: initial load.
    initial_load_order = Column(Integer, default=1, nullable=False)

    #: Optional expression that can be used to pare down the data
    #: selected from a table during the initial load process.
    initial_load_select = Column(String, nullable=True)

    #: The expression that is used to delete data when an initial load occurs.
    #: If this field is empty, no delete will occur before the initial load.
    #: If this field is not empty, the text will be used as a sql statement
    #: and executed for the initial load delete.
    initial_load_delete_stmt = Column(String, nullable=True)

    #: Only applicable if the initial load extract job is enabled. The number
    #: of batches to split an initial load of a table across. If 0 then a
    #: select count(*) will be used to dynamically determine the number
    #: of batches based on the max_batch_size of the reload channel.
    initial_load_batch_count = Column(Integer, default=1, nullable=True)

    #: When enabled, the node will route data that originated from a
    #: node back to that node. This attribute is only effective if
    #: sync_on_incoming_batch is set to 1.
    ping_back_enabled = Column(IntBoolean, default=False, nullable=False)

    trigger = relationship('Trigger', foreign_keys=[trigger_id])

    router = relationship('Router', foreign_keys=[router_id])


class Conflict(SymmetricDSTrackUpdatesDomain):

    """
    Conflict.

    Defines how conflicts in row data should be handled during the load process.
    """

    __tablename__ = sym_table("conflict")
    __table_args__ = (
        ForeignKeyConstraint(['source_node_group_id', 'target_node_group_id'],
                             [NodeGroupLink.source_node_group_id,
                              NodeGroupLink.target_node_group_id]),
        {'schema': SCHEMA_NAME},
    )

    #: Indicates that only the primary key is used to detect a conflict.
    #: If a row exists with the same primary key, then no conflict is
    #: detected during an update or a delete. Updates and deletes rows are
    #: resolved using only the primary key columns. If a row already exists
    #: during an insert then a conflict has been detected.
    DETECT_TYPE_USE_PK_DATA = 'USE_PK_DATA'

    #: Indicates that the primary key plus any data that has changed on
    #: the source system will be used to detect a conflict. If a row exists
    #: with the same old values on the target system as they were on the
    #: source system for the columns that have changed on the source system,
    #: then no conflict is detected during an update or a delete. If a row
    #: already exists during an insert then a conflict has been detected.
    DETECT_TYPE_USE_CHANGED_DATA = 'USE_CHANGED_DATA'

    #: Indicates that all of the old data values are used to detect a
    #: conflict. Old data is the data values of the row on the source
    #: system prior to the change. If a row exists with the same old
    #: values on the target system as they were on the source system,
    #: then no conflict is detected during an update or a delete. If a row
    #: already exists during an insert then a conflict has been detected.
    DETECT_TYPE_USE_OLD_DATA = 'USE_OLD_DATA'

    #: Indicates that the primary key plus a timestamp column (as configured
    #: in detect_expression ) will indicate whether a conflict has occurred.
    #: If the target timestamp column is not equal to the old source timestamp
    #: column, then a conflict has been detected. If a row already exists during
    #: an insert then a conflict has been detected.
    DETECT_TYPE_USE_USE_TIMESTAMP = 'USE_TIMESTAMP'

    #: Indicates that the primary key plus a version column (as configured in
    #: detect_expression ) will indicate whether a conflict has occurred.
    #: If the target version column is not equal to the old source version column,
    #: then a conflict has been detected. If a row already exists during an insert
    #: then a conflict has been detected.
    DETECT_TYPE_USE_USE_VERSION = 'USE_VERSION'

    #: Indicates that when a conflict is detected the system should
    #: automatically apply the changes anyways. If the source operation
    #: was an insert, then an update will be attempted. If the source
    #: operation was an update and the row does not exist, then an
    #: insert will be attempted. If the source operation was a delete
    #: and the row does not exist, then the delete will be ignored. The
    #: resolve_changes_only flag controls whether all columns will be
    #: updated or only columns that have changed will be updated during
    #: a fallback operation.
    RESOLVE_TYPE_FALLBACK = 'FALLBACK'

    #: Indicates that when a conflict is detected the system should
    #: automatically ignore the incoming change. The resolve_row_only
    #: column controls whether the entire batch should be ignore or just
    #: the row in conflict.
    RESOLVE_TYPE_IGNORE = 'IGNORE'

    #: Indicates that when a conflict is detected the batch will remain
    #: in error until manual intervention occurs. A row in error is
    #: inserted into the INCOMING_ERROR table. The conflict detection id
    #: that detected the conflict is recorded (i.e., the conflict_id
    #: value from CONFLICT), along with the old data, new data, and the
    #: "current data" (by current data, we mean the unexpected data at
    #: the target which doesn’t match the old data as expected) in
    #: columns old_data, new_data, and cur_data. In order to resolve, the
    #: resolve_data column can be manually filled out which will be used
    #: on the next load attempt instead of the original source data. The
    #: resolve_ignore flag can also be used to indicate that the row
    #: should be ignored on the next load attempt.
    RESOLVE_TYPE_MANUAL = 'MANUAL'

    #: Indicates that when a conflict is detected by USE_TIMESTAMP or
    #: USE_VERSION that the either the source or the target will win
    #: based on the which side has the newer timestamp or higher version
    #: number. The resolve_row_only column controls whether the entire
    #: batch should be ignore or just the row in conflict.
    RESOLVE_TYPE_NEWER_WINS = 'NEWER_WINS'

    #: The resolved data of the single row in the batch in conflict,
    #: along with the entire remainder of the batch, is sent back to the
    #: originating node.
    PING_BACK_REMAINING_ROWS = 'REMAINING_ROWS'

    #: The resolved data of the single row in the batch that caused the
    #: conflict is sent back to the originating node.
    PING_BACK_SINGLE_ROW = 'SINGLE_ROW'

    #: No data is sent back to the originating node, even if the resolved
    #: data doesn’t match the data the node sent.
    PING_BACK_OFF = 'OFF'

    #: Unique identifier for a specific conflict detection setting.
    conflict_id = Column(String(50), primary_key=True, nullable=False)

    #: The source node group for which this setting will be applied to.
    #: References a node group link.
    source_node_group_id = Column(String(50),
                                  ForeignKey(NodeGroup.node_group_id),
                                  primary_key=True,
                                  nullable=False)

    #: The target node group for which this setting will be applied to.
    #: References a node group link.
    target_node_group_id = Column(String(50),
                                  ForeignKey(NodeGroup.node_group_id),
                                  primary_key=True,
                                  nullable=False)

    #: Optional channel that this setting will be applied to.
    target_channel_id = Column(String(128), nullable=True)

    #: Optional database catalog that the target table belongs to. Only use
    #: this if the target table is not in the default catalog.
    target_catalog_name = Column(String(255), nullable=True)

    #: Optional database schema that the target table belongs to. Only use
    #: this if the target table is not in the default schema.
    target_schema_name = Column(String(255), nullable=True)

    #: Optional database table that this setting will apply to. If left blank,
    #: the setting will be for any table in the channel (if set) and in the
    #: specified node group link.
    target_table_name = Column(String(255), nullable=True)

    #: Indicates the strategy to use for detecting conflicts during a dml action.
    #: The possible values are:
    #: - use_pk_data (manual, fallback, ignore),
    #: - use_changed_data (manual, fallback, ignore),
    #: - use_old_data (manual, fallback, ignore),
    #: - use_timestamp (newer_wins),
    #: - use_version (newer_wins)
    detect_type = Column(String(128), default=DETECT_TYPE_USE_PK_DATA, nullable=False)

    #: An expression that provides additional information about the detection
    #: mechanism. If the detection mechanism is use_timestamp or use_version
    #: then this expression will be the name of the timestamp or version column.
    detect_expression = Column(String, nullable=True)

    #: Indicates the strategy for resolving update conflicts. The possible values
    #: differ based on the detect_type that is specified.
    resolve_type = Column(String(128), default=RESOLVE_TYPE_FALLBACK, nullable=False)

    #: Indicates the strategy for sending resolved conflicts back to the source system.
    #: Possible values are: OFF, SINGLE_ROW, and REMAINING_ROWS.
    ping_back = Column(String(128), default=PING_BACK_OFF, nullable=False)

    #: Indicates that when applying changes during an update that only data that has
    #: changed should be applied. Otherwise, all the columns will be
    #: updated. This really only applies to updates.
    resolve_changes_only = Column(IntBoolean, default=False, nullable=False)

    #: Indicates that an action should take place for the entire batch if possible.
    #: This applies to a resolve type of 'ignore'. If a row is in conflict and the
    #: resolve type is 'ignore', then the entire batch will be ignored.
    resolve_row_only = Column(IntBoolean, default=False, nullable=False)


class NodeHost(SymmetricDSBaseDomain):

    """
    Node host.

    Representation of an physical workstation or server that is hosting
    the SymmetricDS software. In a clustered environment there may be more than
    one entry per node in this table.
    """

    __tablename__ = sym_table("node_host")
    __table_args__ = (
        {'schema': SCHEMA_NAME},
    )

    #: A unique identifier for a node.
    node_id = Column(String(50), primary_key=True, nullable=False)

    #: The host name of a workstation or server. If more than one instance of
    #: SymmetricDS runs on the same server, then this value can be a 'server id'
    #: specified by -Druntime.symmetric.cluster.server.id
    host_name = Column(String(60), primary_key=True, nullable=False)

    #: The ip address for the host.
    ip_address = Column(String(50), nullable=True)

    #: The user SymmetricDS is running under
    os_user = Column(String(50), nullable=True)

    #: The name of the OS
    os_name = Column(String(50), nullable=True)

    #: The hardware architecture of the OS
    os_arch = Column(String(50), nullable=True)

    #: The version of the OS
    os_version = Column(String(50), nullable=True)

    #: The number of processors available to use.
    available_processors = Column(Integer, default=0, nullable=True)

    #: The amount of free memory available to the JVM.
    free_memory_bytes = Column(BigInteger, default=0, nullable=True)

    #: The amount of total memory available to the JVM.
    total_memory_bytes = Column(BigInteger, default=0, nullable=True)

    #: The max amount of memory available to the JVM.
    max_memory_bytes = Column(BigInteger, default=0, nullable=True)

    #: The version of java that SymmetricDS is running as.
    java_version = Column(String(50), nullable=True)

    #: The vendor of java that SymmetricDS is running as.
    java_vendor = Column(String(255), nullable=True)

    #: The verision of the JDBC driver that is being used.
    jdbc_version = Column(String(255), nullable=True)

    #: The version of SymmetricDS running at this node.
    symmetric_version = Column(String(50), nullable=True)

    #: The time zone offset in RFC822 format at the time of the last heartbeat.
    timezone_offset = Column(String(6), nullable=True)

    #: The last timestamp when the node sent a heartbeat, which is attempted
    #: every ten minutes by default.
    heartbeat_time = Column(DateTime, nullable=True)

    #: Timestamp when this instance was last restarted.
    last_restart_time = Column(DateTime, nullable=False)

    #: Timestamp when this entry was created
    create_time = Column(DateTime, nullable=False)

    @classmethod
    def get_heartbeat_time(cls, session, node_id):
        """Get the last timestamp for a given node."""
        try:
            self = (
                cls.query
                .filter_by(node_id=node_id)
                .order_by(cls.heartbeat_time.desc())
                .limit(1)
                .one()
            )
            return self.heartbeat_time
        except NoResultFound:
            pass
