# Copyright (C) 2013-2020 SparkMeter, Inc.
# All Rights Reserved.
"""SMRPI meter model support.

Revision ID: 0.81
Revises: 0.80
Create Date: 2020-08-17 11:00:42.902466

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.misc.uuidutils import as_uuid

revision = "0.81"
down_revision = "0.80"

ModelHelper = sa.Table(
    "meter_models",
    sa.MetaData(),
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("name", sa.String(), unique=True, nullable=False),
    sa.Column("inrush_limit", sa.DECIMAL(), nullable=False),
    sa.Column("continuous_limit", sa.DECIMAL(), nullable=False),
    sa.Column("phase_count", sa.Integer(), nullable=False),
    sa.Column("scalars_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meter_scalars.id"), nullable=False),
    sa.Column("enabled", sa.BOOLEAN(), default=True, nullable=False),
    schema="public",
)


def upgrade():
    """Upgrade the database schema from 0.80 to 0.81."""
    models_to_insert = []
    for model_name in ("SMRPI", "SMRPIRF", "SMRPIPLC"):
        result = op.get_bind().execute(ModelHelper.select().where(ModelHelper.c.name == model_name)).scalar()
        if not result:
            models_to_insert.append(
                {
                    "id": as_uuid(model_name),
                    "name": model_name,
                    "continuous_limit": 61.0,
                    "inrush_limit": 81.0,
                    "phase_count": 3,
                    "scalars_id": as_uuid("2x"),
                    "enabled": True,
                }
            )
    if models_to_insert:
        op.bulk_insert(ModelHelper, models_to_insert)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.81 to 0.80."""
