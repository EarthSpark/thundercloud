# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Add merged sync collections.

Revision ID: 0.01
Revises: e9b4b2460bc
Create Date: 2015-08-20 18:37:21.192314

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0.01'
down_revision = 'e9b4b2460bc'


def upgrade():  # pragma: nocoverage
    """Upgrade the database schema from e9b4b2460bc to 0.01."""
    op.add_column('sync_operation',
                  sa.Column('merged_local_collection_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('sync_operation',
                  sa.Column('merged_remote_collection_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.drop_column('sync_operation', 'merged_collection_id')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.01 to e9b4b2460bc."""
    op.add_column('sync_operation',
                  sa.Column('merged_collection_id', postgresql.UUID(), autoincrement=False, nullable=True))
    op.drop_column('sync_operation', 'merged_remote_collection_id')
    op.drop_column('sync_operation', 'merged_local_collection_id')
