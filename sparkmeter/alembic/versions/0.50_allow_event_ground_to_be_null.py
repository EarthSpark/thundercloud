# Copyright (C) 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Allow event ground to be NULL.

Revision ID: 0.50
Revises: 0.49
Create Date: 2017-06-27 10:45:37.230500

"""

import logging

from alembic import op

revision = "0.50"
down_revision = "0.49"
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.49 to 0.50."""
    op.alter_column("event", "ground_id", nullable=True)

    conn = op.get_bind()
    res = conn.execute("UPDATE event SET ground_id = NULL WHERE event_type = 'tariff-power-limit-changed'")
    logger.info("Set ground to NULL of %r events" % (res.rowcount,))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.50 to 0.49."""
    raise SystemExit("Downgrading from 0.50 to 0.49 not supported")
