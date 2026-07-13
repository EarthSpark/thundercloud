# Copyright (C) 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Create inrush tables and map existing meters..

Revision ID: 0.67
Revises: 0.66
Create Date: 2018-11-05 09:55:22.565976

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm.session import Session

from sparkmeter.alembic.migrationutils import create_synced_table, force_table_reload_if_exists
from sparkmeter.config.configdict import config
from sparkmeter.database.sync import SYNC_CHANNEL_METER
from sparkmeter.exceptions import MeterError
from sparkmeter.meter.meterutils import ModelMapper, merge_local_meter_models, rekey_serial
from sparkmeter.misc.uuidutils import as_uuid

revision = "0.67"
down_revision = "0.66"

logger = logging.getLogger()

meter_scalars = [
    {
        "id": as_uuid("2x"),
        "name": "2x",
        "frequency_scalar": 0.01,
        "voltage_scalar": 0.01,
        "current_scalar": 0.002,
        "energy_scalar": 0.00003125,
        "power_scalar": 2.0,
        "power_factor_scalar": 0.001,
    },
    {
        "id": as_uuid("4x"),
        "name": "4x",
        "frequency_scalar": 0.01,
        "voltage_scalar": 0.01,
        "current_scalar": 0.004,
        "energy_scalar": 0.00003125,
        "power_scalar": 4.0,
        "power_factor_scalar": 0.001,
    },
]

scalars_lookup = {scalar["name"]: scalar["id"] for scalar in meter_scalars}

meter_models = [
    {
        "id": as_uuid("SM5R"),
        "name": "SM5R",
        "inrush_limit": 12.0,
        "continuous_limit": 6.0,
        "scalars_id": scalars_lookup["2x"],
        "enabled": True,
    },
    {
        "id": as_uuid("SM5XR"),
        "name": "SM5XR",
        "inrush_limit": 12.0,
        "continuous_limit": 6.0,
        "scalars_id": scalars_lookup["2x"],
        "enabled": False,
    },
    {
        "id": as_uuid("SM15R"),
        "name": "SM15R",
        "inrush_limit": 20.0,
        "continuous_limit": 20.0,
        "scalars_id": scalars_lookup["2x"],
        "enabled": True,
    },
    {
        "id": as_uuid("SM20R"),
        "name": "SM20R",
        "inrush_limit": 20.0,
        "continuous_limit": 20.0,
        "scalars_id": scalars_lookup["2x"],
        "enabled": True,
    },
    {
        "id": as_uuid("SM20XR"),
        "name": "SM20XR",
        "inrush_limit": 50.0,
        "continuous_limit": 20.0,
        "scalars_id": scalars_lookup["2x"],
        "enabled": False,
    },
    {
        "id": as_uuid("SM60R"),
        "name": "SM60R",
        "inrush_limit": 61.0,
        "continuous_limit": 61.0,
        "scalars_id": scalars_lookup["2x"],
        "enabled": True,
    },
    {
        "id": as_uuid("SM60RP"),
        "name": "SM60RP",
        "inrush_limit": 61.0,
        "continuous_limit": 61.0,
        "scalars_id": scalars_lookup["2x"],
        "enabled": True,
    },
    {
        "id": as_uuid("SM100E"),
        "name": "SM100E",
        "inrush_limit": 100.0,
        "continuous_limit": 100.0,
        "scalars_id": scalars_lookup["2x"],
        "enabled": True,
    },
    {
        "id": as_uuid("SM200E"),
        "name": "SM200E",
        "inrush_limit": 200.0,
        "continuous_limit": 200.0,
        "scalars_id": scalars_lookup["4x"],
        "enabled": True,
    },
]


MeterHelper = sa.Table(
    "meter",
    sa.MetaData(),
    sa.Column("id", postgresql.UUID(), primary_key=True),
    sa.Column("serial", sa.String()),
    sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
)


def upgrade():  # pragma: nocoverage
    """Upgrade the database schema from 0.66 to 0.67."""
    scalars_table = create_synced_table(
        "meter_scalars",
        SYNC_CHANNEL_METER,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), unique=True),
        sa.Column("frequency_scalar", sa.DECIMAL(), nullable=False),
        sa.Column("voltage_scalar", sa.DECIMAL(), nullable=False),
        sa.Column("current_scalar", sa.DECIMAL(), nullable=False),
        sa.Column("energy_scalar", sa.DECIMAL(), nullable=False),
        sa.Column("power_scalar", sa.DECIMAL(), nullable=False),
        sa.Column("power_factor_scalar", sa.DECIMAL(), nullable=False),
        schema="public",
    )

    op.bulk_insert(scalars_table, meter_scalars)

    models_table = create_synced_table(
        "meter_models",
        SYNC_CHANNEL_METER,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), unique=True, nullable=False),
        sa.Column("inrush_limit", sa.DECIMAL(), nullable=False),
        sa.Column("continuous_limit", sa.DECIMAL(), nullable=False),
        sa.Column(
            "scalars_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meter_scalars.id"), nullable=False
        ),
        sa.Column("enabled", sa.BOOLEAN(), default=True, nullable=False),
        schema="public",
    )

    op.add_column("meter", sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("meter_model_id_fkey", "meter", "meter_models", ["model_id"], ["id"])

    conn = op.get_bind()
    meters = conn.execute(MeterHelper.select())
    # Always run on ground since the `CURRENT_LIMIT`s are only known there.
    #  However, if there are no meters, assume that this is a new system
    #  without any special CURRENT_LIMIT values and proceed.
    should_populate_models = not config["HEROKU"] or meters.rowcount == 0
    if should_populate_models:
        logger.info("Merging models with local current limits")
        models = merge_local_meter_models(meter_models, config["CURRENT_LIMIT"])
        mapper = ModelMapper(models)
        meter_updates = []
        for meter in meters:
            # This loop only runs on the ground since the cloud reaches it when no meters are present.
            try:
                model = mapper.get_serial_model(meter.serial)
                to_change = {}
                # If this meter model should be migrated to an X-variant, do so.
                if config["CURRENT_LIMIT"].get(model["name"], 1.0) > model["inrush_limit"]:
                    model = mapper.get_x_model(model["name"])
                    to_change["serial"] = rekey_serial(meter.serial, model["name"])
                    logger.info('Rekeying serial "%s" to "%s"', meter.serial, to_change["serial"])
                to_change["model_id"] = model["id"]
                meter_updates.append((meter, model, to_change))
                model["enabled"] = True
            except MeterError as me:
                logger.exception(
                    'Could not map meter with ID "%s" and serial "%s" to a model. %s',
                    meter.id,
                    meter.serial,
                    me,
                )
        logger.info("Inserting merged models")
        op.bulk_insert(models_table, models)
        session = Session(bind=conn)
        if not config["HEROKU"]:  # Never run these commands on the cloud
            force_table_reload_if_exists(models_table.name, "cloud", "ground-meter-channel", session)
            for meter, model, values in meter_updates:
                conn.execute(MeterHelper.update().where(MeterHelper.c.id == meter.id).values(**values))
                logger.info(
                    'Mapped meter with serial "%s" to model "%s"',
                    to_change.get("serial", meter.serial),
                    model["name"],
                )
            force_table_reload_if_exists(MeterHelper.name, "cloud", "ground-meter-channel", session)
            logger.info("Resetting power limit for migrated meters.")
            conn.execute(
                """UPDATE meter_system_info
                SET current_user_power_limit = NULL
                FROM meter
                WHERE meter.id=meter_id
                AND NOT meter.model_id IS NULL
                """
            )


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.67 to 0.66."""
    logger.warning("Downgrading is not possible")
