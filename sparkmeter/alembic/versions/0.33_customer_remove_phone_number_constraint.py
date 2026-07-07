# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""customer: Remove phone number constraint.

Revision ID: 0.33
Revises: 0.32
Create Date: 2016-05-31 11:06:29.239818

"""

from alembic import op

revision = '0.33'
down_revision = '0.32'


def upgrade():
    """Upgrade the database schema from 0.32 to 0.33."""
    op.drop_constraint('customer_phone_number_unique', 'customer')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.33 to 0.32."""
    op.create_unique_constraint('customer_phone_number_unique', 'customer', ['phone_number'])
