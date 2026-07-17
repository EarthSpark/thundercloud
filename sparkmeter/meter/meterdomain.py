# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Meter domain."""

from __future__ import division

import datetime
import logging
import uuid
from builtins import str

import phonenumbers
from flask_babel import lazy_gettext as _
from past.utils import old_div
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import load_only, relationship
from sqlalchemy.sql.expression import and_, or_, select, true
from sqlalchemy.sql.schema import CheckConstraint, Column, ForeignKey, UniqueConstraint
from sqlalchemy.sql.sqltypes import Boolean, DateTime, Float, Integer, Numeric, String

from sparkmeter.config.configdict import config
from sparkmeter.config.configparameter import parameters
from sparkmeter.database.alchemy import sql
from sparkmeter.database.columns import JSONString
from sparkmeter.database.sync import SYNC_CHANNEL_ADDRESS, SYNC_CHANNEL_METER, SYNC_GROUP_GROUND, syncchannel
from sparkmeter.database.tables import get_table_by_name
from sparkmeter.database.types import UUIDType
from sparkmeter.event.eventdomain import Event, SMSConfigMessage, SMSMessage
from sparkmeter.exceptions import MeterError, TransactionError
from sparkmeter.meter.meterstate import MeterState
from sparkmeter.meter.meterutils import SERIAL_RE
from sparkmeter.metering.api import send_set_config
from sparkmeter.misc.phoneutils import parse_country_national
from sparkmeter.misc.pythonutils import unset
from sparkmeter.misc.uuidutils import as_uuid
from sparkmeter.models import BaseDomain, BaseView
from sparkmeter.reading.readingdomain import Reading
from sparkmeter.transaction.transactiondomain import Transaction, TransactionView, Wallet

logger = logging.getLogger(__name__)


@syncchannel(SYNC_CHANNEL_METER)
class SparkmacNode(BaseDomain):
    """Sparkmac Network Forwarding."""

    __tablename__ = "sparkmac_node"

    #: Id of the meter
    meter_id = Column(UUIDType(binary=False), ForeignKey("meter.id"), nullable=False)

    static_routes = Column(JSONString)

    flooding_macs = Column(JSONString)

    #: Forwarding is disabled
    FORWARDING_OFF = "off"

    #: Forwarding via routing
    FORWARDING_ROUTING = "routing"

    #: Forwarding via flooding
    FORWARDING_FLOODING = "flooding"

    # FIXME: constraint to ['off', 'routing', 'flooding'] values
    forwarding = Column(String, info={"label": _("Sparkmac Forwarding")}, default=FORWARDING_FLOODING)

    #: Routing using a custom function
    ROUTING_CUSTOM = "custom"

    #: Routing using static routes
    ROUTING_STATIC = "static"

    #: Routing using a dynamic algorithm
    ROUTING_DYNAMIC = "dynamic"

    # FIXME: constraint to ['custom', 'static', 'dynamic'] values
    routing_enabled = Column(
        JSONString,
        default=[ROUTING_CUSTOM, ROUTING_STATIC, ROUTING_DYNAMIC],
        info={"label": _("Sparkmac Routing Enabled")},
    )

    flooding_subnets = Column(Integer, default=255, info={"label": _("Sparkmac Flooding Subnets")})

    # FIXME: constraint choices=range(1, 16),
    ttl = Column(Integer, default="5", info={"label": _("Sparkmac TTL")})

    #: A reference to the meter
    meter = relationship("Meter", foreign_keys=[meter_id])

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            ground_t = get_table_by_name("ground")
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                group.format_trigger_attr(cls.meter_id) == Meter.id,
                Meter.ground_id == ground_t.c.id,
            )


# FIXME: This should be moved out to its own module or a base/core module.
@syncchannel(SYNC_CHANNEL_METER)
class Customer(BaseDomain):
    """Customer table."""

    __tablename__ = "customer"

    #: The meter this customer belongs to
    meter_id = Column(UUIDType(binary=False), ForeignKey("meter.id"), nullable=False)

    #: Full name of the customer
    name = Column(String, default="new customer", info={"label": _("Name")})

    #: Code identifying the customer
    code = Column(String, info={"label": _("Code")})

    #: Phone number for this customer
    phone_number = Column(String, info={"label": _("Phone Number")})

    #: If the phone number for this customer has been verified with a CHECK SMS message
    phone_number_verified = Column(Boolean, default=False)

    #: A reference to the meter
    meter = relationship("Meter", foreign_keys=[meter_id])

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            ground_t = get_table_by_name("ground")
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                group.format_trigger_attr(cls.meter_id) == Meter.id,
                Meter.ground_id == ground_t.c.id,
            )

    @property
    def country_code(self):
        if self.phone_number:
            number = phonenumbers.parse(self.phone_number)
            return str(number.country_code)

        return getattr(self, "_country_code", None)

    @country_code.setter
    def country_code(self, value):
        if self.national_number:
            phone_number = parse_country_national(value, self.national_number)
        else:
            phone_number = None
        self.phone_number = phone_number
        self._country_code = value

    @property
    def national_number(self):
        national_number = getattr(self, "_national_number", None)
        if national_number is not None:
            return str(national_number)

        if self.phone_number:  # pragma: nocoverage
            number = phonenumbers.parse(self.phone_number)
            return str(number.national_number)

    @national_number.setter
    def national_number(self, value):
        if hasattr(self, "_country_code") and value:
            phone_number = parse_country_national(self._country_code, value)
        else:
            phone_number = None
        self.phone_number = phone_number
        self._national_number = value

    def send_phone_number_verification(self):
        """Send a message verification to this phone number.
        :returns: the message
        """
        config = SMSConfigMessage.get_by_message_type(SMSConfigMessage.TYPE_VERIFY_NUMBER)
        return config.create(self.phone_number)

    def verification_message_sent(self):
        """Check if this customer has been verified.

        This method will see if a SMS verification message has already been sent.
        :returns: True if the verified phone number has been queued.
        """
        return (
            SMSMessage.query.filter(SMSMessage.config_message_type == SMSConfigMessage.TYPE_VERIFY_NUMBER)
            .filter_by(phone_number=self.phone_number)
            .count()
        ) > 0


@syncchannel(SYNC_CHANNEL_ADDRESS)
class Address(BaseDomain):
    """Address table."""

    __tablename__ = "address"

    #: ID of ground this address belongs to, used by syncing
    ground_id = Column(UUIDType(binary=False), ForeignKey("ground.id"), nullable=False)

    #: Street name, eg. 123 Main Street
    street1 = Column(String, info={"label": _("Street1")})

    #: Additional street name
    street2 = Column(String, info={"label": _("Street2")})

    #: City, eg. New Dehli
    city = Column(String, info={"label": _("City")})

    #: State, if applicable, eg. California
    state = Column(String, info={"label": _("State")})

    #: Postal/Zip code, eg. 12345
    postalcode = Column(String, info={"label": _("Postal code")})

    #: Country, eg. Haiti
    country = Column(String, info={"label": _("Country")})

    #: latitude and longitude coordinates, separated by a comma; for example -12.345,67.890
    coords = Column(String, info={"label": _("Coordinates")})

    #: Ground this address belongs to, used by syncing.
    ground = relationship("Ground")

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            ground_t = get_table_by_name("ground")
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                group.format_trigger_attr(cls.ground_id) == ground_t.c.id,
            )


