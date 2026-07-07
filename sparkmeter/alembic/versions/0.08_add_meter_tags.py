# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Add meter tags.

Revision ID: 0.08
Revises: 0.07
Create Date: 2015-11-26 18:35:34.389389

"""

import sqlalchemy as sa
from alembic import op

from sparkmeter.database.types import UUIDType

revision = '0.08'
down_revision = '0.07'


def upgrade():
    """Upgrade the database schema from 0.07 to 0.08."""
    op.create_table('meter_tag',
                    sa.Column('id', UUIDType(binary=True), nullable=False),
                    sa.Column('last_update', sa.DateTime(), nullable=True),
                    sa.Column('needs_sync', sa.Boolean(), nullable=True),
                    sa.Column('last_sync', sa.DateTime(), nullable=True),
                    sa.Column('name', sa.String(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('name', name='meter_tag_name'))
    op.create_table('meters_tags',
                    sa.Column('id', UUIDType(binary=True), nullable=False),
                    sa.Column('last_update', sa.DateTime(), nullable=True),
                    sa.Column('needs_sync', sa.Boolean(), nullable=True),
                    sa.Column('last_sync', sa.DateTime(), nullable=True),
                    sa.Column('tag_id', UUIDType(binary=True), nullable=False),
                    sa.Column('meter_id', UUIDType(binary=True), nullable=False),
                    sa.ForeignKeyConstraint(['meter_id'], ['meter.id'], ),
                    sa.ForeignKeyConstraint(['tag_id'], ['meter_tag.id'], ),
                    sa.PrimaryKeyConstraint('id'))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.08 to 0.07."""
    op.drop_table('meters_tags')
    op.drop_table('meter_tag')
