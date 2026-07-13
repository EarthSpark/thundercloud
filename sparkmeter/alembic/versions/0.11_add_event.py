# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Add event.

Revision ID: 0.11
Revises: 0.10
Create Date: 2016-01-21 13:03:39.616010

"""

import sqlalchemy as sa
from alembic import op

from sparkmeter.database.types import UUIDType

revision = "0.11"
down_revision = "0.10"


def upgrade():
    """Upgrade the database schema from 0.10 to 0.11."""
    op.create_table(
        "event",
        sa.Column("id", UUIDType(binary=True), nullable=False),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("needs_sync", sa.Boolean(), nullable=True),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("object_id", UUIDType(binary=True), nullable=True),
        sa.Column("object_table", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.11 to 0.10."""
    op.drop_table("event")
