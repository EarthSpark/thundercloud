# Copyright (C) 2013-2026 SparkMeter, Inc.
# All Rights Reserved.
"""add meter driver selection.

Revision ID: 0.84
Revises: 0.83
Create Date: 2026-07-11

"""

import sqlalchemy as sa
from alembic import op

revision = "0.84"
down_revision = "0.83"


def upgrade():
    """Upgrade the database schema from 0.83 to 0.84."""
    op.add_column("meter", sa.Column("provider_id", sa.String(), nullable=True))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.84 to 0.83."""
    op.execute("DROP VIEW IF EXISTS meter_view")
    op.drop_column("meter", "provider_id")
