# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""messages: Add microgrid reference.

Revision ID: 0.46
Revises: 0.45
Create Date: 2016-08-29 18:01:31.091926

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0.46"
down_revision = "0.45"
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.45 to 0.46."""
    op.add_column("sms_message", sa.Column("microgrid_id", postgresql.UUID(), autoincrement=False))
    conn = op.get_bind()
    res = conn.execute("UPDATE sms_message SET microgrid_id = microgrid.id FROM microgrid;")
    logger.info("Set microgrid of %r sms_message" % (res.rowcount,))


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.46 to 0.45."""
    op.drop_column("sms_message", "microgrid_id")