@syncchannel(SYNC_CHANNEL_METER)
class MeterBilling(BaseDomain):
    """
    Billing related state for this meter.

    Only created for customer meters.
    """

    __tablename__ = "meter_billing"

    #: The meter this customer belongs to
    meter_id = Column(UUIDType(binary=False), ForeignKey("meter.id"), nullable=False)

    #: The tariff used to bill the meter.
    tariff_id = Column(UUIDType(binary=False), ForeignKey("tariff.id"), nullable=False)

    #: last time the plan payment was paid.
    last_plan_payment_date = Column(DateTime, default=None)

    #: last plan expiration date
    last_plan_expiration_date = Column(DateTime, default=None)

    #: last time the current cycle started
    last_cycle_start = Column(DateTime, default=None)

    #: The total amount of energy used with the current plan, it's used to select
    #: the correct block rate value
    total_cycle_energy = Column(Float, default=0)

    #: If the customer has paid his current plan
    is_running_plan = Column(Boolean, default=False)

    #: The datetime that the current daily energy limit started counting the days energy
    last_daily_energy_limit_reset_datetime = Column(DateTime, default=None)

    #: The energy value recorded at the time the current energy counter started counting
    last_daily_energy_limit_reset_value = Column(Float, default=None)

    #: A reference to the meter
    meter = relationship("Meter", foreign_keys=[meter_id])

    #: A reference to the tariff
    tariff = relationship("Tariff")

    ignore_changed_fields = [
        "total_cycle_energy",
    ]

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            ground_t = get_table_by_name("ground")
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                group.format_trigger_attr(cls.meter_id) == Meter.id,
                Meter.ground_id == ground_t.c.id,
            )


@syncchannel(SYNC_CHANNEL_METER)
class MeterSystemInfo(BaseDomain):
    """
    System controlled info about the Meter.

    This information is writable by the system only and can only be written to from the gateway.
    """

    __tablename__ = "meter_system_info"

    #: Id of the meter
    meter_id = Column(UUIDType(binary=False), ForeignKey("meter.id"), nullable=False)

    #: The energy value from the last reading processed in the billing controller.
    #: This value is copied from the latest processed reading for this meter.
    last_energy = Column(Float, default=0.0, info={"label": _("Last Energy")})

    #: The datetime of the energy value from the last reading processed in the billing controller.
    #: This value is copied from the latest processed reading for this meter.
    last_energy_datetime = Column(
        DateTime, default=datetime.datetime.utcnow, info={"label": _("Last Energy Datetime")}
    )

    # FIXME: Investigate if this should be proper foreign key once we can sync references right
    #: last reading for this meter
    reading_id = Column(UUIDType(binary=False))

    #: The firmware version of the physical meter.
    firmware = Column(String)

    #: The bootloader version of the physical meter.
    bootloader = Column(String)

    # FIXME: maybe we should remove this and just reference the readings state directly
    #: The most recent meter reading. This value may not match the actual
    #: state if the meter has not yet reported since changing.
    #: This is updated when we receive a READ_REPLY/SET_CONFIG_REPLY from a meter.
    current_state = Column(Integer, default=MeterState.STATE_OFF.id)

    #: This is updated when we receive a reading (READ_REPLY)
    current_user_power_limit = Column(Float)

    last_config_datetime = Column(DateTime)

    #: The latest reading received from this meter.
    reading = relationship(
        "Reading",
        uselist=False,
        load_on_pending=True,
        viewonly=True,
        primaryjoin="foreign(Reading.id) == MeterSystemInfo.reading_id",
    )

    #: A reference to the meter
    meter = relationship("Meter", foreign_keys=[meter_id])

    ignore_changed_fields = [
        "last_energy",
        "last_energy_datetime",
        "total_cycle_energy",
    ]

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            ground_t = get_table_by_name("ground")
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                group.format_trigger_attr(cls.meter_id) == Meter.id,
                Meter.ground_id == ground_t.c.id,
            )

    def update_from_reading(self, reading):
        """Update ourselves based on a reading reply.
        :param reading: a reading
        """
        self.current_state = reading.state
        self.current_user_power_limit = reading.user_power_limit
        self.last_energy = reading.energy
        self.last_energy_datetime = reading.heartbeat_end
        self.reading_id = reading.id

    def update_from_set_config(self, command, application_version, bootloader_version, power_limit):
        """Update ourselves based on a set config reply.
        :param command: set-config command set
        :param application_version: application version reply
        :param bootloader_version: bootloader version reply
        :param power_limit: power_limit sent in raw, unscaled format
        """
        if command == "enable":
            state = MeterConfig.STATE_ON
        elif command == "disable":
            state = MeterConfig.STATE_OFF
        else:  # pragma: nocoverage
            raise AssertionError(command)

        self.firmware = application_version
        self.bootloader = bootloader_version
        self.current_state = state
        self.current_user_power_limit = power_limit * self.meter.scalars.power_scalar
        self.last_config_datetime = datetime.datetime.utcnow()


@syncchannel(SYNC_CHANNEL_METER)
class MeterConfig(BaseDomain):
    """
    Configuration for the Meter.

    This is the information that the user has control over to manage a meter.
    """

    __tablename__ = "meter_config"

    #: Id of the meter
    meter_id = Column(UUIDType(binary=False), ForeignKey("meter.id"), nullable=False)

    #: FIXME: Rename to active and swap true/false
    #: If the meter should be hidden from the normal fields, this is usually done to disable an unused meter.
    hidden = Column(Boolean, default=False, nullable=False, info={"label": _("Hidden")})

    # FIXME: constraint subnet >= 1 and subnet <= 255
    #: The meter subnet, this chooses what subnet the physical meter will have.
    subnet = Column(Integer, default=255, nullable=False, info={"label": _("Meter Subnet")})

    #: State of the meter is Off (default)
    STATE_OFF = 0

    #: State of the meter is On
    STATE_ON = 1

    #: State of the meter is Automatic, the meters wallet balance will control the state
    STATE_AUTO = 2

    #: The theoretical correct state of the meter.
    #: .. note :: This value may not match the :attr:`~sparkmeter.models.Meter.current_state`
    #: if the meter has not yet received a command to set the correct value or the meter
    #: has not yet reported the changed state.
    state = Column(
        Integer, default=STATE_OFF, nullable=False, info={"label": _("State")}
    )  # 0=off, 1=on, 2=auto

    #: A reference to the meter
    meter = relationship("Meter", foreign_keys=[meter_id])

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            ground_t = get_table_by_name("ground")
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                group.format_trigger_attr(cls.meter_id) == Meter.id,
                Meter.ground_id == ground_t.c.id,
            )

    @property
    def active(self):
        """Active property getter, inverse proxying config.active, mainly for forms."""
        return not self.hidden


@syncchannel(SYNC_CHANNEL_METER)
class MeterTag(BaseDomain):
    """
    Meter tag.

    A tag can be used to group a meter, geographically for example.

    The tag is just a free-form string.
    """

    __tablename__ = "meter_tag"
    __table_args__ = (UniqueConstraint("name", name="meter_tag_name"),)

    #: Name of the tag
    name = Column(String, info={"label": _("Name")})

    @classmethod
    def get_default_id(cls, context):
        """Get the default id for a MeterTag object."""
        return as_uuid(context.current_parameters["name"])

    @classmethod
    def add(cls, name, meter):
        """Add a tag to a meter.

        Add the tag to a meter, create the tag and the mapping if they don't exist.

        :param name: name of the meter.
        :param meter: meter to add the tag to.
        """
        created, self = cls.get_one_or_create(name=name)
        if created:
            meter.tags.append(self)
        else:  # pragma: nocoverage
            meters_tags = MetersTags.get_one_or_create(meter=meter, tag=self).object
            meters_tags.active = True

    @classmethod
    def remove(cls, name, meter):
        """Remove a tag from a meter.

        Remove a tag from a meter and update the mapping.

        :param name: name of the meter.
        :param meter: meter to remove the tag from.
        """
        self = cls.query.filter_by(name=name).one()
        meters_tags = MetersTags.get_one_or_create(meter=meter, tag=self).object
        meters_tags.active = False


