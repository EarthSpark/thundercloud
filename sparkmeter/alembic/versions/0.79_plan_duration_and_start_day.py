# Copyright (C) 2013-2020 SparkMeter, Inc.
# All Rights Reserved.
"""Add awareness of plan duration and start day to tariffs

Revision ID: 0.79
Revises: 0.78
Create Date: 2020-01-29 19:41:21.367217

"""

import sqlalchemy as sa
from alembic import op

revision = "0.79"
down_revision = "0.78"


def upgrade():
    """Upgrade the database schema from 0.78 to 0.79."""
    op.add_column("tariff", sa.Column("plan_duration_span", sa.Integer, server_default="1", nullable=True))
    op.add_column("tariff", sa.Column("plan_duration_unit", sa.String(), server_default="m", nullable=True))
    op.execute("UPDATE tariff SET plan_duration_span = '1', plan_duration_unit = 'm'")
    op.alter_column("tariff", "plan_duration_span", nullable=False)
    op.alter_column("tariff", "plan_duration_unit", nullable=False)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.79 to 0.78."""
    op.drop_column("tariff", "plan_duration_span")
    op.drop_column("tariff", "plan_duration_unit")
