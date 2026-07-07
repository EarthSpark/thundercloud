# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Remove Microgrid graph

Revision ID: 0.42
Revises: 0.41
Create Date: 2016-06-16 21:45:01.783495

"""

from alembic import op

revision = '0.42'
down_revision = '0.41'


def upgrade():
    """Upgrade the database schema from 0.41 to 0.42."""
    op.drop_column('microgrid', 'graph')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.42 to 0.41."""
    raise SystemExit("Downgrading from 0.42 to 0.41 is not supported")