@syncchannel(SYNC_CHANNEL_METER)
class MetersTags(BaseDomain):
    """Meter Tag mapping table."""

    __tablename__ = "meters_tags"

    #: Id of the tag
    tag_id = Column(UUIDType(binary=False), ForeignKey("meter_tag.id"), nullable=False)

    #: Id of the meter
    meter_id = Column(UUIDType(binary=False), ForeignKey("meter.id"), nullable=False)

    #: If this tag is active, this is True when created and set to False when removed
    #: in the user interface
    active = Column(Boolean, default=True, nullable=False)

    #: Reference to the tag of this mapping
    tag = relationship("MeterTag")

    #: Reference to the meter for this mapping
    meter = relationship("Meter")

    @classmethod
    def sync_init(cls, group):
        """Initialize both cloud and ground for this table."""
        group.set_key_columns(cls.tag_id, cls.meter_id)
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            ground_t = get_table_by_name("ground")
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                group.format_trigger_attr(cls.meter_id) == Meter.id,
                Meter.ground_id == ground_t.c.id,
            )

    @classmethod
    def get_default_id(cls, context):
        """Get the default id for a MetersTags object."""
        return as_uuid(context.current_parameters["tag_id"], context.current_parameters["meter_id"])


@syncchannel(SYNC_CHANNEL_METER)
class MeterScalars(BaseDomain):
    """
    Scalars and their combinations

    This represents the multipliers required for transforming values sent to meters.
    """

    __tablename__ = "meter_scalars"

    # Name of the scalar
    name = Column(String, unique=True)

    # Scalar for frequency
    frequency_scalar = Column(Numeric(asdecimal=False), nullable=False)

    # Scalar for frequency
    voltage_scalar = Column(Numeric(asdecimal=False), nullable=False)

    # Scalar for frequency
    current_scalar = Column(Numeric(asdecimal=False), nullable=False)

    # Scalar for frequency
    energy_scalar = Column(Numeric(asdecimal=False), nullable=False)

    # Scalar for frequency
    power_scalar = Column(Numeric(asdecimal=False), nullable=False)

    # Scalar for frequency
    power_factor_scalar = Column(Numeric(asdecimal=False), nullable=False)

    @classmethod
    def get_by_name(cls, name):
        """Get a meter scalar by its name

        :param name: The name of the meter to fetch
        :rtype: MeterScalars | None
        :returns the meter scalars or None if they cannot be found
        """
        return cls.query.filter(func.lower(cls.name) == func.lower(name)).scalar()


@syncchannel(SYNC_CHANNEL_METER)
class MeterModels(BaseDomain):
    """
    Scalars and their combinations

    This represents a meter product line (e.g. SM5R, SM60RP, etc.)
    """

    __tablename__ = "meter_models"

    name = Column(String, unique=True, nullable=False)

    inrush_limit = Column(Numeric(asdecimal=False), nullable=False)

    continuous_limit = Column(Numeric(asdecimal=False), nullable=False)

    phase_count = Column(Integer, nullable=False)

    scalars_id = Column(UUIDType(binary=False), ForeignKey("meter_scalars.id"), nullable=False)

    scalars = relationship("MeterScalars", lazy="joined")

    enabled = Column(Boolean, default=True, nullable=False)

    @classmethod
    def get_by_name(cls, name, include_disabled=False):
        """Get a meter model by its name

        :param name: The name of the meter to fetch
        :rtype: MeterModels | None
        :returns: the meter model or None if it cannot be found
        """
        query = cls.query.filter(func.lower(cls.name) == func.lower(name))
        if not include_disabled:
            query = query.filter(cls.enabled == true())
        return query.scalar()

    @classmethod
    def get_by_serial(cls, serial, include_disabled=False):
        """Get the model for a meter with the given serial.

        :param serial: The desired serial
        :rtype: MeterModels | None
        :returns: The meter model, or None if it cannot be found
        """
        match = Meter.SERIAL_RE.match(serial)
        if not match:
            raise MeterError(
                MeterError.INVALID_SERIAL, "serial {} is not a valid meter serial".format(serial)
            )
        return cls.get_by_name(match.group("product_code"), include_disabled=include_disabled)

    @classmethod
    def get_lowest_inrush_current(cls):
        """Get the lowest inrush current used.

        :rtype: float
        :returns: The lowest inrush current (in amps) associated with a model
        """
        return cls.query.with_entities(func.min(cls.inrush_limit)).scalar()

    @classmethod
    def get_model_counts(cls, include_disabled=False):
        """Get a collection of all meter models (and the number of meters of that model on the site)

        :param include_disabled: `True` if disabled models should be included, `False` otherwise.
        :returns: A named tuple of id, name, continuous_limit, inrush_limit, and count
        """
        return (
            select(
                cls.id,
                cls.name,
                cls.continuous_limit,
                cls.inrush_limit,
                cls.phase_count,
                func.count(Meter.__table__.c.id).label("count"),
            )
            .select_from(cls.__table__.outerjoin(Meter, cls.id == Meter.model_id))
            .group_by(cls.__table__.c.id)
            .having(or_(func.count(Meter.__table__.c.id) > 0, cls.enabled == true()))
            .order_by(cls.name)
        )


