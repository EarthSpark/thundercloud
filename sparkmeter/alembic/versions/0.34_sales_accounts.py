# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""sales accounts.

Revision ID: 0.34
Revises: 0.33
Create Date: 2016-06-16 21:45:01.783495

"""

import logging
from builtins import map

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.misc.uuidutils import as_uuid

revision = '0.34'
down_revision = '0.33'
logger = logging.getLogger()


def insert_sales_accounts_users(conn, user_id, sales_account_id):
    """Insert an entry to the sales_accounts_users table."""
    logging.info("- Adding SalesAccount<>User mapping %s, %s" % (
        user_id, sales_account_id
    ))
    conn.execute(
        sa.sql.text("INSERT INTO sales_accounts_users (id, user_id, sales_account_id)"
                    " VALUES (:id, :user_id, :sales_account_id)"),
        id=as_uuid(user_id, sales_account_id),
        user_id=user_id,
        sales_account_id=sales_account_id)


def insert_sales_account(conn, id, **kwargs):
    """Insert an entry to the sales_account table."""

    stmt = ("INSERT INTO sales_account "
            "(id, name, active, system, markup, microgrid_id)"
            "VALUES "
            "(:id, :name, :active, :system, :markup, :microgrid_id);")
    sales_account_id = as_uuid(id)
    conn.execute(
        sa.sql.text(stmt),
        id=sales_account_id,
        **kwargs)
    logging.info("- Created SalesAccount %r (%s)" % (kwargs['name'], sales_account_id))
    return sales_account_id


def migrate_users(conn):
    """Migrate users."""
    # For each user that has a wallet
    for result in conn.execute(
            'SELECT DISTINCT "user".id AS id, '
            '"user".username AS username, '
            '"user".markup AS markup, '
            '"user".microgrid_id AS microgrid_id '
            'FROM "user", wallet '
            'WHERE "user".id = wallet.user_id;'):
        subres = conn.execute(
            sa.sql.text('SELECT id FROM wallet WHERE wallet.user_id = :user_id;'),
            user_id=result.id,
        )
        wallet_ids = list(map(list, subres))
        n_wallets = conn.execute(
            sa.sql.text('SELECT COUNT(*) '
                        'FROM transactions, "user", wallet '
                        'WHERE ARRAY[from_wallet_id] <@ :wallet_ids OR '
                        'ARRAY[to_wallet_id] <@ :wallet_ids'),
            wallet_ids=wallet_ids,
        )
        if n_wallets.fetchone()[0] == 0:
            logging.info("Deleted wallets for user %r, no transcations" % (result.username, ))
            stmt = "DELETE FROM wallet WHERE ARRAY[id] <@ :wallet_ids;"
            conn.execute(sa.sql.text(stmt),
                         wallet_ids=wallet_ids)
            continue

        logging.info("Migrating wallets for user %r to a sales account" % (result.username, ))

        # Create a Sales Account
        sales_account_id = insert_sales_account(
            conn,
            result.id,
            name="Sales Account for {0.username}".format(result),
            markup=result.markup,
            active=True,
            system=False,
            microgrid_id=result.microgrid_id)

        # Allow that user to sell to that sales account
        insert_sales_accounts_users(conn,
                                    user_id=result.id,
                                    sales_account_id=sales_account_id)

        # Update the user wallets to point to the sales
        stmt = "UPDATE wallet SET sales_account_id = :id WHERE user_id = :user_id;"
        conn.execute(sa.sql.text(stmt),
                     id=sales_account_id,
                     user_id=result.id)
        logging.info("")


def migrate_api_users(conn):
    """Migrate API users."""
    # For each API user with an associated sales account
    for result in conn.execute(
            'SELECT DISTINCT "user".id AS id, "user".username as username, '
            'sales_accounts_users.sales_account_id AS sales_account_id '
            'FROM "user", wallet, sales_accounts_users '
            'WHERE "user".vendor_id = wallet.user_id AND '
            '"user".vendor_id = sales_accounts_users.user_id;'):
        logging.info("Migrating API user %r" % (result.username, ))

        # Allow the API user to sell to the vendors sales account
        insert_sales_accounts_users(
            conn,
            user_id=result.id,
            sales_account_id=result.sales_account_id)


def migrate_microgrids(conn):
    """Migrate microgrids."""
    operator_ids = []
    for result in conn.execute(
            'SELECT "user".id AS user_id FROM "user", roles_users, role '
            'WHERE roles_users.user_id = "user".id AND '
            'roles_users.role_id = role.id AND '
            'role.name = \'operator\''):
        operator_ids.append(result._mapping['user_id'])

    # For each microgrid
    for result in conn.execute('SELECT microgrid.id AS id FROM microgrid'):
        # create a new sales account
        sales_account_id = insert_sales_account(
            conn,
            result.id,
            name="System",
            markup=0,
            active=True,
            system=True,
            microgrid_id=result.id)

        # Update the microgrid wallets to point to the sales
        stmt = "UPDATE wallet SET sales_account_id = :id WHERE microgrid_id = :microgrid_id;"
        conn.execute(sa.sql.text(stmt),
                     id=sales_account_id,
                     microgrid_id=result.id)

        # Add operator permissions to the System account
        for operator_id in operator_ids:
            insert_sales_accounts_users(conn,
                                        user_id=operator_id,
                                        sales_account_id=sales_account_id)


def upgrade():
    """Upgrade the database schema from 0.33 to 0.34."""
    op.create_table(
        'sales_account',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('last_update', sa.DateTime(), nullable=True),
        sa.Column('needs_sync', sa.Boolean(), nullable=True),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('system', sa.Boolean(), nullable=True),
        sa.Column('markup', sa.Float(), nullable=True),
        sa.Column('microgrid_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['microgrid_id'], ['public.microgrid.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_table(
        'sales_accounts_users',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('last_update', sa.DateTime(), nullable=True),
        sa.Column('needs_sync', sa.Boolean(), nullable=True),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('sales_account_id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['sales_account_id'], ['public.sales_account.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['public.user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.add_column('wallet', sa.Column('sales_account_id', postgresql.UUID(), nullable=True))
    op.drop_constraint('wallet_type_unique', 'wallet', type_='unique')
    op.drop_constraint('wallet_references_not_null', 'wallet')
    op.drop_constraint('wallet_references_one_null', 'wallet')

    conn = op.get_bind()
    logging.info("Migrating Users")
    migrate_users(conn)
    logging.info("")

    logging.info("Migrating API Users")
    migrate_api_users(conn)
    logging.info("")

    logging.info("Migrating Microgrid")
    migrate_microgrids(conn)
    logging.info("")

    # 4) Remove broken wallets with dangling user_id references.
    op.drop_column(u'user', 'markup')
    op.drop_column(u'user', 'vendor_id')
    op.drop_column(u'wallet', 'user_id')
    op.drop_column(u'wallet', 'microgrid_id')

    op.create_check_constraint(
        'wallet_references_one_null',
        'wallet',
        'meter_id IS NULL OR sales_account_id IS NULL')

    op.create_check_constraint(
        'wallet_references_not_null',
        'wallet',
        'meter_id IS NOT NULL OR sales_account_id IS NOT NULL')

    op.create_unique_constraint(
        'wallet_type_unique',
        'wallet',
        ['meter_id', 'sales_account_id', 'wallet_type'], schema='public')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.34 to 0.33."""
