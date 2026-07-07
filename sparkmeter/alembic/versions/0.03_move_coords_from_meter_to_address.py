# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Move coords from meter to address.

Revision ID: 0.03
Revises: 0.02
Create Date: 2015-08-27 16:09:28.220426

"""

import sqlalchemy as sa
from alembic import op

revision = '0.03'
down_revision = '0.02'


def upgrade():  # pragma: nocoverage
    """Upgrade the database schema from 0.02 to 0.03."""
    op.add_column('address', sa.Column('coords', sa.String(), nullable=True))
    op.drop_column('meter_config', 'coords')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.03 to 0.02."""
    op.add_column('meter_config', sa.Column('coords', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('address', 'coords')