@syncchannel(SYNC_CHANNEL_METER)
class Meter(BaseDomain):
    """
    The Meter object.

    This is the base meter object that will be used in the code and has
    the references to all the parts of the meter.

    This also has all of the meter methods, properties, and scalars.

    The user editable meter config is stored in the MeterConfig model,
    and the system controlled settings are kept in the MeterSystemInfo model.
    Those are both referenced inside this model so the data can be accessed from here.

    This is done so that when syncing there should be no conflicts between user edits and system edits.

    """

    __tablename__ = "meter"
    __table_args__ = (
        UniqueConstraint("code", "ground_id", name="meter_code_ground_unique"),
        UniqueConstraint("serial", name="meter_serial_unique"),
        CheckConstraint(r"serial ~* '^[\dA-Z]+-\d{2}-[\dA-F]{8}$'", name="meter_serial_format"),
    )

    #: This code is used to identify the meter on the sparkmac network.
    #: It can only be written on initial creation, then is uneditable by the user.
    #: Currently this is loosely tied to the UniqueID on the meter QR label by convention only.
    code = Column(Integer, nullable=False)

    #: This globally unique product code used to identify the meter.
    #: It can only be written on initial creation, then is uneditable by the user.
    #: This is the UniqueID on the meter QR label.
    #: The serial has 3 parts to it. [Product Code]-[Version]-[GID MAC]
    #: For now the GID MAC is used to generate the code (by convention only).
    #: This is a hybrid property field where upon being set the value is converted to upper case.
    _serial = Column("serial", String, nullable=False)

    #: the regex for the serial, used in form validation and for extracting the product_code
    SERIAL_RE = SERIAL_RE

    #: A customer meter
    TYPE_CUSTOMER = "customer"

    #: A totalizer meter
    TYPE_TOTALIZER = "totalizer"

    #: The meter type, either customer meter or totalizer meter
    meter_type = Column(String, default=TYPE_CUSTOMER, nullable=False)

    #: meter address, where the meter is actually located
    address_id = Column(UUIDType(binary=False), ForeignKey("address.id"), nullable=False)

    #: The ground this meter belongs to
    ground_id = Column(UUIDType(binary=False), ForeignKey("ground.id"), nullable=False)

    #: Selected meter driver id from the registered driver list
    provider_id = Column(String, nullable=True)

    model_id = Column(UUIDType(binary=False), ForeignKey("meter_models.id"))

    # Relationships
    address = relationship("Address")  # type: Address

    ground = relationship("Ground")  # type: Ground

    model = relationship(
        "MeterModels", primaryjoin="and_(Meter.model_id == MeterModels.id)", uselist=False, lazy="joined"
    )  # type: MeterModels

    #: The meter config for this meter
    config = relationship(
        "MeterConfig", primaryjoin="and_(Meter.id == MeterConfig.meter_id)", uselist=False, overlaps="meter"
    )  # type: MeterConfig

    sparkmac = relationship(
        "SparkmacNode", primaryjoin="and_(Meter.id == SparkmacNode.meter_id)", uselist=False, overlaps="meter"
    )  # type: SparkmacNode

    system_info = relationship(
        "MeterSystemInfo",
        primaryjoin="and_(Meter.id == MeterSystemInfo.meter_id)",
        uselist=False,
        overlaps="meter",
    )  # type: MeterSystemInfo

    #: The credit_wallet for this meter, only set for customer meters
    credit_wallet = relationship(
        "Wallet",
        primaryjoin="and_(foreign(Meter.id) == Wallet.meter_id, Wallet.wallet_type == 'credit')",
        single_parent=True,
        cascade="all, delete-orphan",
    )  # type: Wallet

    #: The debt_wallet for this meter, only set for customer meters
    debt_wallet = relationship(
        "Wallet",
        primaryjoin="and_(foreign(Meter.id) == Wallet.meter_id, Wallet.wallet_type == 'debt')",
        single_parent=True,
        cascade="all, delete-orphan",
        overlaps="credit_wallet",
    )  # type: Wallet

    #: The plan_wallet for this meter, only set for customer meters
    plan_wallet = relationship(
        "Wallet",
        primaryjoin="and_(foreign(Meter.id) == Wallet.meter_id, Wallet.wallet_type == 'plan')",
        single_parent=True,
        cascade="all, delete-orphan",
        overlaps="credit_wallet,debt_wallet",
    )  # type: Wallet

    #: The customer that owns this meter, only set for customer meters
    customer = relationship(
        "Customer", primaryjoin="Customer.meter_id == Meter.id", uselist=False, overlaps="meter"
    )  # type: Customer

    #: The billing information for this, only set for customer meters
    billing = relationship(
        "MeterBilling", primaryjoin="MeterBilling.meter_id == Meter.id", uselist=False, overlaps="meter"
    )  # type: MeterBilling

    #: the tags for this meter
    tags = relationship(
        "MeterTag",
        secondary=MetersTags.__table__,
        secondaryjoin=and_(MetersTags.tag_id == MeterTag.id, MetersTags.active == true()),
        order_by="MeterTag.name",
        overlaps="meter,tag",
    )  # type: MeterTag

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            ground_t = get_table_by_name("ground")
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                ground_t.c.id == group.format_trigger_attr(cls.ground_id),
            )

    def convert_to_customer_meter(self, tariff=None):
        """Add customer, billing and wallets data for this meter."""
        self.customer = Customer()
        self.billing = MeterBilling(tariff=tariff)
        # the query flush in add_wallets breaks the form because meter has not yet been populated
        # with the other required fields.
        with sql.session.no_autoflush:
            self.add_wallets()

    def convert_to_totalizer_meter(self):
        """Remove customer, billing and wallets data for this meter."""
        logger.info("Removing transactions for meter %s", self.serial)
        for trans_view, count in self.get_transaction_view():
            trans = Transaction.query.get(trans_view.id)
            sql.session.delete(trans)

        logger.info("Removing Customer and Billing for meter %s", self.serial)
        sql.session.delete(self.customer)
        sql.session.delete(self.billing)

        logger.info("Removing wallets for meter %s", self.serial)
        sql.session.delete(self.credit_wallet)
        sql.session.delete(self.debt_wallet)
        sql.session.delete(self.plan_wallet)

    def add_wallets(self):
        """Add wallets to a Meter.

        This should be called after creating a meter.
        """
        # FIXME: Replace this with constraints
        session = self.session
        if session.query(Wallet).filter_by(meter_id=self.id).count():  # pragma: nocoverage
            raise TypeError("Wallets already exists")

        logger.info("Creating wallets for meter %s" % (self.id,))
        wallet_types = [
            ("credit_wallet", Wallet.TYPE_CREDIT),
            ("debt_wallet", Wallet.TYPE_DEBT),
            ("plan_wallet", Wallet.TYPE_PLAN),
        ]
        for attr, wallet_type in wallet_types:
            wallet = Wallet(
                id=uuid.uuid4(),
                wallet_type=wallet_type,
                grid_id=self.ground.id,
                meter_id=self.id,
                negative_permitted=False,
                value=0,
            )
            setattr(self, attr, wallet)

    @property
    def description(self):
        """Describe this meter."""
        return "{ground_name}, {title}".format(
            ground_name=getattr(self.ground, "name", "UNASSOCIATED"),
            title=self.title(),
        )

    @property
    def tariff(self):
        """Get tariff for this meter, only set for a customer meter."""
        if self.billing is None:
            return None
        return self.billing.tariff

    @tariff.setter
    def tariff(self, tariff):
        """Set tariff for this meter, only set for a customer meter."""
        self.billing.tariff = tariff

    @classmethod
    def get_by_code(cls, ground, code):
        """Get a meter by code/mac address."""
        return sql.session.query(cls).filter_by(ground=ground, code=code).scalar()

    @classmethod
    def get_by_serial(cls, serial):
        """Get a meter by the UniqueID serial
        :rtype: Meter | None
        :returns the meter or None if it cannot be found
        """
        return cls.query.filter(func.lower(cls.serial) == func.lower(serial)).scalar()

    @classmethod
    def get_by_customer_code(cls, customer_code):
        """Get a meter by a customer code
        :param customer_code: customer code
        :type customer_code: str
        :rtype: Meter | None
        :returns the meter or None if it cannot be found
        """
        return (
            cls.query.filter(Meter.id == Customer.meter_id)
            .filter(func.lower(Customer.code) == func.lower(customer_code))
            .scalar()
        )

    @classmethod
    def get_all_customer_meters(cls):
        """Get all customer meters."""
        return cls.query.filter(Meter.meter_type == Meter.TYPE_CUSTOMER).all()

    @classmethod
    def get_all_totalizer_meters(cls):
        """Get all customer meters."""
        return cls.query.filter(Meter.meter_type == Meter.TYPE_TOTALIZER).all()

    @classmethod
    def state_from_string(cls, state):
        """Convert a string on/off/auto to a meter config state."""
        if state == "on":
            config_state = MeterConfig.STATE_ON
        elif state == "off":
            config_state = MeterConfig.STATE_OFF
        elif state == "auto":
            config_state = MeterConfig.STATE_AUTO
        else:
            raise ValueError(state)
        return config_state

    @property
    def state_text(self):
        """Readable meter state."""
        txt = [_("Off"), _("On")][self.state_value]
        if self.config.state == MeterConfig.STATE_AUTO:
            txt = _("Auto (%(state)s)", state=txt)
        return txt

    @property
    def state_value(self):
        """Meter relay boolean state."""
        state = self.config.state
        # Auto state means that the plan and the funds will decide if the meter
        # should be turned on or off
        if state == MeterConfig.STATE_AUTO:
            tariff = self.tariff
            # If the current tariff includes a plan and it is not running it
            if tariff is not None and tariff.plan_enabled and not self.billing.is_running_plan:
                state = MeterConfig.STATE_OFF
            # If we don't have enough credits, in either the plan wallet or the
            # prepaid credits
            elif (
                self.plan_wallet is not None
                and self.credit_wallet is not None
                and self.plan_wallet.value <= 0
                and self.credit_wallet.value <= 0
            ):
                state = MeterConfig.STATE_OFF
            else:
                state = MeterConfig.STATE_ON

            # check if the daily energy limit is enabled, and if we have exceeded the daily limit
            if tariff is not None and tariff.daily_energy_limit_enabled:
                daily_energy_consumed = self.current_daily_energy
                if daily_energy_consumed is not None:
                    if daily_energy_consumed >= tariff.daily_energy_limit_value:
                        state = MeterConfig.STATE_OFF
        return state

    @property
    def current_state_text(self):
        """Readable current state of the meter based on the last reading."""
        return MeterState.get_state_translation_from_id(self.system_info.current_state)

    @hybrid_property
    def serial(self):
        """Serial hybrid property, allowing for an upper case serial."""
        return self._serial

    @serial.setter
    def serial(self, value):
        """Setter for the serial field, to make sure the value is upper case."""
        self._serial = value.upper()

    @property
    def scalars(self):
        """The meter scalars for this meter"""
        try:
            return self.model.scalars
        except AttributeError:
            raise MeterError(
                MeterError.UNKNOWN_MODEL,
                "Cannot retrieve scalars for model with serial: {}".format(self.serial),
            )

    @property
    def continuous_current_limit(self):
        """The total current this meter can continuously support."""
        try:
            return self.model.phase_count * self.model.continuous_limit
        except AttributeError:
            raise MeterError(
                MeterError.UNKNOWN_MODEL,
                "Cannot retrieve attributes for model with serial: {}".format(self.serial),
            )

    def get_wallet(self, wallet_type):
        """Get a wallet for a given wallet type.

        :raises sqlalchemy.orm.exc.NoResultFound: if no wallets are in the database.
        """
        return self.session.query(Wallet).filter_by(meter_id=self.id, wallet_type=wallet_type).one()

    def is_customer_meter(self):
        """Figure out if this is a customer meter."""
        return self.meter_type == Meter.TYPE_CUSTOMER

    def is_totalizer_meter(self):
        """Figure out if this is a totalizer meter."""
        return self.meter_type == Meter.TYPE_TOTALIZER

    def get_dataframe(self, since, before, fields):
        """Get a pandas dataframe of this meter's reading data."""
        import pandas  # lazy load pandas to avoid loading it into memory when not needed

        field_set = set(fields)
        columns = [getattr(Reading, field) for field in field_set]
        # make sure heartbeat_end is in the list of fields to query
        columns.append(Reading.heartbeat_end)

        query = (
            sql.session.query(*columns)
            .filter_by(meter=str(self.code))
            .filter(Reading.heartbeat_end.between(since, before))
        )
        c = query.statement.compile(sql.engine)
        df = pandas.read_sql(sql=c.string, con=sql.engine, params=c.params, index_col="heartbeat_end")

        # FIXME: do the sorting in postgres instead of pandas
        df = df.sort_index()
        return df

    def title(self):
        """Meter object display title."""
        return _("Meter %(serial)s", serial=self.serial)

    def get_transaction_view(self):
        """Get the transaction data for this meter.

        This will be used to display the list of transactions on the meter page
        :returns: a list of attributes that will be used in the meter page.
        """
        view = TransactionView.get_transaction_view(meter=self)
        return view

    def get_last_placed_transaction(self):
        """Get the last transaction that was placed for this meter.

        Will return None if there hasn't been any transaction placed.
        """
        return (
            Transaction.query.filter(Transaction.state == Transaction.STATE_PROCESSED)
            .filter(and_(Transaction.to_wallet_id == Wallet.id, Wallet.meter_id == self.id))
            .order_by(Transaction.created.desc())
            .limit(1)
            .scalar()
        )

    def get_latest_reading(self):
        """Get the latest reading on the meter

        :return: A reading object or None
        :rtype: Reading or None
        """
        return Reading.get_by_meter_code(self.code).first()

    def is_new_cycle(self, date):
        """Check if we should start a new periodic billing cycle.

        :param date: the time we need to check against, typically from reading heartbeat
        :type date: a datetime.datetime object
        :returns: `True` if we are in a new periodic billing cycle, `False` otherwise.
        """

        # if this is the first cycle recorded, start unconditionally.
        if self.billing.last_cycle_start is None:
            return True
        # if the current plan hasn't expired yet, don't start a new cycle.
        if (
            self.billing.last_plan_expiration_date is not None
            and date < self.billing.last_plan_expiration_date
        ):
            return False
        # if the cycle start date computed for this tariff would be later than the current
        # cycle start date stored by the meter, a new cycle should start.
        return self.tariff.get_last_cycle_start(date) > self.billing.last_cycle_start

    def _needs_update(
        self, current_state=unset, current_load_limit=unset, override_meter_state=False, nominal_voltage=None
    ):
        """
        Check the state/powerlimit to determine if a meter needs to be updated.
        """

        # FIXME: make sure this can handle totalizers (tariff less meters)
        if current_state is unset or current_load_limit is unset:
            msg = "{} is requesting update by force (load_limit={}, state={})."
            logger.info(msg.format(self.title(), current_load_limit, current_state))
            return True

        if current_state is None or current_load_limit is None:
            msg = "{} has unknown current load_limit/state, requesting update (load_limit={}, state={})."
            logger.info(msg.format(self.title(), current_load_limit, current_state))
            return True

        def log_current_state(state):
            msg = "%s has a current state of %s, but it should be %s, requesting update."
            current_state_text = MeterState.get_state_translation_from_id(current_state)
            logger.info(msg, self.title(), current_state_text, state)

        if override_meter_state:
            if current_state != MeterState.STATE_OFF.id:
                log_current_state("Off (override enabled)")
                return True
        elif self.is_customer_meter():  # Totalizers don't have power limits
            nominal_voltage = nominal_voltage or parameters.NOMINAL_VOLTAGE
            tariff_load_limit = self.tariff.get_current_load_limit()
            continuous_power = self.continuous_current_limit * nominal_voltage
            power_limit = min(continuous_power, tariff_load_limit)
            if current_load_limit is not None and current_load_limit != power_limit:
                msg = "%s has a load limit of %s, but it should be %s, requesting update."
                logger.info(msg, self.title(), current_load_limit, power_limit)
                return True

            # Explanation:
            #    self.state_value is 0 (off) or 1 (on)
            #    current_state is 0-9, 0 (off) 1-9 (on)
            #
            # FIXME: This should be two checks (to be refactored):
            #    if known meter state is off but current state is > 0 OR
            #       known meter state is on but current state == 0
            if bool(self.state_value) != bool(current_state):
                log_current_state(self.state_text)
                return True

        logger.info("%s has state and load limit are up to date, skipping update.", self.title())
        return False

    def set_state(self, state):
        """Update the meter state for this meter.

        :param state: the state to set.
        """
        if state != self.config.state:
            self.config.state = state
            event = Event.create(Event.TYPE_METER_STATE_CHANGED, obj=self)
            self.session.add(event)

    def reset_state(self):
        """Reset the meter state for this meter."""
        event = Event.create(Event.TYPE_METER_STATE_CHANGED, obj=self)
        self.session.add(event)

    def send_set_config_unconditionally(self):
        """Send a set-config regardless of known state/limit.

        Send a set-config without taking into account the known database
        state as we store in meter_system_info.

        Called from:
         - Creating a new meter
         - Reset a meter
         - ./manage.py send_config
         - Application startup
         - Tariff change power limit
        """
        return self._maybe_send_set_config(state=unset, load_limit=unset)

    def send_set_config_based_on_system_info(self, nominal_voltage=None):
        """Send a set-config if its desired state is conflicting

        Send a set-config based on the known state in the database that
        we store in meter_system_info conflicts with the desired state.
        Both state and load_limit are checked and updated if needed.

        For example:
        - scheduled load limit has crossed an hour with different current
        - Current state is not consistent with the operating mode.

        Called from:
         - Transaction placed
         - Application startup

        Nominal system voltage can be provided to minimize DB roundtrips
        during calculation.
        """
        return self._maybe_send_set_config(
            nominal_voltage=nominal_voltage,
            state=self.system_info.current_state,
            load_limit=self.system_info.current_user_power_limit,
        )

    def send_set_config_based_on_reading(self, reading):
        """Send a set-config based on an information in a reading.

        Send a set-config based on the values in a reading.

        Called from:
         - Incoming reading (state & power limit from Reading instance)
        """
        return self._maybe_send_set_config(state=reading.state, load_limit=reading.user_power_limit)

    def get_total_balance(self):
        """Get the total balance associated with this meter, sum of credit and
        plan wallets.
        :returns: total balance
        """
        return self.credit_wallet.value + self.plan_wallet.value

    def has_low_balance(self):
        """
        :returns True if the total balance is less than the low balance threshold
        """
        threshold = self.tariff.low_balance_threshold
        if threshold is None:
            return False
        return self.get_total_balance() <= threshold

    def _maybe_send_set_config(self, state=None, load_limit=None, nominal_voltage=None):
        """
        Send a set config packet to the meter.

        :param start: expected meter state, or ``None``
        :param load_limit: expected load limit or ``None``
        :param nominal_voltage: nominal system voltage or ``None``
        :returns: ``True`` if a packet was sent, ``False`` otherwise

        This is being called from:
        """
        override_meter_state = self.ground.private.override_meter_state

        # FIXME: if we ever allow meter creation in heroku, this will not get
        # executed after syncing so this should be added to the eventual
        # post_sync update hook
        if config["HEROKU"] or not self._needs_update(
            override_meter_state=override_meter_state,
            current_load_limit=load_limit,
            current_state=state,
            nominal_voltage=nominal_voltage,
        ):
            return False

        power_limit = 65535
        command = "disable"
        balance = 0
        low_balance = False
        provider_uses_engineering_units = bool(getattr(self, "provider_id", None))

        if self.is_customer_meter():
            tariff_load_limit = self.tariff.get_current_load_limit()

            nominal_voltage = nominal_voltage or parameters.NOMINAL_VOLTAGE

            continuous_power = self.continuous_current_limit * nominal_voltage
            power_limit = min(continuous_power, tariff_load_limit)
            if not provider_uses_engineering_units:
                power_limit = old_div(power_limit, self.scalars.power_scalar)
            if self.state_value == MeterConfig.STATE_ON and not override_meter_state:
                command = "enable"
            else:
                command = "disable"
            balance = self.get_total_balance()
            low_balance = self.has_low_balance()

        # don't allow a current_limit greater than the max possible value
        current_limit = self.model.inrush_limit
        if not provider_uses_engineering_units:
            current_limit = old_div(current_limit, self.scalars.current_scalar)
        current_limit = min(current_limit, 65535)

        send_set_config(
            mac=self.code,
            command=command,
            load_limit=power_limit,
            subnet=self.config.subnet,
            current_limit=current_limit,
            balance=balance,
            low_balance=low_balance,
            firmware_version=self.system_info.firmware,
        )
        return True

    @property
    def product_code(self):
        """
        The product code for this meter.

        The product code is derived from the first part meter serial.
        Serial: [Product Code]-[Version]-[GID MAC]
        """
        return self.SERIAL_RE.match(self.serial).group("product_code")

    def remove(self):
        """Remove a meter from the system.

        This deletes a meter and tables referencing it, including
        wallets and transactions, but does not remove readings.
        """

        # About to delete this, so make a copy
        serial = self.serial

        logger.info("Removing transactions for meter %s", serial)
        for trans_view, count in self.get_transaction_view():
            trans = Transaction.query.get(trans_view.id)
            sql.session.delete(trans)

        logger.info("Removing meter %s and associated tables", serial)
        if self.is_customer_meter():
            self.convert_to_totalizer_meter()
        sql.session.delete(self.config)
        sql.session.delete(self)
        sql.session.delete(self.address)
        sql.session.delete(self.system_info)
        sql.session.delete(self.sparkmac)

    def _check_ground_access(self, prefix):
        from sparkmeter.ground.grounddomain import Ground

        ground = Ground.get_by_serial(config["SERIAL"])
        if not config["HEROKU"] and ground != self.ground:
            message = prefix + _(
                "transactions for this meter can only be placed on ground '%(ground)s'.",
                ground=self.ground.name,
            )
            raise TransactionError(TransactionError.ERROR_PERMISSION_DENIED, message)

    def check_can_sell_from(self, user):
        """
        Checks if a user can place transactions from this meter.
        This is used for repayig debts.

        :param user: the user to check
        :type user: User
        :raises TransactionError: if it cannot be sold from
        """

        prefix = _(
            "user '%(username)s' cannot repay debt for meter '%(serial)s': ",
            username=user.username,
            serial=self.serial,
        )

        if user.is_api():
            raise TransactionError(
                TransactionError.ERROR_PERMISSION_DENIED, prefix + _("api users cannot repay debt.")
            )

        self._check_ground_access(prefix)

        if self.ground not in user.grounds:
            raise TransactionError(
                TransactionError.ERROR_PERMISSION_DENIED,
                prefix + _("user is not associated with ground '%(ground)s'.", ground=self.ground.name),
            )

    def check_can_sell_to(self, user):
        """
        Checks if a user can place transactions to this meter.
        This is used to buy credits.

        :param user: the user to check
        :type user: User
        :raises TransactionError: if it cannot be sold from
        """
        if user.is_api():
            return

        prefix = _(
            "user '%(username)s' cannot buy credit for meter '%(serial)s': ",
            username=user.username,
            serial=self.serial,
        )

        self._check_ground_access(prefix)

        if self.ground not in user.grounds:
            raise TransactionError(
                TransactionError.ERROR_PERMISSION_DENIED,
                prefix + _("user is not associated with ground '%(ground)s'.", ground=self.ground.name),
            )

    def maybe_convert_negative_balance_to_debt(self):
        """
        Ensure that negative balance is converted into debt.

        This requires the following conditions to be true
        - meter must be pre-paid
        - there must be a negative balance
        - negative balance option must be turned on

        :return: True if debt was added, False if not
        """
        # Only post-paid meters should have their debt converted
        if self.config.state != MeterConfig.STATE_AUTO:
            return False
        # Negative balance required to have something to convert to debt
        if self.credit_wallet.value >= 0:
            return False
        # If we allow negative balance, do not convert
        if parameters.ALLOW_NEGATIVE_BALANCE:
            return False

        logger.info(
            "Converting {} credit balance for meter {} into debt".format(
                self.credit_wallet.value,
                self.serial,
            )
        )
        self.debt_wallet.value += abs(self.credit_wallet.value)
        self.credit_wallet.value = 0
        return True

    def is_new_day(self):
        """
        Check if we are in a new day with regards to the daily energy limit.

        This checks if the last time we reset the energy counter is older than
        the time the tariff defines as the last time we should have reset it.
        This will return true on or any time after the reset minute as long
        as we have not yet processed the reset.

        :returns: `True` if we should reset the counter because it is a new day, `False` otherwise
        :rtype: bool
        """
        # this meter daily energy limit has never been reset, so lets start the counter now
        if self.billing.last_daily_energy_limit_reset_datetime is None:
            return True

        tariff_reset_dt = self.tariff.last_daily_energy_limit_reset_datetime()
        meter_last_reset_dt = self.billing.last_daily_energy_limit_reset_datetime
        # tariff_reset_dt is inclusive and will update to today on the minute that the reset time happens.
        # It always shows the last time it was supposed to reset so this operator must only be gt because
        # otherwise the result would always be true. So this is inclusive, but doesnt look like it here.
        return tariff_reset_dt > meter_last_reset_dt

    @property
    def current_daily_energy(self):
        """
        Check how much energy has been consumed today.

        This checks to see how much energy has been consumed since the last daily energy limit reset time.
        If no readings have come in since the energy limit was enabled then it will return None
        It will also return None if it is not a customer meter.

        :returns: kWh consumed since the last daily reset, or None if it can not yet be calculated
        :rtype: float
        """
        if self.billing and self.billing.last_daily_energy_limit_reset_value is not None:
            return self.system_info.last_energy - self.billing.last_daily_energy_limit_reset_value

    def update_from_reading(self, reading):
        """
        Perform any actions needed when updating a meter from a reading.

        This calls the update_from_reading on the meters system_info object.
        This will reset the daily energy limit if the reading is past todays reset time.

        :returns: `None`
        :rtype: None
        """
        # update the system info
        self.system_info.update_from_reading(reading)

        # update the daily energy limit reset time
        if self.is_customer_meter():
            if self.tariff.daily_energy_limit_enabled:
                if self.is_new_day():
                    # the reset time has passed, time to reset the energy limit for the day
                    msg = (
                        "Meter {} has crossed the daily energy limit reset time. Resetting saved energy value"
                    )
                    logger.info(msg.format(self.serial))
                    tariff_reset_dt = self.tariff.last_daily_energy_limit_reset_datetime()
                    self.billing.last_daily_energy_limit_reset_datetime = tariff_reset_dt
                    self.billing.last_daily_energy_limit_reset_value = self.system_info.last_energy
                    self.session.add(self.billing)
            else:
                # the daily energy limit is not enabled, lets reset their fields
                # to None so old data doesn't make it into future calculations
                self.billing.last_daily_energy_limit_reset_datetime = None
                self.billing.last_daily_energy_limit_reset_value = None
                self.session.add(self.billing)


