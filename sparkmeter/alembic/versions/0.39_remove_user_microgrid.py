# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Remove user microgrid reference.

Revision ID: 0.39
Revises: 0.38
Create Date: 2016-06-16 21:45:01.783495

"""

from alembic import op

revision = '0.39'
down_revision = '0.38'


def upgrade():
    """Upgrade the database schema from 0.38 to 0.39."""
    op.drop_column(u'user', 'microgrid_id')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.39 to 0.38."""
    raise SystemExit("Downgrading from 0.39 to 0.38 is not supported")
