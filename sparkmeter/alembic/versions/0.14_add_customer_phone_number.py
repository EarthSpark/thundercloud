# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Add customer phone number.

Revision ID: 0.14
Revises: 0.13
Create Date: 2016-02-12 09:26:09.388309

"""

import sqlalchemy as sa
from alembic import op

revision = '0.14'
down_revision = '0.13'


def upgrade():
    """Upgrade the database schema from 0.13 to 0.14."""
    op.add_column('customer', sa.Column('phone_number', sa.String(), nullable=True))
    op.add_column('customer', sa.Column('phone_number_verified', sa.Boolean(), nullable=False,
                                        server_default=sa.false()))
    op.create_unique_constraint('customer_phone_number_unique', 'customer', ['phone_number'])


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.14 to 0.13."""
    op.drop_column('customer', 'phone_number')
    op.drop_column('customer', 'phone_number_verified')
    op.drop_constraint(u'customer_phone_number_unique')


def test_defaults():
    conn = op.get_bind()
    conn.execute(
        "UPDATE customer "
        "SET phone_number = '+15555550101', phone_number_verified = true "
        "WHERE id = 'fb58f722-9e1a-4ea1-9606-1e3417e91c82'")
    conn.execute(
        "UPDATE customer "
        "SET phone_number = '+15555550102', phone_number_verified = true "
        "WHERE id = '8cc67eb0-51d5-4ab3-9ee3-2be9bfc1f181'")
    conn.execute(
        "UPDATE customer "
        "SET phone_number = '+15555550103', phone_number_verified = false "
        "WHERE id = 'ace82e9e-b18b-4e52-9fc3-23cf46b80302'")
