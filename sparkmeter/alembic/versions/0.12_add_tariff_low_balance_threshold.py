# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Add tariff low_balance_threshold.

Revision ID: 0.12
Revises: 0.11
Create Date: 2016-01-22 11:04:42.253432

"""

import sqlalchemy as sa
from alembic import op

revision = '0.12'
down_revision = '0.11'


def upgrade():
    """Upgrade the database schema from 0.11 to 0.12."""
    op.add_column('tariff', sa.Column('low_balance_threshold', sa.Float(),
                                      server_default='0.0',
                                      nullable=False))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.12 to 0.11."""
    op.drop_column('tariff', 'low_balance_threshold')
