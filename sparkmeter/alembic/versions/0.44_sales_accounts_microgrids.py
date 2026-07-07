# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""accounts_microgrids

Revision ID: 0.44
Revises: 0.43
Create Date: 2016-05-31 11:06:29.239818

"""

import logging

import sqlalchemy as sa
from alembic import op

from sparkmeter.misc.uuidutils import as_uuid

revision = '0.44'
down_revision = '0.43'
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.43 to 0.44."""
    op.add_column(
        'sales_account',
        sa.Column(
            'global_account',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )
    op.alter_column('sales_account', 'microgrid_id', nullable=True)
    op.alter_column('wallet', 'grid_id', nullable=True)
    op.drop_constraint(u'sales_accounts_users_sales_account_id_fkey',
                       'sales_accounts_users', type_='foreignkey')
    op.drop_constraint(u'user_api_sales_account_id_fkey',
                       'user', type_='foreignkey')

    conn = op.get_bind()
    sales_account_id = conn.execute(
        'SELECT id FROM sales_account WHERE system = true;').fetchone()[0]

    conn.execute(
        sa.sql.text(
            'UPDATE wallet '
            'SET sales_account_id = :id '
            'FROM sales_account '
            'WHERE sales_account.id = wallet.sales_account_id AND system = true;'
        ),
        id=as_uuid('system-sales-account')
    )
    conn.execute(
        sa.sql.text(
            'UPDATE sales_account '
            'SET id = :id, '
            'global_account = true, '
            'microgrid_id = NULL '
            'WHERE system = true;'
        ),
        id=as_uuid('system-sales-account')
    )
    for stmt in [
        ('UPDATE "user" SET api_sales_account_id = :new_id '
         'WHERE api_sales_account_id = :old_id;'),
        ('UPDATE sales_accounts_users SET sales_account_id = :new_id '
         'WHERE sales_account_id = :old_id;')]:
        conn.execute(
            sa.sql.text(stmt),
            new_id=as_uuid('system-sales-account'),
            old_id=sales_account_id,
        )
    logger.info('Updated uuid for system sales accounts')

    res = conn.execute(
        'UPDATE sales_account '
        'SET global_account = true, '
        'microgrid_id = NULL '
        'FROM wallet '
        'WHERE sales_account.id = wallet.sales_account_id AND '
        'wallet.negative_permitted = true;'
    )
    logger.info('Converted %d no-limit accounts into global sales accounts' % (
        res.rowcount))
    op.create_foreign_key(u'sales_accounts_users_sales_account_id_fkey',
                          'sales_accounts_users', 'sales_account',
                          ['sales_account_id'], ['id'])
    op.create_foreign_key(u'user_api_sales_account_id_fkey',
                          'user', 'sales_account',
                          ['api_sales_account_id'], ['id'])

    res = conn.execute('UPDATE wallet '
                       'SET grid_id = NULL '
                       'WHERE sales_account_id != NULL')
    logger.info('Set grid_id = NULL for %d sales account wallets' % (res.rowcount))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.44 to 0.43."""
    raise SystemExit("Downgrading from 0.44 to 0.43 is not supported")
