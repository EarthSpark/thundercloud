# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Store totalizer in the database.

Revision ID: 0.21
Revises: 0.20
Create Date: 2016-03-29 11:56:41.783598

"""

import logging

import sqlalchemy as sa
from alembic import op

revision = '0.21'
down_revision = '0.20'
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.20 to 0.21."""
    op.add_column('meter', sa.Column('meter_type', sa.String(), nullable=True))
    conn = op.get_bind()
    res = conn.execute("""
        UPDATE meter SET meter_type = 'customer'""")
    logger.info('Set meter_type of %r meters' % (res.rowcount, ))
    op.alter_column('meter', 'meter_type', nullable=False)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.21 to 0.20."""
    op.drop_column('meter', 'meter_type')
