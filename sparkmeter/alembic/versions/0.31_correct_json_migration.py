# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""json: correct migration columns.

Revision ID: 0.31
Revises: 0.30
Create Date: 2016-05-25 16:22:58.981848

"""

import sqlalchemy as sa
from alembic import op

from sparkmeter.database.columns import JSONString

revision = "0.31"
down_revision = "0.30"

COLUMNS = [
    ("microgrid", "graph"),
    ("microgrid", "status"),
    ("sparkmac_node", "flooding_macs"),
    ("sparkmac_node", "routing_enabled"),
    ("sparkmac_node", "static_routes"),
    ("tariff", "blockrates"),
    ("tariff", "tous"),
    ("transaction_sources", "transaction_metadata"),
]


def upgrade():
    """Upgrade the database schema from 0.30 to 0.31."""
    for table, column in COLUMNS:
        op.alter_column(table, column, existing_type=sa.VARCHAR(), type_=JSONString(), existing_nullable=True)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.31 to 0.30."""
    for table, column in COLUMNS:
        op.alter_column(table, column, existing_type=JSONString(), type_=sa.VARCHAR(), existing_nullable=True)
