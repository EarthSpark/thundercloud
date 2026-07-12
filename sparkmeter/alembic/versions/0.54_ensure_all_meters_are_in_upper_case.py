# Copyright (C) 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Ensure all meters are in upper-case.

Revision ID: 0.54
Revises: 0.53
Create Date: 2017-11-03 10:29:27.543204

"""

from alembic import op

revision = "0.54"
down_revision = "0.53"


def upgrade():
    """Upgrade the database schema from 0.53 to 0.54."""
    conn = op.get_bind()
    conn.execute("UPDATE meter SET serial = UPPER(serial);")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.54 to 0.53."""
    raise SystemExit("Downgrading from 0.54 to 0.53 not supported")
