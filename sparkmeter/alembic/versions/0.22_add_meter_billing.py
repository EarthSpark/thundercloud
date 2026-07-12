# Copyright (C) 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Add meter_billing.

Revision ID: 0.22
Revises: 0.21
Create Date: 2016-03-30 17:31:26.801402

"""

import logging

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.misc.uuidutils import as_uuid

revision = "0.22"
down_revision = "0.21"
logger = logging.getLogger()


def upgrade():
    """Upgrade the database schema from 0.21 to 0.22."""
    op.create_table(
        "meter_billing",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("needs_sync", sa.Boolean(), nullable=True),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("meter_id", postgresql.UUID(), nullable=False),
        sa.Column("last_plan_payment_date", sa.DateTime(), nullable=True),
        sa.Column("last_cycle_start", sa.DateTime(), nullable=True),
        sa.Column("total_cycle_energy", sa.Float(), nullable=True),
        sa.Column("is_running_plan", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["meter_id"],
            ["meter.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "meters_tariffs",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("needs_sync", sa.Boolean(), nullable=True),
        sa.Column("last_sync", sa.DateTime(), nullable=True),
        sa.Column("meter_id", postgresql.UUID(), nullable=False),
        sa.Column("tariff_id", postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["meter_id"],
            ["meter.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tariff_id"],
            ["tariff.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    conn = op.get_bind()
    results = conn.execute("""
    SELECT meter.id AS meter_id,
           meter_config.tariff_id AS tariff_id,
           meter_system_info.last_plan_payment_date,
           meter_system_info.last_cycle_start,
           meter_system_info.total_cycle_energy,
           meter_system_info.is_running_plan
      FROM meter_system_info, meter_config, meter
    WHERE  meter_system_info.id = meter.system_info_id AND
           meter.config_id = meter_config.id""")
    for result in results:
        query = sa.sql.text("""
        INSERT INTO meter_billing VALUES (
        :id, :last_update, :needs_sync, :last_sync, :meter_id, :last_plan_payment_date,
        :last_cycle_start, :total_cycle_energy, :is_running_plan)
        """)
        values = dict(result._mapping)
        values["id"] = as_uuid(values["meter_id"])
        values["last_update"] = None
        values["needs_sync"] = True
        values["last_sync"] = None
        tariff_id = values.pop("tariff_id")
        conn.execute(query, **values)

        query = sa.sql.text("""
        INSERT INTO meters_tariffs VALUES (
        :id, :last_update, :needs_sync, :last_sync, :meter_id, :tariff_id)
        """)
        values = dict(
            id=as_uuid(values["meter_id"], tariff_id),
            last_update=None,
            needs_sync=True,
            last_sync=None,
            meter_id=values["meter_id"],
            tariff_id=tariff_id,
        )
        conn.execute(query, **values)

    logger.info("Converted %d meter_config & meter_system_info" % (results.rowcount,))
    op.drop_constraint("meter_config_tariff_id_fkey", "meter_config", type_="foreignkey")
    op.drop_column("meter_config", "tariff_id")
    op.drop_column("meter_system_info", "last_cycle_start")
    op.drop_column("meter_system_info", "total_cycle_energy")
    op.drop_column("meter_system_info", "is_running_plan")
    op.drop_column("meter_system_info", "last_plan_payment_date")


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.22 to 0.21."""
    op.add_column(
        "meter_system_info",
        sa.Column("last_plan_payment_date", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "meter_system_info", sa.Column("is_running_plan", sa.BOOLEAN(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "meter_system_info",
        sa.Column(
            "total_cycle_energy",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "meter_system_info",
        sa.Column("last_cycle_start", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "meter_config", sa.Column("tariff_id", postgresql.UUID(), autoincrement=False, nullable=True)
    )

    conn = op.get_bind()
    results = conn.execute("""
    SELECT meter.id AS meter_id,
           meters_tariffs.tariff_id,
           meter_billing.last_plan_payment_date,
           meter_billing.last_cycle_start,
           meter_billing.total_cycle_energy,
           meter_billing.is_running_plan
      FROM meters_tariffs, meter_billing, meter
     WHERE meters_tariffs.meter_id = meter.id AND
           meter_billing.meter_id = meter.id""")
    for result in results:
        query = sa.sql.text("""
        UPDATE meter_system_info SET last_plan_payment_date = :last_plan_payment_date,
                                     last_cycle_start = :last_cycle_start,
                                     total_cycle_energy = :total_cycle_energy,
                                     is_running_plan = :is_running_plan
         FROM meter
        WHERE meter.system_info_id = meter_system_info.id AND
              meter.id = :meter_id
        """)
        values = dict(result._mapping)
        conn.execute(query, **values)

        query = sa.sql.text("""
        UPDATE meter_config SET tariff_id = :tariff_id
          FROM meter
         WHERE meter.config_id = meter_config.id AND
               meter.id = :meter_id
        """)
        values = dict(result._mapping)
        conn.execute(query, **values)

    logger.info("Converted %d meters_tariffs & meter_billing" % (results.rowcount,))
    op.alter_column("meter_config", "tariff_id", nullable=False)
    op.create_foreign_key("meter_config_tariff_id_fkey", "meter_config", "tariff", ["tariff_id"], ["id"])
    op.drop_table("meter_billing")
    op.drop_table("meters_tariffs")
