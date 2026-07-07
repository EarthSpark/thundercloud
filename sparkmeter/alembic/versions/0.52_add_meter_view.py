# Copyright (C) 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""add meter_view.

Revision ID: 0.52
Revises: 0.51
Create Date: 2017-08-02 17:59:44.071418

"""

revision = '0.52'
down_revision = '0.51'


def upgrade():
    """Upgrade the database schema from 0.51 to 0.52."""
    # Intentionally empty, adding meter_view


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.52 to 0.51."""
    raise SystemExit("Downgrading from 0.52 to 0.51 not supported")
