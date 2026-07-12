# Copyright (C) 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Remove ground_private.status.

Revision ID: 0.58
Revises: 0.57
Create Date: 2018-02-28 21:08:19.397283

"""

from alembic import op

revision = "0.58"
down_revision = "0.57"


def upgrade():
    """Upgrade the database schema from 0.57 to 0.58."""
    op.drop_column("ground_private", "status")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.58 to 0.57."""
    raise SystemExit("Downgrading from 0.58 to 0.57 not supported")
