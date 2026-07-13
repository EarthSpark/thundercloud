# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Reading domain models."""

import logging
from builtins import object, str

from dateutil.tz import tzutc
from flask_babel import lazy_gettext as _
from sqlalchemy import and_, false, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.expression import cast, func
from sqlalchemy.sql.schema import Column, UniqueConstraint
from sqlalchemy.sql.sqltypes import DateTime, Float, Integer, String

from sparkmeter.database.sync import (
    SYNC_CHANNEL_READING,
    SYNC_DIRECTION_GROUND_TO_CLOUD,
    SYNC_GROUP_GROUND,
    syncchannel,
)
from sparkmeter.database.tables import get_table_by_name
from sparkmeter.models import BaseDomain

logger = logging.getLogger(__name__)


class ReadingViewResult(object):
    """
    The result from a call to Reading.get_latest_reading_view(), which can be used
    in conjunction with a type checking.
    """

    city = None  # type: unicode
    state = None  # type: unicode
    street1 = None  # type: unicode
    street2 = None  # type: unicode
    serial = None  # type: str
    current_avg = None  # type: float
    current_max = None  # type: float
    current_min = None  # type: float
    energy = None  # type: float
    frequency = None  # type: float
    heartbeat_end = None  # type: datetime.datetime
    reading_id = None  # type: uuid.UUID
    reading_state = None  # type: str
    true_power_avg = None  # type: float
    true_power_inst = None  # type: float
    uptime = None  # type: float
    user_power_limit = None  # type: float
    voltage_avg = None  # type: float
    voltage_max = None  # type: float
    voltage_min = None  # type: float
    ground_name = None  # type: str
    ground_serial = None  # type: str


