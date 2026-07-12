# Copyright (C) 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
"""Add the SM16R.

Revision ID: 0.70
Revises: 0.69
Create Date: 2019-05-16 11:19:27.332972

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.misc.uuidutils import as_uuid

revision = "0.70"
down_revision = "0.69"

logger = logging.getLogger()

ModelHelper = sa.Table(
    "meter_models",
    sa.MetaData(),
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
    sa.Column("name", sa.String(), unique=True, nullable=False),
    sa.Column("inrush_limit", sa.DECIMAL(), nullable=False),
    sa.Column("continuous_limit", sa.DECIMAL(), nullable=False),
    sa.Column("scalars_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meter_scalars.id"), nullable=False),
    sa.Column("enabled", sa.BOOLEAN(), default=True, nullable=False),
    schema="public",
)


def upgrade():
    """Upgrade the database schema from 0.69 to 0.70."""
    result = op.get_bind().execute(ModelHelper.select().where(ModelHelper.c.name == "SM16R")).scalar()
    if not result:
        logger.debug("SM16R not found. Inserting.")
        op.bulk_insert(
            ModelHelper,
            [
                {
                    "id": as_uuid("SM16R"),
                    "name": "SM16R",
                    "continuous_limit": 16.0,
                    "inrush_limit": 19.0,
                    "scalars_id": as_uuid("2x"),
                    "enabled": True,
                }
            ],
        )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.70 to 0.69."""