class MeterView(BaseView):
    """
    A database view of meter and related columns.
    This contains aggregated columns of a meter list, suitable for usage within
    a form and listing.
    """

    __tablename__ = "meter_view"

    #: If the meter is active (!meter.hidden)
    active = Column(Boolean, default=False, nullable=False)

    #: Address street1 (address.street1)
    address_street1 = Column(String)

    #: Address street2 (address.street2)
    address_street2 = Column(String)

    #: Address city (address.city)
    address_city = Column(String)

    #: Address state (address.state)
    address_state = Column(String)

    #: Address postalcode (address.postalcode)
    address_postalcode = Column(String)

    #: Address country (address.country)
    address_country = Column(String)

    #: Address coordinates (address.coords)
    address_coords = Column(String)

    # FIXME: Rename to mac or gid_mac
    #: Meter code (meter.code)
    code = Column(Integer, nullable=False)

    # Value in the credit wallet (credit_wallet.value)
    credit_value = Column(Float, default=0, nullable=False)

    #: Current meter state (meter_system_info.current_state)
    current_state = Column(Integer, default=MeterState.STATE_OFF.id)

    #: Customer id (customer.id)
    customer_id = Column(UUIDType(binary=False), ForeignKey("customer.id"), nullable=False)

    #: Customer name (customer.name)
    customer_name = Column(String, default="new customer")

    #: Customer code (customer.code)
    customer_code = Column(String)

    #: Customer phone number (customer.phone_number)
    customer_phone_number = Column(String)

    #: Customer phone number (customer.phone_number)
    customer_phone_number_verified = Column(Boolean, default=False)

    #: Current debt balance (debt_wallet.value)
    debt_value = Column(Float, default=0, nullable=False)

    #: Ground id (ground.id)
    ground_id = Column(UUIDType(binary=False), ForeignKey("ground.id"), nullable=False)

    #: Ground name (ground.name)
    ground_name = Column(String, nullable=False)

    #: Ground serial (ground.serial)
    ground_serial = Column(String, nullable=False)

    #: Selected meter driver id (meter.provider_id)
    provider_id = Column(String, nullable=True)

    model_id = Column(UUIDType(binary=False), ForeignKey("meter_models.id"), nullable=False)

    model_name = Column(String, nullable=False)

    #: If we are using billing plan (meter_billing.is_running_plan)
    is_running_plan = Column(Boolean, default=None)

    #: Start of last cycle (meter_billing.last_cycle_start)
    last_cycle_start = Column(DateTime, default=None)

    #: Last consumed energy (meter_system_info.last_energy)
    last_energy = Column(Float, default=0.0)

    #: Datetime of last consumed energy (meter_system_info.last_energy_datetime)
    last_energy_datetime = Column(DateTime, default=datetime.datetime.utcnow)

    #: last plan expiration date (meter_billing.last_plan_expiration_date)
    last_plan_expiration_date = Column(DateTime, default=None)

    #: Last plan payment date (meter_billing.last_plan_payment_date)
    last_plan_payment_date = Column(DateTime, default=None)

    #: Current plan balance (plan_wallet.value)
    plan_value = Column(Float, default=0, nullable=False)

    #: Type of meter (meter.meter_type)
    meter_type = Column(String, nullable=False)

    #: Meter serial (meter.serial)
    serial = Column(String, nullable=False)

    #: Sparkmac forwarding
    sparkmac_forwarding = Column(String, default=SparkmacNode.FORWARDING_FLOODING)

    #: Sparkmac flooding subnets
    sparkmac_flooding_subnets = Column(Integer, default=255)

    #: Sparkmac ttl (time to live)
    sparkmac_ttl = Column(Integer, default=15)

    #: Meter state (meter_config.state)
    state = Column(Integer, default=MeterConfig.STATE_OFF, nullable=False)

    #: Meter subnet (meter_config.subnet)
    subnet = Column(Integer, default=255, nullable=False)

    #: Tariff (tariff.id)
    tariff_id = Column(UUIDType(binary=False), ForeignKey("tariff.id"), nullable=False)

    #: Tariff name (tariff.name)
    tariff_name = Column(String, nullable=False)

    #: Tariff plan enabled (tariff.plan_enabled)
    tariff_plan_enabled = Column(Boolean, default=None)

    #: List of meter tags (meter_tag/meters_tags)
    tags = Column(ARRAY(String))

    #: Total energy consumed in the cycle (meter_billing.total_cycle_energy)
    total_cycle_energy = Column(Float, default=None)

    #: A reference to the ground
    ground = relationship("Ground")

    #: A reference to the tariff
    tariff = relationship("Tariff")

    #: A reference to the customer
    customer = relationship("Customer")

    model = relationship("MeterModels")

    @classmethod
    def validate_serial(cls, serial, ground=None):
        """
        Validate a meter serial.

        :param serial: meter serial
        :param ground: the ground object
        :raises MeterError: if the serial is invalid
        :raises MeterError: if a meter with that serial already exists
        :returns: The customer code and model
        """
        match = Meter.SERIAL_RE.match(serial)
        if not match:
            message = "serial {} is not a valid meter serial".format(serial)
            raise MeterError(MeterError.INVALID_SERIAL, message)

        code = int(Meter.SERIAL_RE.match(serial).group("gid_mac"), 16) & 0xFFFF
        if Meter.get_by_serial(serial) or Meter.get_by_code(ground, code):
            message = "meter with serial {} already exists".format(serial)
            raise MeterError(MeterError.DUPLICATE_SERIAL, message)

        model = MeterModels.get_by_serial(serial)
        if model is None:
            raise MeterError(MeterError.UNKNOWN_MODEL, "No model found for {}".format(serial))

        return code, model

    @classmethod
    def create_meter(cls, meter_type, ground, serial):
        """
        Create a new customer meter.

        :param meter_type: the kind of meter we want to create
        :param ground: the ground to create this meter on
        :param serial: the serial for this meter
        :return: a meter view for the newly created meter
        :raises MeterError: if the serial is invalid
        :raises MeterError: if a meter with that serial already exists
        """
        code, model = cls.validate_serial(serial=serial, ground=ground)

        self = MeterView()
        self.ground = ground
        self.meter_type = meter_type
        self.serial = serial
        self.code = code
        self.model = model
        self.state = config.get("NEW_METER_STATE")
        self.active = not config.get("NEW_METER_HIDDEN", True)
        self.subnet = config.get("NEW_METER_SUBNET")
        self.sparkmac_forwarding = config.get("NEW_METER_SPARKMAC_FORWARDING")
        self.sparkmac_flooding_subnets = config.get("NEW_METER_SPARKMAC_FLOODING_SUBNETS")
        self.sparkmac_ttl = config.get("NEW_METER_SPARKMAC_TTL")
        return self

    @property
    def meter(self):
        if self.id is not None:
            return Meter.get_by_id(self.id)

    @classmethod
    def get_view(
        cls,
        active=None,
        ground=None,
        tariff=None,
        user=None,
        meter_type=None,
        meter=None,
        customer_code=None,
        customer_phone_number=None,
    ):
        # type: (bool, Ground, Tariff, User, str, str, str) -> sqlalchemy.orm.query.Query[MeterView]
        """
        Get a sequence of view of meters, given a set of conditions.

        :param active: if active meters should be included
        :type active: bool | None
        :param ground: only show meters for this ground
        :type ground: Ground | None
        :param tariff: limit to meters of this tariff
        :type tariff: Tariff | None
        :param user: only show meters for this user
        :type user: User
        :param meter_type: the kind of meters to return, defaults to customer meter
        :type meter_type: str | None
        :param meter:
        :type meter: Meter | None
        :param customer_code:
        :type customer_code: str | None
        :param customer_phone_number:
        :type customer_phone_number: str | None
        :return: query result
        :rtype: sqlalchemy.orm.query.Query
        """
        q = cls.query
        if active is not None:
            q = q.filter_by(active=active)
        if ground is not None:
            q = q.filter_by(ground=ground)
        if tariff is not None:
            q = q.filter_by(tariff=tariff)
        if user is not None:
            users_grounds_t = get_table_by_name("users_grounds")
            q = q.filter(users_grounds_t.c.user_id == user.id, users_grounds_t.c.ground_id == cls.ground_id)
        if meter_type is not None:
            q = q.filter_by(meter_type=meter_type)
        if meter is not None:
            q = q.filter_by(id=meter.id)
        if customer_code is not None:
            q = q.filter(func.lower(cls.customer_code) == func.lower(customer_code))
        if customer_phone_number is not None:
            q = q.filter_by(customer_phone_number=customer_phone_number)

        q = q.order_by(cls.id)
        return q

    @classmethod
    def get_by_customer_id(cls, customer_id):
        """Get a meter view for a given customer id.
        :param customer_id: ID of customer to get
        :returns: ``None`` or a customer.
        """
        return cls.query.filter_by(customer_id=customer_id).scalar()

    @classmethod
    def get_active_meter_codes(cls):
        """Get a sequence of meter codes for all active meters.
        :returns: generator of meter codes.
        """
        for mv in cls.get_view(active=True).options(load_only(cls.code)):
            yield mv.code

    @classmethod
    def get_reading_request_data(cls, codes=None, shuffle_request_data=False):
        """Get data necessary for sending out read requests
        :param codes: sequence of codes to limit query to, if None, all active
        meters are queried
        :shuffle_request_data: radomize request data; if false, sort by
        MeterView.id
        :returns: generator of data for creating reading requests
        """
        from sparkmeter.tariff.tariffdomain import Tariff

        query = (
            select(
                MeterView.code,
                MeterView.plan_value,
                MeterView.credit_value,
                MeterSystemInfo.firmware,
                Tariff.low_balance_threshold,
                MeterSystemInfo.last_energy_datetime,
            )
            .select_from(
                sql.outerjoin(MeterView, MeterSystemInfo, MeterView.id == MeterSystemInfo.meter_id).outerjoin(
                    Tariff
                )
            )
            .where(MeterView.active)
            .order_by(func.random() if shuffle_request_data else MeterView.id)
        )
        if codes is not None:
            query = query.where(MeterView.code.in_(codes))

        cycle_length = config["HEARTBEAT_PERIOD"]
        cycle_length_delta = datetime.timedelta(minutes=config["HEARTBEAT_PERIOD"])
        now = datetime.datetime.utcnow()
        this_heartbeat_start = now.replace(
            microsecond=0, second=0, minute=(old_div(now.minute, cycle_length)) * cycle_length
        )
        last_heartbeat_start = this_heartbeat_start - cycle_length_delta
        last_last_heartbeat_start = last_heartbeat_start - cycle_length_delta

        prioritized_readings_query = query.where(
            MeterSystemInfo.last_energy_datetime == last_last_heartbeat_start
        )

        normal_priority_query = query.where(MeterSystemInfo.last_energy_datetime != last_last_heartbeat_start)

        reading_query_batches = []
        if config["PRIORITIZED_READ_QUEUE"]:
            reading_query_batches = [prioritized_readings_query, normal_priority_query]
        else:
            reading_query_batches = [query]

        for batch_query in reading_query_batches:
            for code, plan, credit, firmware, low_balance_threshold, last_read_time in sql.session.execute(
                batch_query
            ):
                credit = 0 if credit is None else credit
                plan = 0 if plan is None else plan
                total_balance = plan + credit
                has_low_balance = low_balance_threshold is not None and total_balance <= low_balance_threshold
                yield code, firmware, total_balance, has_low_balance

    def finish_creation(self):
        """Finish the creation of a meter"""
        self.session.flush()
        meter = self.meter
        event = Event.create(Event.TYPE_METER_CREATED, obj=meter)
        self.session.add(event)
        if not config["HEROKU"]:
            event.process()

    @property
    def customer_country_code(self):
        if self.customer_phone_number:
            number = phonenumbers.parse(self.customer_phone_number)
            return str(number.country_code)

        return getattr(self, "_customer_country_code", None)

    @customer_country_code.setter
    def customer_country_code(self, value):
        if self.customer_national_number:
            phone_number = parse_country_national(value, self.customer_national_number)
        else:
            phone_number = None
        self.customer_phone_number = phone_number
        self._customer_country_code = value

    @property
    def customer_national_number(self):
        national_number = getattr(self, "_customer_national_number", None)
        if national_number is not None:  # pragma: nocoverage
            return str(national_number)

        if self.customer_phone_number:
            number = phonenumbers.parse(self.customer_phone_number)
            return str(number.national_number)

    @customer_national_number.setter
    def customer_national_number(self, value):
        if hasattr(self, "_customer_country_code") and value:
            phone_number = parse_country_national(self._customer_country_code, value)
        else:
            phone_number = None
        self.customer_phone_number = phone_number
        self._customer_national_number = value

    def is_customer_meter(self):
        """Figure out if this is a customer meter."""
        return self.meter_type == Meter.TYPE_CUSTOMER

    def is_totalizer_meter(self):
        """Figure out if this is a totalizer meter."""
        return self.meter_type == Meter.TYPE_TOTALIZER
