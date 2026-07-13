# Copyright (C) 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
"""Daily energy limit default values.

Revision ID: 0.76
Revises: 0.75
Create Date: 2019-11-26 16:40:33.611349

"""

import sqlalchemy as sa
from alembic import op

revision = "0.76"
down_revision = "0.75"


def upgrade():
    """Upgrade the database schema from 0.75 to 0.76."""
    # These updates will only impact tariffs that don't have energy limiting enabled, so they won't cause
    #  changes to customer meter operation
    op.execute(
        """
        UPDATE tariff
        SET daily_energy_limit_enabled = false
        WHERE daily_energy_limit_enabled IS NULL;
        """
    )
    op.execute(
        """
        UPDATE tariff
        SET daily_energy_limit_reset_hour = 0
        WHERE daily_energy_limit_reset_hour IS NULL;
        """
    )
    op.execute(
        """
        UPDATE tariff
        SET daily_energy_limit_value = 0.0
        WHERE daily_energy_limit_value IS NULL;
        """
    )
    op.alter_column("tariff", "daily_energy_limit_enabled", existing_type=sa.Boolean(), nullable=False)
    op.alter_column("tariff", "daily_energy_limit_reset_hour", existing_type=sa.Integer(), nullable=False)
    op.alter_column("tariff", "daily_energy_limit_value", existing_type=sa.Float(), nullable=False)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.76 to 0.75."""
    op.alter_column("tariff", "daily_energy_limit_value", existing_type=sa.Float(), nullable=True)
    op.alter_column("tariff", "daily_energy_limit_reset_hour", existing_type=sa.Integer(), nullable=True)
    op.alter_column("tariff", "daily_energy_limit_enabled", existing_type=sa.Boolean(), nullable=True)
