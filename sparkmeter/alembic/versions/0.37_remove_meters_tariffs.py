# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Remove meters_tariffs table.

Revision ID: 0.37
Revises: 0.36
Create Date: 2016-03-30 17:31:26.801402

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0.37"
down_revision = "0.36"


def upgrade():
    """Upgrade the database schema from 0.36 to 0.37."""
    op.add_column(
        "meter_billing", sa.Column("tariff_id", postgresql.UUID(), autoincrement=False, nullable=True)
    )

    conn = op.get_bind()
    results = conn.execute("""
    SELECT meter.id AS meter_id,
           meters_tariffs.tariff_id
      FROM meters_tariffs, meter
     WHERE meters_tariffs.meter_id = meter.id""")
    for result in results:
        query = sa.sql.text("""
        UPDATE meter_billing SET tariff_id = :tariff_id
         WHERE meter_billing.meter_id = :meter_id
        """)
        values = dict(result._mapping)
        conn.execute(query, **values)

    op.alter_column("meter_billing", "tariff_id", nullable=False)
    op.drop_table("meters_tariffs")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.37 to 0.36."""
