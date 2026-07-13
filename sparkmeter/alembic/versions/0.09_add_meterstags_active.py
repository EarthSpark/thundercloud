# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Add MetersTags.active.

Revision ID: 0.09
Revises: 0.08
Create Date: 2015-12-14 14:36:03.576126

"""

import sqlalchemy as sa
from alembic import op

revision = "0.09"
down_revision = "0.08"


def upgrade():
    """Upgrade the database schema from 0.08 to 0.09."""
    op.add_column("meters_tags", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.09 to 0.08."""
    op.drop_column("meters_tags", "active")
