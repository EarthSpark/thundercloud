# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""meter-system-info: remove packet request/response.

Revision ID: 0.47
Revises: 0.46
Create Date: 2016-08-29 18:01:31.091926

"""

from alembic import op

revision = "0.47"
down_revision = "0.46"


def upgrade():
    """Upgrade the database schema from 0.46 to 0.47."""
    op.drop_column("meter_system_info", "packet_request")
    op.drop_column("meter_system_info", "packet_response")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.47 to 0.46."""
    raise SystemExit("Downgrading from 0.47 to 0.46 is not supported")
