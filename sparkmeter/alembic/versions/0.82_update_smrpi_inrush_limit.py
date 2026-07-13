# Copyright (C) 2013-2021 SparkMeter, Inc.
# All Rights Reserved.
"""Update SMRPI inrush limit.

Revision ID: 0.82
Revises: 0.81
Create Date: 2021-09-21 19:33:36.793303

"""

from alembic import op

revision = "0.82"
down_revision = "0.81"


def upgrade():
    """Upgrade the database schema from 0.81 to 0.82."""
    # Set the new inrush limit for all SMRPI* models
    op.execute(
        """
        UPDATE meter_models
        SET inrush_limit = 101.0
        WHERE name ILIKE 'SMRPI%';
        """
    )
    # Force new configs out to all SMRPIs
    op.execute(
        """
        UPDATE meter_system_info
        SET current_user_power_limit = NULL
        FROM meter
        JOIN meter_models ON meter_models.id = meter.model_id
        WHERE meter_models.name ILIKE 'SMRPI%'
        AND meter.id = meter_id;
        """
    )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.82 to 0.81."""
    op.execute(
        """
        UPDATE meter_models
        SET inrush_limit = 81.0
        WHERE name ILIKE 'SMRPI%';
        """
    )
    # Force new configs out to all SMRPIs
    op.execute(
        """
        UPDATE meter_system_info
        SET current_user_power_limit = NULL
        FROM meter
        JOIN meter_models ON meter_models.id = meter.model_id
        WHERE meter_models.name ILIKE 'SMRPI%'
        AND meter.id = meter_id;
        """
    )
