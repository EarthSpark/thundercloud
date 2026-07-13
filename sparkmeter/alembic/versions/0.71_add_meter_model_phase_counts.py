# Copyright (C) 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
"""Add meter model phase counts.

Revision ID: 0.71
Revises: 0.70
Create Date: 2019-05-21 14:35:43.378985

"""

import sqlalchemy as sa
from alembic import op

revision = "0.71"
down_revision = "0.70"


def upgrade():
    """Upgrade the database schema from 0.70 to 0.71."""
    # Create the column
    op.add_column("meter_models", sa.Column("phase_count", sa.INTEGER, nullable=False, server_default="1"))
    # Set the phase count for the SM60RP
    op.execute(
        """
        UPDATE meter_models
        SET phase_count = 3, continuous_limit = 61.0
        WHERE name = 'SM60RP';
        """
    )
    # Remove the default value for the column now that all models have defined phases
    op.alter_column("meter_models", "phase_count", server_default=None)
    # Force fresh configs to go out for SM60RPs
    op.execute(
        """
        UPDATE meter_system_info
        SET current_user_power_limit = NULL
        FROM meter
        JOIN meter_models ON meter_models.id = meter.model_id
        WHERE meter_models.name = 'SM60RP'
        AND meter.id = meter_id;
        """
    )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.71 to 0.70."""
    op.drop_column("meter_models", "phase_count")
    # Revert to the power limit workaround that we used prior to this release
    op.execute("UPDATE meter_models SET continuous_limit = 183.0 WHERE name = 'SM60RP'")
