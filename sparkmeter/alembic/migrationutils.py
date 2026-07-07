# -*- coding: utf-8 -*-
# Copyright © 2018 SparkMeter, Inc.
# All Rights Reserved.
"""Migration utilities."""
import logging

import sqlalchemy.orm.exc
from alembic import op
from sqlalchemy.engine import reflection
from sqlalchemy.orm.session import Session

from sparkmeter.database.symmetricdsdomain import NodeGroup, NodeGroupLink
from sparkmeter.database.sync import (SYNC_DIRECTION_BOTH, SYNC_GROUP_CLOUD, SYNC_GROUP_GROUND,
                                      SyncChannelHelper, configure_domain_sync_channels,
                                      force_table_reload)

logger = logging.getLogger(__name__)


def create_synced_table(table_name, channel_name, *cols, **kwargs):
    """Create a table migration that also sets up a sync channel.

    :param table_name: The name of the table to create
    :param channel_name: The base name of the channel over which the table should be synced (e.g., 'meter')
    :param *cols: The SQLAlchemy column definitions for the table.
    :param **kwargs: An optional 'sync_init_callback' function, 'sync_direction', and values to pass to
        Alembic's `create_table`
    :returns: A reference to the table
    """
    sync_init_callback = kwargs.pop('sync_init_callback', lambda *args: None)
    sync_direction = kwargs.pop('sync_direction', SYNC_DIRECTION_BOTH)
    table = op.create_table(table_name, *cols, **kwargs)
    if sym_ds_configured():
        session = Session(bind=op.get_bind())
        channel_helpers = _create_channel_helpers(session)
        sync_channel_classes = {}
        # For the provided channel, build a fake/mock class that has everything the existing sync code needs
        sync_channel_classes[channel_name] = [
            type("{}_DOMAIN".format(table_name.upper()), (object,), {
                '__tablename__': table_name,
                'sync_direction': sync_direction,
                'sync_init': classmethod(sync_init_callback)
            }),
        ]
        logger.info('Setting up sync for table "%s" on channel "%s"', table_name, channel_name)
        configure_domain_sync_channels(session, channel_helpers, sync_channel_classes)
        session.commit()
    else:  # pragma: nocoverage
        logger.info('SymmetricDS not detected. Skipping setting up sync for table "%s".', table_name)
    return table


def force_table_reload_if_exists(table, dest_node_id, channel, session):
    """Conditionally force symmetricds to reload data from the local table to the corresponding table on the
    destination node.

    :param table: The name of the table to reload.
    :param dest_node_id: The node ID of the target database.
    :param channel: The SymDS channel to sync over.
    :param session: The SQL session to use.
    """
    if sym_ds_configured():
        force_table_reload(table, dest_node_id, channel, session)
    else:  # pragma: nocoverage
        logger.info('SymmetricDS not detected. Skipping forced reload for table "%s".', table)


def sym_ds_configured():
    """Test if any SymmetricDS tables are present and SymDS is configured.

    :returns: `True` if SymDS tables are present, `False` otherwise.
    """
    insp = reflection.Inspector.from_engine(op.get_bind())
    try:
        next(table for table in insp.get_table_names() if table.startswith('sym_'))
    except StopIteration:  # pragma: nocoverage
        return False

    # If SymDS tables are present, verify the bare minimum amount of config is present
    try:
        session = Session(op.get_bind())
        cloud_group = session.query(NodeGroup).filter_by(node_group_id=SYNC_GROUP_CLOUD).one()
        ground_group = session.query(NodeGroup).filter_by(node_group_id=SYNC_GROUP_GROUND).one()
        session.query(NodeGroupLink).filter_by(
            source_node_group_id=ground_group.node_group_id,
            target_node_group_id=cloud_group.node_group_id
        ).one()
        session.query(NodeGroupLink).filter_by(
            source_node_group_id=cloud_group.node_group_id,
            target_node_group_id=ground_group.node_group_id
        ).one()
    except sqlalchemy.orm.exc.NoResultFound:  # pragma: nocoverage
        return False
    return True


def _create_channel_helpers(session):
    """Get the channel creation helpers.

    :param session: The active session.
    :returns: A collection of session helpers for the ground and cloud
    """
    cloud_group = session.query(NodeGroup).filter_by(node_group_id=SYNC_GROUP_CLOUD).one()
    ground_group = session.query(NodeGroup).filter_by(node_group_id=SYNC_GROUP_GROUND).one()
    ground_to_cloud = session.query(NodeGroupLink).filter_by(
        source_node_group_id=ground_group.node_group_id,
        target_node_group_id=cloud_group.node_group_id
    ).one()
    cloud_to_ground = session.query(NodeGroupLink).filter_by(
        source_node_group_id=cloud_group.node_group_id,
        target_node_group_id=ground_group.node_group_id
    ).one()
    return [
        SyncChannelHelper('ground', ground_to_cloud),
        SyncChannelHelper('cloud', cloud_to_ground),
    ]
