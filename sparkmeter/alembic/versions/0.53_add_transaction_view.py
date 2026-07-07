# Copyright (C) 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""add meter_view.

Revision ID: 0.53
Revises: 0.52
Create Date: 2017-10-16 12:24:20.089282

"""

revision = '0.53'
down_revision = '0.52'


def upgrade():
    """Upgrade the database schema from 0.52 to 0.53."""
    # Intentionally empty, adding transaction_view


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.53 to 0.52."""
    raise SystemExit("Downgrading from 0.53 to 0.52 not supported")
