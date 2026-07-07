# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Add transaction origin.

Revision ID: 0.16
Revises: 0.15
Create Date: 2016-02-21 15:17:29.512722

"""

import logging

import sqlalchemy as sa
from alembic import op

revision = '0.16'
down_revision = '0.15'
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.15 to 0.16."""
    op.add_column('transactions', sa.Column('origin', sa.String()))

    conn = op.get_bind()
    res = conn.execute("""
        UPDATE transactions SET origin = 'user'
          FROM transaction_sources
         WHERE transactions.source_id = transaction_sources.id AND
               lower(transaction_sources.name) = 'cash';""")
    logger.info('Set origin of %r user transactions' % (res.rowcount, ))

    res = conn.execute("""
        UPDATE transactions SET origin = 'system'
         WHERE transactions.origin is NULL;""")
    logger.info('Set origin of %r system transactions' % (res.rowcount, ))
    op.alter_column('transactions', 'origin', existing_type=sa.String(), nullable=False)

    op.add_column('transactions', sa.Column('state', sa.String()))
    conn = op.get_bind()
    res = conn.execute("""
        UPDATE transactions SET state = 'error'
         WHERE transactions.error IS NOT NULL;""")
    logger.info('Set state of %r error transactions' % (res.rowcount, ))

    res = conn.execute("""
        UPDATE transactions SET state = 'pending'
         WHERE transactions.error IS NULL AND transactions.processed = false;""")
    logger.info('Set state of %r pending transactions' % (res.rowcount, ))

    res = conn.execute("""
        UPDATE transactions SET state = 'processed'
         WHERE transactions.processed = true;""")
    logger.info('Set state of %r processed transactions' % (res.rowcount, ))

    op.alter_column('transactions', 'state', existing_type=sa.String(), nullable=False)
    op.drop_column('transactions', 'processed')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.16 to 0.15."""
    op.add_column('transactions', sa.Column('processed', sa.Boolean()))
    conn = op.get_bind()
    res = conn.execute("""
        UPDATE transactions SET processed = true
         WHERE transactions.state = 'processed';""")
    logger.info('Set processed of %r transactions' % (res.rowcount, ))
    res = conn.execute("""
        UPDATE transactions SET processed = false
         WHERE transactions.processed IS NULL;""")
    logger.info('Set unprocessed of %r transactions' % (res.rowcount, ))
    op.alter_column('transactions', 'processed',
                    existing_type=sa.String(), nullable=False,
                    server_default=sa.false())
    op.drop_column('transactions', 'origin')
    op.drop_column('transactions', 'state')
