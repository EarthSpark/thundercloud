# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Add an API user.

Revision ID: 0.20
Revises: 0.19
Create Date: 2016-04-06 11:20:29.150372

"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.misc.uuidutils import as_uuid

revision = '0.25'
down_revision = '0.24'


def upgrade():
    """Upgrade the database schema from 0.24 to 0.25."""
    op.add_column('user', sa.Column('vendor_id', postgresql.UUID(), nullable=True))
    op.create_foreign_key(u'user_vendor_id_fkey', 'user', 'user', ['vendor_id'], ['id'])
    conn = op.get_bind()
    conn.execute(
        sa.sql.text("""INSERT INTO role VALUES (
        :id, :last_update, :needs_sync, :last_sync, :name, :description)"""),
        id=uuid.UUID('000000000-0000-0000-0001-00000000004'),
        last_update=None, needs_sync=True, last_sync=None,
        name='api', description='')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.25 to 0.24."""
    op.drop_constraint(u'user_vendor_id_fkey', 'user', type_='foreignkey')
    op.drop_column(u'user', 'vendor_id')


def test_defaults():
    """Add an API user for the unittests."""
    conn = op.get_bind()
    microgrid_id = conn.execute('SELECT id FROM microgrid;').fetchone()[0]
    vendor_role_id = conn.execute('SELECT id FROM role WHERE name = \'vendor\';').fetchone()[0]
    api_role_id = conn.execute('SELECT id FROM role WHERE name = \'api\';').fetchone()[0]
    vendor_id = as_uuid('api-user-vendor')
    api_user_id = as_uuid('api-user')

    # Vendor w/ wallets
    for wallet_type in ['debt', 'credit']:
        wallet_id = as_uuid(wallet_type, vendor_id)
        conn.execute(
            sa.sql.text("""INSERT INTO wallet VALUES (
            :id, :last_update, :needs_sync, :last_sync,
            :meter_id, :microgrid_id, :user_id, :wallet_type, :value, :negative_permitted)"""),
            id=wallet_id,
            last_update=None, needs_sync=True, last_sync=None,
            meter_id=None,
            microgrid_id=None,
            user_id=vendor_id,
            wallet_type=wallet_type,
            value=0,
            negative_permitted=False,
        )
    data = [
        (vendor_id, 'api-vendor', 'api-vendor@example.com', None, vendor_role_id),
        (api_user_id, 'api-user', None, vendor_id, api_role_id)
    ]
    for user_id, username, email, vendor_id, role_id in data:
        conn.execute(
            sa.sql.text("""INSERT INTO "user" VALUES (
            :id, :last_update, :needs_sync, :last_sync, :username, :password,
            :email, :active, :locale, :microgrid_id, :markup, :vendor_id)"""),
            id=user_id,
            last_update=None, needs_sync=True, last_sync=None,
            username=username,
            password='$2a$12$5dvgOSHS3.St0vlrffQ2JOSabs4fLF1R1V3oQ6o/nESp4fYbC2uju',
            email=email,
            active=True,
            locale='en_US',
            microgrid_id=microgrid_id,
            markup=0,
            vendor_id=vendor_id,
        )
        conn.execute(
            sa.sql.text("""INSERT INTO roles_users VALUES (
            :id, :last_update, :needs_sync, :last_sync, :role_id, :user_id)"""),
            id=as_uuid(user_id, role_id),
            last_update=None, needs_sync=True, last_sync=None,
            user_id=user_id,
            role_id=role_id,
        )

    conn.execute(
        sa.sql.text("""INSERT INTO transactions (id, last_update, needs_sync, last_sync, microgrid_id,
                         user_id, created, state, origin, amount, acct_type, from_wallet_id,
                         to_wallet_id, reference_id, external_id, memo, source_id, error)
      VALUES ('3b10873e-002d-4d30-9516-9b7e74f7801e', NULL, false,
              '2015-09-03 23:01:57.800063',
              'a6680c80-b159-11e4-b35e-002d9826d412',
              '42f9bd80-fa6d-11e4-a575-00617b7c44e1',
              '2015-02-16 21:38:15.752043', 'processed', 'system', 85, 'credit',
              '73f3a4f0-de22-4609-9bdc-d64c381c5d6d',
              :to_wallet_id, NULL, NULL, NULL, NULL, NULL);"""),
        to_wallet_id=as_uuid('credit', vendor_id)
    )