@syncchannel(SYNC_CHANNEL_READING)
class Reading(BaseDomain):
    """Reading Postgres SQLAlchemy Model.

    A reading captures all the meter state for a specific time period.
    """

    __tablename__ = "reading"
    __table_args__ = (
        UniqueConstraint("meter", "heartbeat_start", name="meter_heartbeat_start_unique"),
        UniqueConstraint("meter", "heartbeat_end", name="meter_heartbeat_end_unique"),
    )

    # Readings are only synced from Ground to Cloud
    sync_direction = SYNC_DIRECTION_GROUND_TO_CLOUD

    # FIXME: Change this into a proper meter reference
    #: Meter code
    meter = Column(String(64), info={"label": _("Meter")})

    #: The start of the time period this reading capture (in UTC)
    heartbeat_start = Column(DateTime, info={"label": _("Heartbeat Start")})

    #: The end of the time period this reading capture (in UTC)
    heartbeat_end = Column(DateTime, info={"label": _("Heartbeat End")})

    # BILLING DATA

    #: Kilowatt hours of energy used (in kWh)
    kilowatt_hours = Column(Float, default=0, info={"label": _("Kilowatt Hours")})

    #: Kilowatt Hours Period (in seconds)
    kilowatt_hours_period = Column(Integer, default=0, info={"label": _("Kilowatt Hours Period")})

    #: Cost for the energy used during this period (in credits)
    cost = Column(Float, default=0, info={"label": _("Cost")})

    #: Credit at the time of this reading (in credits)
    acct_credit = Column(Float, default=0, info={"label": _("Credit")})

    #: Plan credit at the time of this reading (in credits)
    acct_plan = Column(Float, default=0, info={"label": _("Plan")})

    #: Debit at the time of this reading (in credits)
    acct_debt = Column(Float, default=0, info={"label": _("Debt")})

    #: the rate that was used to calculate the cost. Either flat or an block rate average
    rate = Column(Float, default=0, info={"label": _("Rate applied")})

    #: if a tou was used, this stores the modifier value, which is percentage / 100
    tou_modifier = Column(Float, default=0, info={"label": "TOU modifier"})

    # READING DATA

    #: Minimum voltage during the heartbeat of this reading (in volts)
    voltage_min = Column(Float, default=999999, info={"label": "Min Voltage"})

    #: Maximum voltage during the heartbeat of this reading (in volts)
    voltage_max = Column(Float, default=0, info={"label": "Max Voltage"})

    #: Average voltage during the heartbeat of this reading (in volts)
    voltage_avg = Column(Float, default=0, info={"label": "Avg Voltage"})

    #: Average power factor during the heartbeat of this reading (in volt-amperes reactive)
    power_factor_avg = Column(Float, default=0, info={"label": "Avg Power Factor"})

    #: Average true power during the heartbeat of this reading (in watts)
    true_power_avg = Column(Float, default=0, info={"label": "Avg True Power"})

    #: Minimum current during the heartbeat of this reading (in amps)
    current_min = Column(Float, default=0, info={"label": "Min Current"})

    #: Maximum current during the heartbeat of this reading (in amps)
    current_max = Column(Float, default=0, info={"label": "Max Current"})

    #: Average current during the heartbeat of this reading (in amps)
    current_avg = Column(Float, default=0, info={"label": "Avg Current"})

    #: Frequency during the heartbeat of this reading (in Hz)
    frequency = Column(Float, info={"label": _("Frequency")})

    #: Instantaneous True Power during the heartbeat of this reading (in watts)
    true_power_inst = Column(Float, info={"label": _("Instantaneous True Power")})

    #: Energy used (in kWh)
    energy = Column(Float, info={"label": _("Energy")})

    #: Total uptime since the last time the meter was restarted (in seconds)
    uptime = Column(Integer, info={"label": _("Uptime")})

    #: State of the meter at the time of heartbeat end.
    state = Column(Integer, info={"label": _("State")})

    #: The ID of the meter snapshot
    snapshot_id = Column(postgresql.UUID, nullable=True)

    user_power_limit = Column(Integer, info={"label": _("User Power Limit")})
    true_power_avg = Column(Float, info={"label": _("Avg True Power")})
    power_factor_avg = Column(Float, info={"label": _("Avg Power Factor")})
    apparent_power_avg = Column(Float, info={"label": _("Avg Apparent Power")})

    @classmethod
    def sync_init(cls, group):
        """Initialize sync configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)

    @classmethod
    def get_max_total_balance_since(cls, meter, since):
        """Get the maximum total balance for a meter since a date.

        :param meter: the meter
        :param since: when we're checking against
        :returns: max total amount or 0.0 if there has been no readings for the period.
        """
        result = (
            cls.query.with_entities(func.max(cls.acct_credit + cls.acct_plan))
            .filter_by(meter=str(meter.code))
            .filter(cls.heartbeat_end >= since)
            .one()
        )
        return result[0] or 0.0

    @classmethod
    def get_by_tariff_date(cls, tariff, ground, start, end):
        """Get all readings by a tariff and a range.

        Queries will be performed with start of the range inclusive (<=)
        and end of the range exclusive (>).

        :param tariff: the tariff
        :param ground: restrict the sales accounts to a ground or ``None``
        :type ground: sparkmeter.ground.grounddomain.Ground
        :param start: start of the range
        :param end: end of the range
        :returns a query
        """
        meter_t = get_table_by_name("meter")
        meter_billing_t = get_table_by_name("meter_billing")
        return (
            cls.query.filter(cls.meter == cast(meter_t.c.code, String))
            .filter(cls.heartbeat_start.between(start, end))
            .filter(meter_billing_t.c.meter_id == meter_t.c.id)
            .filter(meter_billing_t.c.tariff_id == tariff.id)
            .filter(meter_t.c.ground_id == ground.id)
        )

    @classmethod
    def get_by_meter_code(cls, meter_code):
        """Get readings by meter code ordered from latest to oldest.

        This method is getting readings for a certain meter code,
        and picking the record with the latest `heartbeat_end` timestamp.

        :param meter_code: the code used to identify the meter on the sparkmac network
        :type meter_code: str

        :return: a query to retrieve all the readings for the meter code
        """
        return cls.query.filter_by(meter=str(meter_code)).order_by(cls.heartbeat_end.desc())

    @classmethod
    def get_latest_reading_view(cls, ground=None, user=None):
        """Get the latest readings for a given ground/user.

        This will be used by the latest reading page, which also uses data
        from meter, meter_system_info and address.
        :param ground: restrict the sales accounts to a ground or ``None``
        :type ground: sparkmeter.ground.grounddomain.Ground
        :param user: restrict the sales accounts to a user or ``None``
        :type user: sparkmeter.user.userdomain.User
        :returns: a list of attributes that will be used in the latest reading page.
        """
        address_t = get_table_by_name("address")
        customer_t = get_table_by_name("customer")
        meter_t = get_table_by_name("meter")
        meter_config_t = get_table_by_name("meter_config")
        meter_system_info_t = get_table_by_name("meter_system_info")
        ground_t = get_table_by_name("ground")

        columns = [
            address_t.c.city,
            address_t.c.state,
            address_t.c.street1,
            address_t.c.street2,
            meter_t.c.serial.label("serial"),
            customer_t.c.name.label("customer_name"),
            customer_t.c.code.label("customer_code"),
            cls.current_avg,
            cls.current_max,
            cls.current_min,
            cls.energy,
            cls.frequency,
            cls.heartbeat_end,
            cls.id.label("reading_id"),
            cls.state.label("reading_state"),  # Conflicts w/ address.state
            cls.true_power_avg,
            cls.true_power_inst,
            cls.uptime,
            cls.user_power_limit,
            cls.voltage_avg,
            cls.voltage_max,
            cls.voltage_min,
            ground_t.c.name.label("ground_name"),
            ground_t.c.serial.label("ground_serial"),
        ]
        joins = (
            # Readings might not be present if the meter has never received on,
            # so do an left outer join meaning that this can be empty
            meter_system_info_t.outerjoin(cls, meter_system_info_t.c.reading_id == Reading.id)
            .join(meter_t, meter_system_info_t.c.meter_id == meter_t.c.id)
            .outerjoin(customer_t, meter_system_info_t.c.meter_id == customer_t.c.meter_id)
            .join(address_t, meter_t.c.address_id == address_t.c.id)
            .join(meter_config_t, meter_t.c.id == meter_config_t.c.meter_id)
            .join(ground_t, meter_t.c.ground_id == ground_t.c.id)
        )
        wheres = [
            meter_config_t.c.hidden == false(),
        ]

        if ground is not None:
            wheres.append(ground_t.c.id == ground.id)

        if user is not None:
            users_ground_t = get_table_by_name("users_grounds")
            subquery = select(users_ground_t.c.ground_id).where(users_ground_t.c.user_id == user.id)
            wheres.append(ground_t.c.id.in_(subquery))

        query = select(*columns).select_from(joins).where(and_(*wheres)).order_by(meter_t.c.code)
        return query

    def update_kilowatt_hours(self, last_energy, last_energy_datetime):
        """
        Update the kilowatt hours and kilowatt hours period
        based on the last energy measurement and datetime
        """
        # if this is the first summary for this meter,
        # dont bill them a crazy amount
        if last_energy == 0.0:
            kilowatt_hours = 0
            logger.info("skipping the first summary")
        # If the last energy has decreased then something has gone wrong.
        # The meter was either reflashed, is a new meter, or something unexpected has occurred.
        # We need to discard the current kilowatt-hour reading and start the lifetime count again.
        elif last_energy > self.energy:
            kilowatt_hours = 0
            logger.warning(
                "Something has gone wrong with meter %s. The energy value decreased from %f to %f.",
                self.meter,
                last_energy,
                self.energy,
            )
        # Normal reading, usage is delta between current reading and last
        else:
            kilowatt_hours = self.energy - last_energy

        logger.info(
            "energy usage for meter %s: %s (%.2f -> %.2f) kWh",
            self.meter,
            kilowatt_hours,
            last_energy,
            self.energy,
        )
        self.kilowatt_hours = kilowatt_hours

        heartbeat_end_utc = self.heartbeat_end.replace(tzinfo=tzutc())
        last_energy_datetime_utc = last_energy_datetime.replace(tzinfo=tzutc())
        period = (heartbeat_end_utc - last_energy_datetime_utc).total_seconds()
        self.kilowatt_hours_period = period
