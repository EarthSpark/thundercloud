# Copyright (C) 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
"""Snapshot support.

Revision ID: 0.77
Revises: 0.76
Create Date: 2019-10-29 13:37:20.500022

"""

import logging
from hashlib import sha256

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from sparkmeter.alembic.migrationutils import create_synced_table
from sparkmeter.database.sync import SYNC_CHANNEL_SNAPSHOT
from sparkmeter.misc.jsonutils import json_dumps, json_loads
from sparkmeter.misc.uuidutils import as_uuid

revision = "0.77"
down_revision = "0.76"

logger = logging.getLogger(__name__)


def upgrade():
    """Upgrade the database schema from 0.76 to 0.77."""
    create_synced_table(
        "snapshot",
        SYNC_CHANNEL_SNAPSHOT,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hash", sa.String(64), unique=True, nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
    )
    empty_id = create_empty_snapshot()
    op.add_column("reading", sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("event", sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("transactions", sa.Column("to_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("transactions", sa.Column("from_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("event_snapshot_id_fkey", "event", "snapshot", ["snapshot_id"], ["id"])
    op.create_foreign_key(
        "transactions_to_snapshot_id_fkey", "transactions", "snapshot", ["to_snapshot_id"], ["id"]
    )
    op.create_foreign_key(
        "transactions_from_snapshot_id_fkey", "transactions", "snapshot", ["from_snapshot_id"], ["id"]
    )
    apply_reading_snapshots(empty_id)
    apply_event_snapshots(empty_id)
    apply_transaction_snapshots(empty_id)


def downgrade():  # pragma: nocoverage
    """Downgrade the database schema from 0.77 to 0.76."""
    op.execute("DROP VIEW transaction_view")
    op.drop_constraint("event_snapshot_id_fkey", "event", type_="foreignkey")
    op.drop_constraint("transactions_from_snapshot_id_fkey", "transactions", type_="foreignkey")
    op.drop_constraint("transactions_to_snapshot_id_fkey", "transactions", type_="foreignkey")
    op.drop_column("reading", "snapshot_id")
    op.drop_column("event", "snapshot_id")
    op.drop_column("transactions", "to_snapshot_id")
    op.drop_column("transactions", "from_snapshot_id")
    op.drop_table("snapshot")


def dict_to_snapshot(snap_data):
    """Convert a snapshot dict into a snapshot row tuple.

    :param snap_data: Snapshot payload as a dict.
    :returns: A tuple of ID, hash, and payload.
    """
    serialized = json_dumps(snap_data, sort_keys=True)
    computed_hash = sha256(serialized.encode("utf-8")).hexdigest()
    computed_id = as_uuid(computed_hash)
    return (computed_id, computed_hash, serialized)


def create_snapshot(conn, snap_id, snap_hash, snap_payload):
    """Create a snapshot with the given data."""
    conn.execute(
        sa.text("""INSERT INTO snapshot (id, hash, payload)
                         SELECT :id, :hash, :payload
                         WHERE NOT EXISTS (SELECT id FROM snapshot WHERE id = :id)"""),
        id=snap_id,
        hash=snap_hash,
        payload=snap_payload,
    )


def create_empty_snapshot():
    """Create the empty snapshot.

    :returns: The ID of the snapshot
    """
    conn = op.get_bind()
    snap_id, snap_hash, snap_payload = dict_to_snapshot({})
    create_snapshot(conn, snap_id, snap_hash, snap_payload)
    return snap_id


def create_meter_snapshot(conn, meter_view_row):
    """Create a snapshot from a meter_view entry.

    :returns: The ID of the snapshot
    """
    snapshot_data = get_meter_view_snapshot(meter_view_row)
    snap_id, snap_hash, snap_payload = dict_to_snapshot(snapshot_data)
    create_snapshot(conn, snap_id, snap_hash, snap_payload)
    return snap_id


def create_ground_snapshot(conn, ground_row):
    """Create a snapshot from a ground entry.

    :returns: The ID of the snapshot
    """
    snapshot_data = get_ground_snapshot(ground_row)
    snap_id, snap_hash, snap_payload = dict_to_snapshot(snapshot_data)
    create_snapshot(conn, snap_id, snap_hash, snap_payload)
    return snap_id


def create_tariff_snapshot(conn, tariff_row):
    """Create a snapshot from a tariff entry.

    :returns: The ID of the snapshot
    """
    snapshot_data = get_tariff_snapshot(tariff_row)
    snap_id, snap_hash, snap_payload = dict_to_snapshot(snapshot_data)
    create_snapshot(conn, snap_id, snap_hash, snap_payload)
    return snap_id


def create_sales_account_snapshot(conn, sales_account_row):
    """Create a snapshot from a snapshot tariff.

    :returns: The ID of the snapshot
    """
    snapshot_data = get_sales_account_snapshot(sales_account_row)
    snap_id, snap_hash, snap_payload = dict_to_snapshot(snapshot_data)
    create_snapshot(conn, snap_id, snap_hash, snap_payload)
    return snap_id


def apply_reading_snapshots(empty_id):
    """Apply snapshots to all readings."""
    conn = op.get_bind()
    logger.info("Entering reading snapshots")
    meters = conn.execute(
        """{}
                          WHERE meter.code IN (
                            SELECT DISTINCT NULLIF(meter, '')::int FROM reading
                          ) {}""".format(METER_VIEW_SELECT, METER_VIEW_GROUP_BY)
    )
    for meter in meters:
        create_meter_snapshot(conn, meter)


def apply_event_snapshots(empty_id):
    """Apply snapshots to all events."""
    conn = op.get_bind()
    logger.info("Entering event snapshots")
    meter_events = conn.execute(
        """{}
                                WHERE meter.id IN (
                                    SELECT DISTINCT object_id FROM event WHERE object_table = 'meter'
                                ) {}""".format(METER_VIEW_SELECT, METER_VIEW_GROUP_BY)
    )
    for meter in meter_events:  # pragma: nocoverage
        snap_id = create_meter_snapshot(conn, meter)
        conn.execute(
            sa.text("""UPDATE event SET snapshot_id = :snap_id
                     WHERE object_id = :meter_id AND object_table = 'meter'"""),
            snap_id=snap_id,
            meter_id=meter["id"],
        )

    grounds = conn.execute(
        """SELECT ground.id, name, serial, street1, street2, city, state, postalcode, coords
           FROM ground
           JOIN grounds_addresses ON grounds_addresses.ground_id = ground.id
           JOIN address ON address.id = grounds_addresses.address_id"""
    )
    for ground in grounds:
        ground = dict(ground._mapping) if hasattr(ground, "_mapping") else ground
        snap_id = create_ground_snapshot(conn, ground)
        conn.execute(
            sa.text("""UPDATE event SET snapshot_id = :snap_id
                     WHERE object_id = :ground_id AND object_table = 'ground'"""),
            snap_id=snap_id,
            ground_id=ground["id"],
        )

    tariff_events = conn.execute("""SELECT * FROM tariff
                                 WHERE tariff.id IN (
                                    SELECT DISTINCT object_id FROM event WHERE object_table = 'tariff'
                                 )""")
    for tariff in tariff_events:
        snap_id = create_tariff_snapshot(conn, tariff)
        tariff_id = tariff._mapping["id"] if hasattr(tariff, "_mapping") else tariff["id"]
        conn.execute(
            sa.text("""UPDATE event SET snapshot_id = :snap_id
                     WHERE object_id = :tariff_id AND object_table = 'tariff'"""),
            snap_id=snap_id,
            tariff_id=tariff_id,
        )

    meter_wallet_events = conn.execute(
        """SELECT DISTINCT meter_view.*, wallet.id AS wallet_id
                                       FROM event
                                       JOIN wallet ON wallet.id = event.object_id
                                       JOIN ({}) AS meter_view ON meter_view.id = wallet.meter_id
                                       ORDER BY meter_view.id ASC
                                       """.format(METER_VIEW_QUERY)
    )
    last_meter_id = None
    current_snap_id = None
    for meter in meter_wallet_events:  # pragma: nocoverage
        meter = dict(meter._mapping) if hasattr(meter, "_mapping") else meter
        if last_meter_id != meter["id"]:  # Don't reprocess if multiple associated wallets have events
            current_snap_id = create_meter_snapshot(conn, meter)
        conn.execute(
            sa.text("""UPDATE event SET snapshot_id = :snap_id
                     WHERE object_id = :wallet_id AND object_table = 'wallet'"""),
            snap_id=current_snap_id,
            wallet_id=meter["wallet_id"],
        )
        last_meter_id = meter["id"]

    conn.execute(
        sa.text("UPDATE event SET snapshot_id = :snap_id WHERE snapshot_id IS NULL"), snap_id=empty_id
    )


def apply_transaction_snapshots(empty_id):
    """Apply snapshots to all transactions."""
    conn = op.get_bind()
    logger.info("Entering transaction snapshots")
    transaction_wallets = conn.execute(
        """SELECT * FROM (
                                           SELECT from_wallet_id wallet_id FROM transactions
                                           UNION SELECT to_wallet_id wallet_id FROM transactions
                                       ) AS wallet_ids
                                       JOIN wallet ON wallet_id = wallet.id
                                       LEFT OUTER JOIN sales_account
                                           ON sales_account.id = wallet.sales_account_id
                                       LEFT OUTER JOIN ({}) AS meter_view ON meter_view.id = wallet.meter_id
                                       """.format(METER_VIEW_QUERY)
    )
    last_object_id = None
    current_snap_id = None
    for wallet in transaction_wallets:
        wallet = dict(wallet._mapping) if hasattr(wallet, "_mapping") else wallet
        if wallet["meter_id"] is not None:
            if wallet["meter_id"] != last_object_id:
                current_snap_id = create_meter_snapshot(conn, wallet)
                last_object_id = wallet["meter_id"]
        else:
            if wallet["sales_account_id"] != last_object_id:
                current_snap_id = create_sales_account_snapshot(conn, wallet)
                last_object_id = wallet["sales_account_id"]
        conn.execute(
            sa.text("""UPDATE transactions SET to_snapshot_id = :snap_id
                     WHERE to_wallet_id = :wallet_id"""),
            snap_id=current_snap_id,
            wallet_id=wallet["wallet_id"],
        )
        conn.execute(
            sa.text("""UPDATE transactions SET from_snapshot_id = :snap_id
                     WHERE from_wallet_id = :wallet_id"""),
            snap_id=current_snap_id,
            wallet_id=wallet["wallet_id"],
        )

    conn.execute(
        sa.text("UPDATE transactions SET to_snapshot_id = :snap_id WHERE to_snapshot_id IS NULL"),
        snap_id=empty_id,
    )
    conn.execute(
        sa.text("UPDATE transactions SET from_snapshot_id = :snap_id WHERE from_snapshot_id IS NULL"),
        snap_id=empty_id,
    )


def make_base_snapshot(snapshot_type, payload):
    """Get the common snapshot base."""
    data = {
        "_meta": {
            "version": 1,
            "legacy_migrated": True,
            "type": snapshot_type,
        },
    }
    data.update(payload)
    return data


def get_meter_view_snapshot(meter):
    """Get a snapshot of a meter_view record."""
    if hasattr(meter, "_mapping"):
        meter = dict(meter._mapping)
    snap = make_base_snapshot(
        "meter",
        {
            "id": meter["id"],
            "code": meter["code"],
            "serial": meter["serial"],
            "type": meter["meter_type"],
            "address": {
                "street1": meter["address_street1"],
                "street2": meter["address_street2"],
                "city": meter["address_city"],
                "state": meter["address_state"],
                "postalcode": meter["address_postalcode"],
                "coords": meter["address_coords"],
            },
            "model_name": meter["model_name"],
            "tags": meter["tags"] or [],
        },
    )
    if meter["meter_type"] == "customer":
        snap["customer"] = {
            "id": meter["customer_id"],
            "name": meter["customer_name"],
            "code": meter["customer_code"],
            "phone_number": meter["customer_phone_number"],
        }
        snap["tariff"] = {
            "name": meter["tariff_name"],
            "id": meter["tariff_id"],
        }
    return snap


def get_ground_snapshot(ground):
    """Get a snapshot of a ground record."""
    if hasattr(ground, "_mapping"):
        ground = dict(ground._mapping)
    snap = make_base_snapshot(
        "ground",
        {
            "id": ground["id"],
            "name": ground["name"],
            "serial": ground["serial"],
            "address": {
                "street1": ground["street1"],
                "street2": ground["street2"],
                "city": ground["city"],
                "state": ground["state"],
                "postalcode": ground["postalcode"],
                "coords": ground["coords"],
            },
        },
    )
    return snap


def _maybe_json(field):  # pragma: nocoverage
    """If the field is a JSON string, and should be unpacked, do it."""
    if isinstance(field, str):
        try:
            return json_loads(field)
        except Exception:
            pass  # pass the value through if it's not valid JSON
    return field


def get_tariff_snapshot(tariff):
    """Get a snapshot of a tariff record."""
    snap = make_base_snapshot(
        "tariff",
        {
            "id": tariff.id,
            "tariff_type": tariff.tariff_type,
            "blockrates": _maybe_json(tariff.blockrates),
            "flat_price": tariff.flat_price,
            "flat_load_limit": tariff.flat_load_limit,
            "load_limits": _maybe_json(tariff.load_limits),
            "load_limit_type": tariff.load_limit_type,
            "plan_enabled": tariff.plan_enabled,
            "plan_price": tariff.plan_price,
            "plan_fixed_fee": tariff.plan_fixed_fee,
            "cycle_start_day_of_month": tariff.cycle_start_day_of_month,
            "name": tariff.name,
            "tou_enabled": tariff.tou_enabled,
            "tous": _maybe_json(tariff.tous),
            "low_balance_threshold": tariff.low_balance_threshold,
            "daily_energy_limit_enabled": tariff.daily_energy_limit_enabled,
            "daily_energy_limit_reset_hour": tariff.daily_energy_limit_reset_hour,
            "daily_energy_limit_value": tariff.daily_energy_limit_value,
        },
    )
    return snap


def get_sales_account_snapshot(sales_acct):
    """Get a snapshot of a sales account record."""
    if hasattr(sales_acct, "_mapping"):
        sales_acct = dict(sales_acct._mapping)
    snap = make_base_snapshot(
        "sales_account",
        {
            "id": sales_acct["sales_account_id"],
            "name": sales_acct["name"],
            "is_system_account": sales_acct["system"],
        },
    )
    return snap


METER_VIEW_SELECT = """
  SELECT
    not meter_config.hidden                       AS active,
    address.street1                               AS address_street1,
    address.street2                               AS address_street2,
    address.city                                  AS address_city,
    address.state                                 AS address_state,
    address.postalcode                            AS address_postalcode,
    address.country                               AS address_country,
    address.coords                                AS address_coords,
    meter.code                                    AS code,
    credit_wallet.value                           AS credit_value,
    meter_system_info.current_state               AS current_state,
    customer.id                                   AS customer_id,
    customer.name                                 AS customer_name,
    customer.code                                 AS customer_code,
    customer.phone_number                         AS customer_phone_number,
    customer.phone_number_verified                AS customer_phone_number_verified,
    debt_wallet.value                             AS debt_value,
    ground.id                                     AS ground_id,
    ground.name                                   AS ground_name,
    ground.serial                                 AS ground_serial,
    meter.id                                      AS id,
    meter_billing.is_running_plan                 AS is_running_plan,
    meter_billing.last_cycle_start                AS last_cycle_start,
    meter_system_info.last_energy                 AS last_energy,
    meter_system_info.last_energy_datetime        AS last_energy_datetime,
    meter_billing.last_plan_payment_date          AS last_plan_payment_date,
    meter_billing.last_plan_expiration_date       AS last_plan_expiration_date,
    meter.meter_type                              AS meter_type,
    meter_models.id                               AS model_id,
    meter_models.name                             AS model_name,
    plan_wallet.value                             AS plan_value,
    meter.serial                                  AS serial,
    meter_config.state                            AS state,
    meter_config.subnet                           AS subnet,
    array_remove(array_agg(meter_tag.name), NULL) AS tags,
    meter_billing.tariff_id                       AS tariff_id,
    tariff.name                                   AS tariff_name,
    tariff.plan_enabled                           AS tariff_plan_enabled,
    meter_billing.total_cycle_energy              AS total_cycle_energy,
    sparkmac_node.forwarding                      AS sparkmac_forwarding,
    sparkmac_node.flooding_subnets                AS sparkmac_flooding_subnets,
    sparkmac_node.ttl                             AS sparkmac_ttl
  FROM meter
    JOIN meter_config ON (meter_config.meter_id = meter.id)
    JOIN meter_system_info ON (meter_system_info.meter_id = meter.id)
    JOIN address ON (meter.address_id = address.id)
    JOIN ground ON (meter.ground_id = ground.id)
    JOIN meter_models ON (meter.model_id = meter_models.id)
    LEFT JOIN meter_billing ON (meter_billing.meter_id = meter.id)
    LEFT JOIN tariff ON (meter_billing.tariff_id = tariff.id)
    LEFT JOIN wallet credit_wallet ON (
        credit_wallet.meter_id = meter.id
        AND credit_wallet.wallet_type = 'credit'
    )
    LEFT JOIN wallet debt_wallet ON (debt_wallet.meter_id = meter.id AND debt_wallet.wallet_type = 'debt')
    LEFT JOIN wallet plan_wallet ON (plan_wallet.meter_id = meter.id AND plan_wallet.wallet_type = 'plan')
    LEFT JOIN customer ON (customer.meter_id = meter.id)
    LEFT JOIN meters_tags ON (meters_tags.meter_id = meter.id AND meters_tags.active = TRUE)
    LEFT JOIN meter_tag ON (meter_tag.id = meters_tags.tag_id)
    LEFT JOIN sparkmac_node ON (sparkmac_node.meter_id = meter.id)
"""

METER_VIEW_GROUP_BY = """
  GROUP BY meter.id,
    ground.id,
    ground.name,
    ground.serial,
    meter_billing.tariff_id,
    tariff.name,
    tariff.plan_enabled,
    meter_models.id,
    meter_models.name,
    meter.serial,
    meter.code,
    meter.meter_type,
    meter_config.hidden,
    meter_config.subnet,
    meter_config.state,
    meter_billing.is_running_plan,
    meter_billing.last_cycle_start,
    meter_billing.last_plan_payment_date,
    meter_billing.last_plan_expiration_date,
    meter_billing.total_cycle_energy,
    meter_system_info.last_energy,
    meter_system_info.last_energy_datetime,
    meter_system_info.current_state,
    credit_wallet.value,
    debt_wallet.value,
    plan_wallet.value,
    customer.id,
    customer.name,
    customer.code,
    customer.phone_number,
    customer.phone_number_verified,
    address.street1,
    address.street2,
    address.city,
    address.state,
    address.postalcode,
    address.country,
    address.coords,
    sparkmac_node.forwarding,
    sparkmac_node.flooding_subnets,
    sparkmac_node.ttl
  ORDER BY meter.serial
  """

METER_VIEW_QUERY = METER_VIEW_SELECT + METER_VIEW_GROUP_BY
