# Copyright (C) 2013-2020 SparkMeter, Inc.
# All Rights Reserved.
"""Make snapshot_ids nullable.

Revision ID: 0.80
Revises: 0.79
Create Date: 2020-02-25 15:55:15.091286

"""

from alembic import op

revision = "0.80"
down_revision = "0.79"


def upgrade():
    """Upgrade the database schema from 0.79 to 0.80."""
    # This is needed to patch systems that were upgraded to 1.15.x, which contained a bad migration.
    #  It will bring them in line with the newly-updated revision v0.77
    op.alter_column("reading", "snapshot_id", nullable=True, server_default=None)
    op.alter_column("event", "snapshot_id", nullable=True, server_default=None)
    op.alter_column("transactions", "to_snapshot_id", nullable=True, server_default=None)
    op.alter_column("transactions", "from_snapshot_id", nullable=True, server_default=None)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.80 to 0.79."""
