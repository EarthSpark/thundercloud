# Copyright (C) 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Save limit in meter system info.

Revision ID: 0.57
Revises: 0.56
Create Date: 2018-01-19 17:58:46.571575

"""

import sqlalchemy as sa
from alembic import op

revision = "0.57"
down_revision = "0.56"


def upgrade():
    """Upgrade the database schema from 0.56 to 0.57."""
    op.add_column("meter_system_info", sa.Column("current_user_power_limit", sa.Float(), nullable=True))
    op.add_column("meter_system_info", sa.Column("last_config_datetime", sa.DateTime(), nullable=True))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.57 to 0.56."""
    op.drop_column("meter_system_info", "last_config_datetime")
    op.drop_column("meter_system_info", "current_user_power_limit")
