# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""user: Add API sales account.

Revision ID: 0.35
Revises: 0.34
Create Date: 2016-08-26 18:12:33.990283

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0.35'
down_revision = '0.34'


def upgrade():
    """Upgrade the database schema from 0.34 to 0.35."""
    op.add_column('user', sa.Column('api_sales_account_id', postgresql.UUID(), nullable=True))
    op.create_foreign_key(u'user_api_sales_account_id_fkey', 'user', 'sales_account',
                          ['api_sales_account_id'], ['id'])

    conn = op.get_bind()
    # For each API user with an associated sales account,
    # - delete the sales account user entry
    # - update the user
    for result in conn.execute(
            'SELECT "user".id AS user_id, sales_accounts_users.sales_account_id AS sales_account_id '
            'FROM "user", role, roles_users, sales_accounts_users '
            'WHERE "user".id = sales_accounts_users.user_id AND '
            '"user".id = roles_users.user_id AND '
            'role.id = roles_users.role_id AND '
            'role.name = \'api\';'):
        stmt = ("DELETE FROM sales_accounts_users "
                "WHERE user_id = :user_id")
        conn.execute(sa.sql.text(stmt),
                     user_id=result.user_id)

        stmt = ('UPDATE "user" SET api_sales_account_id = :sales_account_id '
                'WHERE "user".id = :user_id')
        conn.execute(sa.sql.text(stmt),
                     sales_account_id=result.sales_account_id,
                     user_id=result.user_id)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.35 to 0.34."""
    op.drop_constraint(u'user_api_sales_account_id_fkey', 'user', type_='foreignkey')
    op.drop_column(u'user', 'api_sales_account_id')
