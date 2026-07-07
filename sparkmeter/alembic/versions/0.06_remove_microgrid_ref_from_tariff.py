# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Remove microgrid ref from tariff.

Revision ID: 0.06
Revises: 0.05
Create Date: 2015-10-28 10:32:50.093906

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0.06'
down_revision = '0.05'


def upgrade():
    """Upgrade the database schema from 0.05 to 0.06."""
    op.drop_constraint(u'tariff_microgrid_id_fkey', 'tariff', type_='foreignkey')
    op.drop_column('tariff', 'microgrid_id')


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.06 to 0.05."""
    op.add_column('tariff', sa.Column('microgrid_id', postgresql.UUID(), autoincrement=False, nullable=False))
    op.create_foreign_key(u'tariff_microgrid_id_fkey', 'tariff', 'microgrid', ['microgrid_id'], ['id'])
