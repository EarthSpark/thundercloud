# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Add needs_sync indexes.

Revision ID: 0.10
Revises: 0.09
Create Date: 2016-01-07 12:49:57.451514

"""

from alembic import op
from sqlalchemy import sql
from sqlalchemy.sql.expression import text

revision = "0.10"
down_revision = "0.09"


def has_index(index):
    """Check if an index exist in the database."""
    conn = op.get_bind()
    res = conn.execute(
        sql.text("""SELECT COUNT(indexname) FROM pg_indexes WHERE indexname = :index;"""), index=index
    )
    return list(res)[0][0] == 1


def upgrade():
    """Upgrade the database schema from 0.09 to 0.10."""
    if not has_index("reading_needs_sync_true"):
        op.create_index(
            "reading_needs_sync_true",
            "reading",
            ["needs_sync"],
            unique=False,
            postgresql_where=text("needs_sync = TRUE"),
        )
    if not has_index("transaction_needs_sync_true"):
        op.create_index(
            "transaction_needs_sync_true",
            "transactions",
            ["needs_sync"],
            unique=False,
            postgresql_where=text("needs_sync = TRUE"),
        )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.10 to 0.09."""
    op.drop_index("reading_needs_sync_true", table_name="reading")
    op.drop_index("transaction_needs_sync_true", table_name="transactions")
