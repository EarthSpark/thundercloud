# Copyright (C) 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
"""adding_system_tables.

Revision ID: 0.72
Revises: 0.71
Create Date: 2018-11-21 15:40:10.222880

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.alembic.migrationutils import create_synced_table
from sparkmeter.database.sync import SYNC_CHANNEL_SYSTEM

revision = '0.72'
down_revision = '0.71'


def upgrade():
    """Upgrade the database schema from 0.71 to 0.72."""
    create_synced_table(
        'system_state',
        SYNC_CHANNEL_SYSTEM,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('system', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    create_synced_table(
        'system_version',
        SYNC_CHANNEL_SYSTEM,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('version', sa.String(), nullable=False, unique=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.72 to 0.71."""
    op.drop_table('system_version')
    op.drop_table('system_state')
