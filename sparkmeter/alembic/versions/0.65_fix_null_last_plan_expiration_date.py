# Copyright (C) 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""
Make sure last_plan_expiration_date is not null for any meter that is using
a monthly plan tariff

Revision ID: 0.65
Revises: 0.64
Create Date: 2018-09-20 10:34:00.0000
"""

from alembic import op

revision = '0.65'
down_revision = '0.64'


def upgrade():
    """Upgrade the database schema from 0.64 to 0.65."""
    op.execute("""
        UPDATE meter_billing
        SET last_plan_expiration_date =
            date_trunc('month', last_plan_payment_date + '1 month')
            + (cycle_start_day_of_month - 1) * interval '1 day'
        FROM tariff
        WHERE tariff_id=tariff.id
        AND is_running_plan=true
        AND last_plan_expiration_date IS NULL
        AND last_plan_payment_date IS NOT NULL""")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.65 to 0.64."""
