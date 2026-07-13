# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""add ground override meter state.

Revision ID: 0.49
Revises: 0.48
Create Date: 2017-06-02 07:42:57.568653

"""

import sqlalchemy as sa
from alembic import op

revision = "0.49"
down_revision = "0.48"


def upgrade():
    """Upgrade the database schema from 0.48 to 0.49."""
    op.add_column(
        "ground_private",
        sa.Column("override_meter_state", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("ground_private", sa.Column("override_meter_state_modified", sa.DateTime(), nullable=True))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.49 to 0.48."""
    op.drop_column("ground_private", "override_meter_state_modified")
    op.drop_column("ground_private", "override_meter_state")
