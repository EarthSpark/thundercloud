# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""user: Access to all sales accounts.

Revision ID: 0.40
Revises: 0.39
Create Date: 2016-09-16 09:34:43.361974

"""

import logging

import sqlalchemy as sa
from alembic import op

from sparkmeter.misc.uuidutils import as_uuid

revision = '0.40'
down_revision = '0.39'
logger = logging.getLogger()


def insert_sales_accounts_users(conn, user_id, sales_account_id):
    """Insert an entry to the sales_accounts_users table."""
    if conn.execute(
            sa.sql.text("SELECT count(*) as count FROM sales_accounts_users "
                        "WHERE user_id = :user_id AND "
                        "sales_account_id = :sales_account_id;"),
            user_id=user_id,
            sales_account_id=sales_account_id).first().count != 0:
        return False

    conn.execute(
        sa.sql.text("INSERT INTO sales_accounts_users (id, user_id, sales_account_id)"
                    " VALUES (:id, :user_id, :sales_account_id)"),
        id=as_uuid(user_id, sales_account_id),
        user_id=user_id,
        sales_account_id=sales_account_id)
    return True


def upgrade():
    """Upgrade the database schema from 0.39 to 0.40."""
    op.add_column(
        'user',
        sa.Column(
            'account_all_access',
            sa.Boolean(), nullable=False,
            server_default=sa.false()
        )
    )
    conn = op.get_bind()
    res = conn.execute(
        'UPDATE "user" SET account_all_access = true '
        'FROM role, roles_users '
        'WHERE roles_users.user_id = "user".id AND '
        'roles_users.role_id = role.id AND '
        'role.name = \'operator\'')
    logger.info('Updated account_all_access for %d operators' % (res.rowcount, ))

    users_with_account_all_access_ids = []
    for result in conn.execute(
            'SELECT "user".id AS user_id, "user".username AS username FROM "user" '
            'WHERE account_all_access = true;'):
        users_with_account_all_access_ids.append((result._mapping['user_id'], result._mapping['username']))

    for result in conn.execute('SELECT id AS sales_account_id, name FROM sales_account;'):
        # Add operator permissions to the System account
        for user_id, username in users_with_account_all_access_ids:
            if insert_sales_accounts_users(conn,
                                           user_id=user_id,
                                           sales_account_id=result.sales_account_id):
                logger.info('Added sales account %r mapping for %r' % (result.name, username,))


def downgrade():  # pragma nocoverage
    """Downgrade the database schema from 0.40 to 0.39."""
    op.drop_column('user', 'account_all_access')
