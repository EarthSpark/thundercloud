# Copyright (C) 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Update sym_conflict for ground tables.

Revision ID: 0.59
Revises: 0.58
Create Date: 2018-03-01 10:43:35.415350

"""

revision = '0.59'
down_revision = '0.58'


def upgrade():
    """Upgrade the database schema from 0.58 to 0.59."""
    # Noop, since we don't want to regenerate newer patches


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.59 to 0.58."""
    raise SystemExit("Downgrading from 0.59 to 0.58 not supported")
