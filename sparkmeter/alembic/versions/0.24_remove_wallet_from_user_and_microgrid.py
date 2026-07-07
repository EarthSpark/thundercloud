# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Remove wallet from User and Microgrid.

Revision ID: 0.24
Revises: 0.23
Create Date: 2016-04-13 18:03:57.995121

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0.24'
down_revision = '0.23'
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.23 to 0.24."""
    op.drop_constraint(u'microgrid_debt_wallet_id_fkey', 'microgrid', type_='foreignkey')
    op.drop_constraint(u'microgrid_credit_wallet_id_fkey', 'microgrid', type_='foreignkey')
    op.drop_constraint(u'user_debt_wallet_id_fkey', 'user', type_='foreignkey')
    op.drop_constraint(u'user_credit_wallet_id_fkey', 'user', type_='foreignkey')
    op.drop_column('user', 'debt_wallet_id')
    op.drop_column('user', 'credit_wallet_id')
    op.drop_column('microgrid', 'debt_wallet_id')
    op.drop_column('microgrid', 'credit_wallet_id')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.24 to 0.23."""
    conn = op.get_bind()
    for table in ['user', 'microgrid']:
        for wallet_type in ['credit', 'debt']:
            column = '%s_wallet_id' % wallet_type
            op.add_column(table, sa.Column(column, postgresql.UUID(),
                                           autoincrement=False, nullable=True))
            op.create_foreign_key(u'%s_%s_wallet_id_fkey' % (table, wallet_type, ),
                                  table, 'wallet', [column], ['id'])
            res = conn.execute("""
            UPDATE "%(table)s" SET %(column)s = wallet.id
            FROM wallet
            WHERE wallet.%(table)s_id = "%(table)s".id AND wallet_type = '%(wallet_type)s'""" % (
                dict(column=column, wallet_type=wallet_type, table=table)))
            logger.info('Set %s wallet of %r %ss' % (wallet_type, res.rowcount, table))
            # Only vendors have wallets, Null is allowed for operators
            if table != 'user':
                op.alter_column(table, column, nullable=False)
