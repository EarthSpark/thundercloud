# -*- coding: utf-8 -*-
# Copyright © 2019 SparkMeter, Inc.
# All Rights Reserved.
"""Snapshot domain models."""

import logging
from hashlib import sha256

from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import String, Text

from sparkmeter.database.sync import SYNC_CHANNEL_SNAPSHOT, SYNC_GROUP_CLOUD, syncchannel
from sparkmeter.misc.jsonutils import json_dumps, json_loads
from sparkmeter.misc.uuidutils import as_uuid
from sparkmeter.models import BaseDomain

logger = logging.getLogger(__name__)


def _make_snapshot(snapshot_type, version, payload):
    """Get the base snapshot state.

    :param snapshot_type: The name of the entity being snapshotted
    :param version: The snapshot version number
    :param payload: The data to snapshot
    :returns: A snapshot dict
    """
    data = {
        "_meta": {
            "version": version,
            "legacy_migrated": False,
            "type": snapshot_type,
        }
    }
    data.update(payload)
    return data


def get_meter_view_snapshot(meter_view):
    """Transform a meter_view to a meter snapshot dict."""
    snap = _make_snapshot("meter", 1, {
        "id": meter_view.id,
        "code": meter_view.code,
        "serial": meter_view.serial,
        "type": meter_view.meter_type,
        "address": {
            "street1": meter_view.address_street1,
            "street2": meter_view.address_street2,
            "city": meter_view.address_city,
            "state": meter_view.address_state,
            "postalcode": meter_view.address_postalcode,
            "coords": meter_view.address_coords,
        },
        "model_name": meter_view.model_name,
        "tags": meter_view.tags or [],
    })

    if meter_view.is_customer_meter():
        snap["customer"] = {
            "id": meter_view.customer_id,
            "name": meter_view.customer_name,
            "code": meter_view.customer_code,
            "phone_number": meter_view.customer_phone_number,
        }
        snap["tariff"] = {
            "name": meter_view.tariff_name,
            "id": meter_view.tariff_id,
        }
    return snap


def get_ground_snapshot(ground):
    """Transform a ground to a ground snapshot dict."""
    snap = _make_snapshot("ground", 1, {
        "id": ground.id,
        "name": ground.name,
        "serial": ground.serial,
        "address": {
            "street1": ground.address.street1,
            "street2": ground.address.street2,
            "city": ground.address.city,
            "state": ground.address.state,
            "postalcode": ground.address.postalcode,
            "coords": ground.address.coords,
        }
    })
    return snap


def get_sales_account_snapshot(sales_acct):
    """Transform a sales account to a sales account snapshot dict."""
    snap = _make_snapshot("sales_account", 1, {
        "id": sales_acct.id,
        "name": sales_acct.name,
        "is_system_account": sales_acct.system,
    })
    return snap


def _maybe_json(field):
    """If the field is a JSON string, and should be unpacked, do it."""
    if isinstance(field, str):
        try:
            return json_loads(field)
        except Exception:
            pass  # pass the value through if it's not valid JSON
    return field


def get_tariff_snapshot(tariff):
    """Transform a tariff to a tariff snapshot dict."""
    snap = _make_snapshot("tariff", 2, {
        "id": tariff.id,
        "tariff_type": tariff.tariff_type,
        "blockrates": _maybe_json(tariff.blockrates),
        "flat_price": tariff.flat_price,
        "flat_load_limit": tariff.flat_load_limit,
        "load_limits": _maybe_json(tariff.load_limits),
        "load_limit_type": tariff.load_limit_type,
        "plan_enabled": tariff.plan_enabled,
        "plan_price": tariff.plan_price,
        "plan_duration_span": tariff.plan_duration_span,
        "plan_duration_unit": tariff.plan_duration_unit,
        "plan_fixed_fee": tariff.plan_fixed_fee,
        "cycle_start_day_of_month": tariff.cycle_start_day_of_month,
        "name": tariff.name,
        "tou_enabled": tariff.tou_enabled,
        "tous": _maybe_json(tariff.tous),
        "low_balance_threshold": tariff.low_balance_threshold,
        "daily_energy_limit_enabled": tariff.daily_energy_limit_enabled,
        "daily_energy_limit_reset_hour": tariff.daily_energy_limit_reset_hour,
        "daily_energy_limit_value": tariff.daily_energy_limit_value,
    })
    return snap


