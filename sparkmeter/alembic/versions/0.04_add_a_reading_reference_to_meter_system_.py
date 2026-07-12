# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Add a reading reference to meter system info.

Revision ID: 0.04
Revises: 0.03
Create Date: 2015-09-25 13:05:32.597192

"""

import logging
from builtins import str

import sqlalchemy as sa
from alembic import op
from sqlalchemy import sql

from sparkmeter.database.types import UUIDType

revision = "0.04"
down_revision = "0.03"
logger = logging.getLogger()


def upgrade():  # pragma: nocoverage
    """Upgrade the database schema from 0.03 to 0.04."""
    op.add_column("meter_system_info", sa.Column("reading_id", UUIDType(binary=True), nullable=True))

    # This will make the whole migration a lot faster
    op.execute("""
        CREATE INDEX reading_heartbeat_start ON reading(heartbeat_start);""")

    # 1) Get a list of all meters in the system
    conn = op.get_bind()
    res = conn.execute(
        sql.text("""
        SELECT DISTINCT code FROM meter ORDER BY code;""")
    )

    for (meter_code,) in res:
        logger.info("Setting latest reading for %s" % (meter_code,))
        # 2) For each meter, get the latest reading
        res = conn.execute(
            sql.text("SELECT id FROM reading WHERE meter = :meter ORDER BY heartbeat_start DESC LIMIT 1;"),
            meter=str(meter_code),
        )
        row = res.first()
        if row is None:
            reading_id = None
        else:
            reading_id = row[0]
        # 3) Update the meter_system_info with the latest reading.
        conn.execute(
            sql.text(
                "UPDATE meter_system_info "
                "SET reading_id = :reading_id "
                "FROM meter "
                "WHERE meter.system_info_id = meter_system_info.id AND "
                "meter.code = :meter;"
            ),
            reading_id=reading_id,
            meter=meter_code,
        )

    # Remove temporary migration index
    op.execute("""
        DROP INDEX reading_heartbeat_start;""")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.04 to 0.03."""
    op.drop_column("meter_system_info", "reading_id")
