# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Remove user email unique constriant

Revision ID: 0.45
Revises: 0.44
Create Date: 2016-05-31 11:06:29.239818

"""

from alembic import op

revision = '0.45'
down_revision = '0.44'


def upgrade():
    """Upgrade the database schema from 0.44 to 0.45."""
    op.drop_constraint(u'user_email_key', 'user')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.45 to 0.44."""
    raise SystemExit("Downgrading from 0.45 to 0.44 is not supported")