@syncchannel(SYNC_CHANNEL_SNAPSHOT)
class Snapshot(BaseDomain):
    """Snapshot model.

    A snapshot captures the state (and hash) of a JSON object representing a system entity at a given moment
    in time.
    """

    __tablename__ = 'snapshot'

    # Hash (SHA256)
    hash_ = Column('hash', String(64), unique=True)

    # The snapshot content
    payload = Column(Text, nullable=False)

    @classmethod
    def get_default_id(cls, context):
        """Get the default ID for a Snapshot object."""
        return as_uuid(context.current_parameters['hash'])

    @classmethod
    def sync_init(cls, group):
        group.set_conflict_winner(SYNC_GROUP_CLOUD)

    @classmethod
    def _get_or_create_snapshot(cls, snapshot_dict, session=None):
        """Makes a snapshot with the given information.

        :param snapshot_dict: A Python dict of Snapshot metadata.
        :param session: (optional) the database session to use. Will default to the SQLAlchemy session if
            none can be inferred.
        """
        serialized = json_dumps(snapshot_dict, sort_keys=True)
        computed_hash = sha256(serialized.encode('utf-8')).hexdigest()
        computed_id = as_uuid(computed_hash)
        result = cls.get_one_or_create(
            session=session,
            flush=session is None,  # if using the implicit session, flush it so it can be found by others
            id=computed_id,
            hash_=computed_hash,
            payload=serialized,
        )
        return result.object

    @classmethod
    def get_or_create_meter_snapshot(cls, code=None, meter_id=None, session=None):
        """Get or create the snapshot for the given meter.

        :param code: (optional) the code for the meter to create the snapshot for.
        :param meter_id: (optional) the ID for the meter to create the snapshot for.
        :param session: (optional) the database session to use. Will default to the SQLAlchemy session if
            none can be inferred.
        :returns: The corresponding meter Snapshot
        """
        from sparkmeter.meter.meterdomain import MeterView
        if not meter_id:
            if not code:
                raise ValueError("code or meter_id")
            meter_view = MeterView.query.filter_by(code=code).one()
        else:
            meter_view = MeterView.get_by_id(meter_id)

        snap = get_meter_view_snapshot(meter_view)
        return cls._get_or_create_snapshot(snap, session=session)

    @classmethod
    def get_or_create_ground_snapshot(cls, ground_obj, session=None):
        """Get or create the ground snapshot for the given ground.

        :param ground_obj: The ground SQLAlchemy object to snapshot.
        :param session: (optional) the database session to use. Will default to the SQLAlchemy session if
            none can be inferred.
        :returns: The corresponding ground snapshot.
        """
        snap = get_ground_snapshot(ground_obj)
        return cls._get_or_create_snapshot(snap, session=session)

    @classmethod
    def get_or_create_tariff_snapshot(cls, tariff_obj, session=None):
        """Get or create the tariff snapshot for the given tariff.

        :param tariff_obj: The tariff SQLAlchemy object to snapshot.
        :param session: (optional) the database session to use. Will default to the SQLAlchemy session if
            none can be inferred.
        :returns: The corresponding ground snapshot.
        """
        snap = get_tariff_snapshot(tariff_obj)
        return cls._get_or_create_snapshot(snap, session=session)

    @classmethod
    def get_or_create_sales_snapshot(cls, acct_obj, session=None):
        """Get or create the snapshot for the given SalesAccount.

        :param acct_obj: The sales account object to snapshot.
        :param session: (optional) the database session to use. Will default to the SQLAlchemy session if
            none can be inferred.
        :returns: The corresponding sales account snapshot.
        """
        snap = get_sales_account_snapshot(acct_obj)
        return cls._get_or_create_snapshot(snap, session=session)

    @classmethod
    def get_or_create_wallet_snapshot(cls, wallet_obj, session=None):
        """Get or create the snapshot for the object that owns the given Wallet.

        :param wallet_obj: The wallet object to snapshot.
        :param session: (optional) the database session to use. Will default to the SQLAlchemy session if
            none can be inferred.
        :returns: The corresponding wallet-owner snapshot.
        """
        if wallet_obj.sales_account is not None:
            return cls.get_or_create_sales_snapshot(wallet_obj.sales_account, session=session)
        elif wallet_obj.meter is not None:
            return cls.get_or_create_meter_snapshot(meter_id=wallet_obj.meter.id, session=session)
        # This shouldn't be hit - a defensive catch-all in the event we add additional wallet holding objects
        return cls.get_or_create_empty_snapshot(session=session)  # pragma: nocover

    @classmethod
    def get_or_create_empty_snapshot(cls, session=None):
        """Get or create an empty snapshot.

        :param session: (optional) the database session to use. Will default to the SQLAlchemy session if
            none can be inferred.
        :returns: The corresponding empty snapshot.
        """
        return cls._get_or_create_snapshot(dict(), session=session)
