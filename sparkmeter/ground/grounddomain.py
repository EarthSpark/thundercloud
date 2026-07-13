# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Ground domain."""

import datetime
import logging
import socket

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import false, func
from sqlalchemy.sql.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.sql.sqltypes import Boolean, DateTime, Integer, String

from sparkmeter.config.configdict import config
from sparkmeter.config.configparameter import parameters
from sparkmeter.database.alchemy import sql
from sparkmeter.database.symmetricdsdomain import NodeHost
from sparkmeter.database.sync import SYNC_CHANNEL_ADDRESS, SYNC_CHANNEL_GROUND, SYNC_GROUP_CLOUD, syncchannel
from sparkmeter.database.tables import get_table_by_name
from sparkmeter.database.types import UUIDType
from sparkmeter.event.eventdomain import Event
from sparkmeter.meter.meterdomain import Address, Meter, MeterBilling, MeterConfig
from sparkmeter.metering.api import disable_all_meters
from sparkmeter.misc.uuidutils import as_uuid
from sparkmeter.models import BaseDomain
from sparkmeter.reading.readingdomain import Reading
from sparkmeter.tariff.tariffdomain import Tariff

logger = logging.getLogger(__name__)


@syncchannel(SYNC_CHANNEL_ADDRESS)
class GroundsAddresses(BaseDomain):
    """Ground Address mapper.

    The only reason this exists is to avoid cyclic references between the
    address and ground tables and still being able to maintain non-nullable
    foreign keys.

    This is only used for ground addresses and there should only be
    entry in this table per ground.
    """

    __tablename__ = "grounds_addresses"
    __table_args__ = (
        UniqueConstraint("ground_id", "address_id", name="grounds_addresses_ground_address_unique"),
    )

    ground_id = Column(UUIDType(binary=False), ForeignKey("ground.id"), nullable=False, unique=True)

    address_id = Column(UUIDType(binary=False), ForeignKey("address.id"), nullable=False, unique=True)

    address = relationship("Address", foreign_keys=[address_id])

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)
        group.set_key_columns(cls.ground_id, cls.address_id)
        if group.is_cloud():
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                group.format_trigger_attr(cls.ground_id) == Ground.id,
            )


@syncchannel(SYNC_CHANNEL_GROUND)
class GroundPrivate(BaseDomain):
    """Ground private data.

    This contain private properties for a ground, it is separated from the
    main table to avoid sending this data to other grounds.
    """

    __tablename__ = "ground_private"

    #: Ground this private relates to
    ground_id = Column(UUIDType(binary=False), ForeignKey("ground.id"), nullable=False)

    #: Maximum capacity of this grid, in watts
    max_capacity = Column(Integer, default=1000)

    #: secret_key, currently unused
    secret_key = Column(String)

    #: If this is ``True``, do not allow meters to be turned off.
    override_meter_state = Column(Boolean, default=False, server_default="false", nullable=False)

    #: When the override meter state was last modified
    override_meter_state_modified = Column(DateTime)

    #: A reference to the ground
    ground = relationship("Ground")

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)
        if group.is_cloud():
            ground_t = get_table_by_name("ground")
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                group.format_trigger_attr(cls.ground_id) == ground_t.c.id,
            )

    def queue_override_meter_state(self, state):
        """Queue a meter override state update for this ground.

        :param state: the state
        :type state: bool
        """
        ground = self.ground
        if state:
            event_type = Event.TYPE_GROUND_OVERRIDE_METER_STATE_ENABLED
        else:
            event_type = Event.TYPE_GROUND_OVERRIDE_METER_STATE_DISABLED

        event = Event.create(event_type, obj=ground)
        self.session.add(event)

    def set_override_meter_state(self, state):
        """Set a meter override state for this ground.

        :param state: the state
        :type state: bool
        """
        logger.info("Setting meter override state to {}".format(state))
        self.override_meter_state = state
        self.override_meter_state_modified = datetime.datetime.utcnow()
        self.session.flush()
        if not config["HEROKU"]:
            if state:
                # We are turning on override, need to make sure that all meters are turned
                # off as fast as possible.
                # Send out a broadcast packet and ignore the responses
                if parameters.SEND_BROADCAST_SIGNAL:
                    logger.info("Sending broadcast signal.")
                    disable_all_meters()
                else:
                    logger.info("Not sending broadcast signal, disabled in configuration.")

            self.ground.update_all_active_customer_meters()


