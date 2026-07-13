# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Add tariff summary dashboard.

Revision ID: 0.18
Revises: 0.17
Create Date: 2016-02-23 11:57:24.571052

"""

import logging

import sqlalchemy as sa
from alembic import op

from sparkmeter.database.types import UUIDType

revision = "0.18"
down_revision = "0.17"
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.17 to 0.18."""
    op.create_table(
        "dashboard_daily_tariff_summary",
        sa.Column("id", UUIDType(binary=True), nullable=False),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("needs_sync", sa.Boolean(), nullable=True),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("tariff_id", UUIDType(binary=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("transaction_amount", sa.Integer(), nullable=False),
        sa.Column("transaction_count", sa.Integer(), nullable=False),
        sa.Column("kwh_consumed", sa.Float(), nullable=False),
        sa.Column("customer_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tariff_id"],
            ["tariff.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tariff_id", "date", name="tariff_date_unique"),
    )
    op.create_index(
        "dashboard_daily_tariff_summary_needs_sync_true",
        "dashboard_daily_tariff_summary",
        ["needs_sync"],
        unique=False,
        postgresql_where=sa.text("needs_sync = TRUE"),
    )

    logger.info("Adding a 'meter, heartbeat_start' reading index")
    logger.info("WARNING: This is not fast, it will take ~2 minutes for 12M readings")
    op.create_unique_constraint("meter_heartbeat_start_unique", "reading", ["meter", "heartbeat_start"])

    # We are in a transaction, which the VACUUM cannot run in, so finish it
    # by simply committing.
    conn = op.get_bind()
    conn.execute("COMMIT")

    # Since we have changed the index, update the table statistics so that
    # the query planner knows that it can use the new index.
    logger.info("Running VACCUM ANALYZE for the reading table")
    conn.execute("VACUUM ANALYZE reading")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.18 to 0.17."""
    op.drop_index(
        "dashboard_daily_tariff_summary_needs_sync_true", table_name="dashboard_daily_tariff_summary"
    )
    op.drop_table("dashboard_daily_tariff_summary")
    op.drop_index("meter_heartbeat_start_unique", table_name="reading")
