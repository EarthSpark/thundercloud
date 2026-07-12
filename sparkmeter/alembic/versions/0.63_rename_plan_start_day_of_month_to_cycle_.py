# Copyright (C) 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""rename plan_start_day_of_month to cycle_start_day_of_month.

Revision ID: 0.63
Revises: 0.62
Create Date: 2018-08-29 11:27:43.116132

"""

from alembic import op

revision = "0.63"
down_revision = "0.62"


def upgrade():
    """Upgrade the database schema from 0.62 to 0.63."""
    op.alter_column("tariff", "plan_start_day_of_month", new_column_name="cycle_start_day_of_month")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.63 to 0.62."""
    op.alter_column("tariff", "cycle_start_day_of_month", new_column_name="plan_start_day_of_month")
