# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Move Customer ID to a reference.

Revision ID: 0.20
Revises: 0.19
Create Date: 2016-03-29 11:56:41.783598

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0.20"
down_revision = "0.19"


def upgrade():
    """Upgrade the database schema from 0.19 to 0.20."""
    op.add_column("customer", sa.Column("meter_id", postgresql.UUID(), nullable=True))

    conn = op.get_bind()
    res = conn.execute("""
        UPDATE customer SET meter_id = meter.id
          FROM meter
         WHERE meter.customer_id = customer.id""")
    logging.info("Set meter of %r customers" % (res.rowcount,))
    op.alter_column("customer", "meter_id", nullable=False)

    op.create_foreign_key(None, "customer", "meter", ["meter_id"], ["id"])
    op.drop_constraint("meter_customer_id_fkey", "meter", type_="foreignkey")
    op.drop_column("meter", "customer_id")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.20 to 0.19."""
    op.add_column("meter", sa.Column("customer_id", postgresql.UUID(), autoincrement=False, nullable=True))
    conn = op.get_bind()
    res = conn.execute("""
        UPDATE meter SET customer_id = customer.id
          FROM customer
         WHERE customer.meter_id = meter.id""")
    logging.info("Set customer of %r meters" % (res.rowcount,))
    op.alter_column("meter", "customer_id", nullable=False)

    op.create_foreign_key("meter_customer_id_fkey", "meter", "customer", ["customer_id"], ["id"])
    op.drop_column("customer", "meter_id")