@syncchannel(SYNC_CHANNEL_GROUND)
class Ground(BaseDomain):
    """Ground table mapper."""

    __tablename__ = "ground"

    #: Name of this ground
    name = Column(String, unique=True)

    #: A global identifer of this ground
    serial = Column(String, unique=True)

    #: The address of this ground
    address = relationship(
        "Address",
        cascade="save-update, merge, delete",
        secondary=GroundsAddresses.__table__,
        passive_deletes=True,
        uselist=False,
        overlaps="address",
    )

    #: The private, ground specific attributes of this ground
    private = relationship(
        "GroundPrivate",
        primaryjoin="and_(Ground.id == GroundPrivate.ground_id)",
        uselist=False,
        overlaps="ground",
    )  # type: GroundPrivate

    max_capacity = association_proxy("private", "max_capacity")

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)

    @classmethod
    def create_empty(cls, session, serial=None, name=None, secret_key=None):
        """
        Create an empty ground and all sub-objects required.

        :param session: a database session
        :param serial: serial of this ground
        :param name: name of this ground
        :param secret_key: secret api key
        :returns the newly created ground.
        """
        if name is None:
            name = config.get("GROUND_NAME") or socket.gethostname()
        if serial is None:
            serial = config.get("SERIAL") or name + "-serial"
        if secret_key is None:
            secret_key = config.get("SPARKCLOUD_API_KEY") or name + "-secret-key"

        if cls.query.filter_by(name=name).count():
            raise ValueError("A ground with name %s already exists" % (name,))
        if cls.query.filter_by(serial=serial).count():
            raise ValueError("A ground with serial %s already exists" % (serial,))

        self = cls(id=as_uuid(serial), serial=serial)
        session.add(self)
        self.name = name
        self.address = Address(id=as_uuid("{}-address".format(serial)), ground=self)
        private = GroundPrivate(id=as_uuid(secret_key), ground=self, secret_key=secret_key)
        session.add(private)
        logger.info("Created ground with serial %r" % (serial,))
        session.flush()
        return self

    @classmethod
    def get_by_serial(cls, serial):
        """Get a ground by serial number."""
        return cls.query.filter_by(serial=serial).scalar()

    @classmethod
    def get_default(cls):
        """Get the default ground.

        Get the default ground, first by attempting to use
        the default SERIAL configuration variable, then by ordering the
        grounds by name and selecting the first.
        """
        serial = config.get("SERIAL")
        if serial:
            ground = cls.get_by_serial(serial)
            if ground:
                return ground
        return cls.query.order_by("name").first()

    @classmethod
    def get_by_id(cls, object_id):
        """Get the Ground by the given object_id.

        :rtype: Ground
        """
        return cls.query.get(object_id)

    @classmethod
    def get_current(cls):
        """
        Get current Ground.

        On Ground, get the one specfied in SERIAL, on cloud, return None.

        :returns: the Ground or None:
        :rtype: Ground
        """
        if config["HEROKU"]:
            return None
        return cls.get_by_serial(config.get("SERIAL"))

    @classmethod
    def get_by_name(cls, name):
        """Get the Ground by the given name.

        :param name: the ground name
        :type name: str
        :rtype: Ground
        """
        return cls.query.filter(func.lower(cls.name) == func.lower(name)).scalar()

    @classmethod
    def get_override_view(cls):
        # type: () -> List[Tuple[str, str, bool, datetime]]
        """Get an override view suitable for showing on the base template.

        :returns: a list of 4 sized tuples: (ground serial, ground name, override state, override modified)
        """
        # This query does several things together by design, this runs every time a template if rendered,
        # once we can cache some of this on client side we need to be as performant as possible as reduce
        # the amount of queries.
        return sql.session.query(
            cls.serial,
            cls.name,
            GroundPrivate.override_meter_state,
            GroundPrivate.override_meter_state_modified,
        ).outerjoin(GroundPrivate, cls.id == GroundPrivate.ground_id)

    def remove(self):
        """Remove a ground from the system.

        This deletes a ground, meter, sales accounts and everything referencing it,
        but not readings.
        """
        from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
        from sparkmeter.salesaccount.salesaccountdomain import SalesAccount

        if self.private:
            sql.session.delete(self.private)
        address = self.address
        self.address = None
        sql.session.delete(address)
        sql.session.flush()
        for summary in DashboardDailyTariffSummary.query.filter_by(ground_id=self.id):
            sql.session.delete(summary)
        for meter in Meter.query.filter_by(ground_id=self.id):
            meter.remove()
        for account in SalesAccount.query.filter_by(ground_id=self.id):
            account.remove()
        sql.session.flush()
        sql.session.delete(self)

    def get_meters(self):
        """Get all the meter objects in this ground.

        This is slower than a meter view since it will fetch the whole objects.
        """
        return Meter.query.filter_by(ground_id=self.id).order_by(Meter.id)

    def get_active_meters(self):
        """Get all the active (non-hidden) meter objects in this ground."""
        return Meter.query.filter(
            Ground.id == self.id,
            Meter.ground_id == Ground.id,
            Meter.id == MeterConfig.meter_id,
            MeterConfig.hidden == false(),
        ).order_by(Meter.code)

    def get_active_customer_meters(self):
        """Get all the active (non-hidden) customer meter objects in this ground."""
        return self.get_active_meters().filter(Meter.meter_type == Meter.TYPE_CUSTOMER)

    def get_used_capacity(self):
        """Get ground allocated tariff capacity in watts."""
        return (
            sql.session.query(func.sum(Tariff.flat_load_limit))
            .filter(
                Ground.id == self.id,
                Meter.ground_id == Ground.id,
                MeterBilling.meter_id == Meter.id,
                MeterBilling.tariff_id == Tariff.id,
                MeterConfig.meter_id == Meter.id,
                MeterConfig.hidden == false(),
            )
            .scalar()
            or 0
        )

    # FIXME: should this be removed
    def get_readings(self):  # pragma nocover (unused)
        """Get all readings in a ground."""
        # FIXME: this can return many thousands of object, perhaps limit it by
        #        default somehow to avoid huge queries.
        return Reading.query.filter(
            MeterConfig.hidden == false(), MeterConfig.meter_id == Meter.id, Meter.ground_id == self.id
        )

    def get_last_sync_date(self):
        """Get the last time this ground was synchronized against the cloud."""
        if config["HEROKU"]:
            node_id = self.serial
        else:
            node_id = "cloud"
        return NodeHost.get_heartbeat_time(self.session, node_id)

    def update_all_active_customer_meters(self):
        """
        Send out 'set config' packets to all active meters on this ground.

        It will first send out packets to the meters a state that is known to be different
        from the expected state and then send out to all the remaining meters.
        """
        # For all active meters check the previous state,
        # send a new set-config command to it
        active_meters = self.get_active_customer_meters()
        unsent_meters = []

        # First, send out set config packets for meters that are known to be different
        logger.info("Updating meters with unknown state")
        for meter in active_meters:
            if not meter.send_set_config_based_on_system_info():
                unsent_meters.append(meter)

        # Second, send out set config packets to the remaining meters
        logger.info("Updating meters with a known state")
        for meter in unsent_meters:
            meter.send_set_config_unconditionally()
