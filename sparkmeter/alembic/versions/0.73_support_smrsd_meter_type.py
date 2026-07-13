# Copyright (C) 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
"""Support SMRSD meter type.

Revision ID: 0.73
Revises: 0.72
Create Date: 2019-09-08 11:19:27.332972

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.misc.uuidutils import as_uuid

revision = "0.73"
down_revision = "0.72"

logger = logging.getLogger()


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
    """Upgrade the database schema from 0.72 to 0.73."""
    result = op.get_bind().execute(ModelHelper.select().where(ModelHelper.c.name == "SMRSD")).scalar()
    if not result:
        logger.debug("SMRSD not found. Inserting.")
        op.bulk_insert(
            ModelHelper,
            [
                {
                    "id": as_uuid("SMRSD"),
                    "name": "SMRSD",
                    "continuous_limit": 61.0,
                    "inrush_limit": 81.0,
                    "phase_count": 1,
                    "scalars_id": as_uuid("2x"),
                    "enabled": True,
                }
            ],
        )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.73 to 0.72."""
