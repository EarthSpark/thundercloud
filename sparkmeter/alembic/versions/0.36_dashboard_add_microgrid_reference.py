# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""dashboard: Add microgrid reference.

Revision ID: 0.36
Revises: 0.35
Create Date: 2016-08-29 18:01:31.091926

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0.36"
down_revision = "0.35"
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.35 to 0.36."""
    op.add_column(
        "dashboard_daily_tariff_summary", sa.Column("microgrid_id", postgresql.UUID(), autoincrement=False)
    )
    conn = op.get_bind()
    res = conn.execute(
        "UPDATE dashboard_daily_tariff_summary SET microgrid_id = microgrid.id FROM microgrid;"
    )
    logger.info("Set microgrid of %r dashboard_daily_tariff_summary" % (res.rowcount,))
    op.alter_column("dashboard_daily_tariff_summary", "microgrid_id", nullable=False)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.36 to 0.35."""
    op.drop_column("dashboard_daily_tariff_summary", "microgrid_id")
