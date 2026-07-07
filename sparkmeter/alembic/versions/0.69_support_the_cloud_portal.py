# Copyright (C) 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
"""Support the cloud portal.

Revision ID: 0.69
Revises: 0.68
Create Date: 2019-04-15 16:25:30.988094

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0.69'
down_revision = '0.68'


def upgrade():
    """Upgrade the database schema from 0.68 to 0.69."""
    op.add_column(u'user', sa.Column('portal_id', postgresql.UUID(as_uuid=True), nullable=True, unique=True))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.69 to 0.68."""
    op.drop_column('user', 'portal_id')
