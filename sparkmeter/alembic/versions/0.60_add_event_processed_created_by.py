# Copyright (C) 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Add event processed/created_by.

Revision ID: 0.60
Revises: 0.59
Create Date: 2018-03-05 14:36:42.721846

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0.60"
down_revision = "0.59"


def upgrade():
    """Upgrade the database schema from 0.59 to 0.60."""
    op.add_column("event", sa.Column("created_by_id", postgresql.UUID(), nullable=True))
    op.add_column("event", sa.Column("processed_timestamp", sa.DateTime(), nullable=True))
    op.create_foreign_key(None, "event", "user", ["created_by_id"], ["id"])


def downgrade():  # pragma: nocoverage
    op.drop_constraint(None, "event", type_="foreignkey")
    op.drop_column("event", "processed_timestamp")
    op.drop_column("event", "created_by_id")
