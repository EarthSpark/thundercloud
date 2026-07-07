# Copyright (C) 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Add config parameter.

Revision ID: 0.55
Revises: 0.54
Create Date: 2017-12-28 12:34:25.938285

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0.55'
down_revision = '0.54'


def upgrade():
    """Upgrade the database schema from 0.54 to 0.55."""
    op.create_table(
        'config_parameter',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=True),
        sa.Column('value_type', sa.String(), nullable=True),
        sa.Column('ground_id', postgresql.UUID(), nullable=True),
        sa.Column('last_modified', sa.DateTime(), nullable=True),
        sa.Column('updated_by_id', postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['ground_id'], ['public.ground.id'], ),
        sa.ForeignKeyConstraint(['updated_by_id'], ['public.user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.55 to 0.54."""
    raise SystemExit("Downgrading from 0.55 to 0.54 not supported")
