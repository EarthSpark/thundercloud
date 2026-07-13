# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""event: Add a microgrid reference.

Revision ID: 0.29
Revises: 0.28
Create Date: 2016-04-22 18:15:50.259696

"""

import datetime
import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.misc.uuidutils import as_uuid

revision = "0.29"
down_revision = "0.28"
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.28 to 0.29."""
    op.add_column("event", sa.Column("microgrid_id", postgresql.UUID(), nullable=True))

    conn = op.get_bind()
    results = conn.execute("UPDATE event SET microgrid_id = microgrid.id FROM microgrid;")
    logger.info("Updated %r events" % (results.rowcount,))

    op.alter_column("event", "microgrid_id", nullable=False)
    op.create_foreign_key("event_microgrid_id_fkey", "event", "microgrid", ["microgrid_id"], ["id"])


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.29 to 0.28."""
    op.drop_constraint("event_microgrid_id_fkey", "event", type_="foreignkey")
    op.drop_column("event", "microgrid_id")


def test_defaults():
    conn = op.get_bind()
    conn.execute(
        sa.sql.text("""INSERT INTO event VALUES (
        :id, :last_update, :needs_sync, :last_sync,
        :timestamp, :event_type, :object_id, :object_table, :processed, :microgrid_id)"""),
        id=as_uuid("global-event"),
        last_update=None,
        needs_sync=True,
        last_sync=None,
        timestamp=datetime.datetime(2017, 6, 6),
        event_type="tariff-power-limit-changed",
        object_id="0ecfb15c-9d6b-4583-bafa-954604685b1b",  # Limye
        object_table="tariff",
        processed=False,
        microgrid_id="a6680c80-b159-11e4-b35e-002d9826d412",
    )
