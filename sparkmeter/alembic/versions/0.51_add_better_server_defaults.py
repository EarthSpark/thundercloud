# Copyright (C) 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""add better server defaults.

Revision ID: 0.51
Revises: 0.50
Create Date: 2017-07-31 18:18:44.439741

"""

from alembic import op
from sqlalchemy import func
from sqlalchemy.dialects import postgresql

revision = "0.51"
down_revision = "0.50"

TABLES = [
    "address",
    "customer",
    "dashboard_daily_tariff_summary",
    "event",
    "ground",
    "ground_private",
    "grounds_addresses",
    "meter",
    "meter_billing",
    "meter_config",
    "meter_system_info",
    "meter_tag",
    "meters_tags",
    "reading",
    "role",
    "roles_users",
    "sales_account",
    "sales_accounts_users",
    "sms_config",
    "sms_message",
    "sparkmac_node",
    "tariff",
    "transaction_sources",
    "transactions",
    "user",
    "users_grounds",
    "wallet",
]


def upgrade():
    """Upgrade the database schema from 0.50 to 0.51."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    for table in TABLES:
        op.alter_column(
            table,
            "id",
            existing_type=postgresql.UUID(),
            nullable=False,
            server_default=func.uuid_generate_v4(),
        )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.51 to 0.50."""
    raise SystemExit("Downgrading from 0.51 to 0.50 not supported")
