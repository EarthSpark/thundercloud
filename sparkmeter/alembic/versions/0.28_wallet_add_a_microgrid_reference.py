# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""wallet: Add a microgrid reference.

Revision ID: 0.28
Revises: 0.27
Create Date: 2016-04-22 18:08:32.578680

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0.28'
down_revision = '0.27'
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.27 to 0.28."""
    op.add_column('wallet', sa.Column('grid_id', postgresql.UUID(), nullable=True))

    conn = op.get_bind()
    results = conn.execute("UPDATE wallet SET grid_id = microgrid.id FROM microgrid;")
    logger.info('Updated %r wallets' % (results.rowcount, ))

    op.alter_column('wallet', 'grid_id', nullable=False)
    op.create_foreign_key(u'wallet_grid_id_fkey',
                          'wallet', 'microgrid', ['grid_id'], ['id'])


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.28 to 0.27."""
    op.drop_constraint(u'wallet_grid_id_fkey', 'wallet', type_='foreignkey')
    op.drop_column('wallet', 'grid_id')
