# Copyright (C) 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""make tariff plan_price not nullable.

Revision ID: 0.64
Revises: 0.63
Create Date: 2018-08-29 12:52:00.639606

"""

from alembic import op

revision = '0.64'
down_revision = '0.63'


def upgrade():
    """Upgrade the database schema from 0.63 to 0.64."""
    op.execute('UPDATE tariff SET plan_price=0 where plan_price is null')
    op.alter_column(u'tariff', 'plan_price', server_default='0', nullable=False)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.64 to 0.63."""
    op.alter_column(u'tariff', 'plan_price', server_default=None, nullable=True)
