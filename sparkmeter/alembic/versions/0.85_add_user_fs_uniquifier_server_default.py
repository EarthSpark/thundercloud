# Copyright (C) 2013-2026 SparkMeter, Inc.
# All Rights Reserved.
"""add a server default to user.fs_uniquifier.

0.83 made the column NOT NULL with no default. Grounds still on 0.82 sync
users up through SymmetricDS without it, so those inserts failed in the cloud.
The default matches the expression 0.83 backfilled existing rows with.

Revision ID: 0.85
Revises: 0.84
Create Date: 2026-10-08

"""

import sqlalchemy as sa
from alembic import op

revision = "0.85"
down_revision = "0.84"


def upgrade():
    """Upgrade the database schema from 0.84 to 0.85."""
    op.alter_column(
        "user",
        "fs_uniquifier",
        existing_type=sa.String(length=255),
        existing_nullable=False,
        server_default=sa.text("replace(uuid_generate_v4()::text, '-', '')"),
    )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.85 to 0.84."""
    op.alter_column(
        "user",
        "fs_uniquifier",
        existing_type=sa.String(length=255),
        existing_nullable=False,
        server_default=None,
    )
