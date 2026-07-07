# Copyright (C) 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""adding meter reading unique constraint.

Revision ID: 0.05
Revises: 0.04
Create Date: 2015-10-03 09:29:12.059066

"""

from alembic import op

revision = '0.05'
down_revision = '0.04'


def upgrade():
    """Upgrade the database schema from 0.04 to 0.05."""
    op.execute("""DELETE FROM reading WHERE id IN (
      SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (
          partition BY meter, heartbeat_end ORDER BY id)
      AS rnum from reading) t
    WHERE t.rnum > 1);""")
    op.create_unique_constraint('meter_heartbeat_end_unique', 'reading', ['meter', 'heartbeat_end'])


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.05 to 0.04."""
    op.drop_constraint('meter_heartbeat_end_unique', 'reading', type_='unique')
