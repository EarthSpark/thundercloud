# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
from __future__ import division

import datetime
import logging
from builtins import range, str
from unittest import mock

import pytest
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc
from freezegun import freeze_time
from past.utils import old_div

from sparkmeter.billing import CalculateBilling
from sparkmeter.config.configparameter import parameters
from sparkmeter.controller import process_reading
from sparkmeter.event.eventdomain import Event
from sparkmeter.meter.meterdomain import MeterConfig
from sparkmeter.models import session_scope
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (
    EventFactory,
    MeterFactory,
    OperatorFactory,
    ReadingFactory,
    SalesAccountFactory,
    TariffFactory,
    TransactionSourceFactory,
)
from sparkmeter.transaction.transactiondomain import Transaction, Wallet

logger = logging.getLogger(__name__)


class MockValidator(object):
    """
    Used for validating mock calls by overiding the equality test
    """

    def __init__(self, validator):
        """
        :param validator: predicate function
        """
        self.validator = validator

    def __eq__(self, other):
        return bool(self.validator(other))


class BillingTest(SparkMeterTestCaseBase):
    def _set_heartbeat_time(self, reading, dt, minutes=None):
        if minutes is None:
            minutes = 15
        reading.heartbeat_start = dt + relativedelta(minutes=-minutes)
        reading.heartbeat_end = dt

    def _run_billing(self, reading, meter, session=None):
        if session is None:
            session = self.session
        cb = CalculateBilling(reading, meter, session)
        cb.calculate()
        return cb

    def _add_credits(self, meter, amount):
        logger.info("- Customer pays %s", amount)
        meter.credit_wallet.value += amount

    def _use_energy(self, reading, meter, kwh):
        """Update the reading energy by the supplied amount.

        Stores the previous energy as the last_energy.

        :param reading: The reading that consumes energy.
        :param meter: The meter that is emitting the reading.
        :param kwh: The energy to consume this reading cycle.
        """
        logger.info("- Previous %s; Customer uses %s kWh", reading.energy, kwh)
        meter.system_info.last_energy = reading.energy
        reading.energy += kwh

    def _assert_meter_values(
        self,
        meter,
        reading,
        tariff,
        state,
        state_value,
        is_running_plan,
        acct_credit,
        acct_plan,
        acct_debt,
        total_cycle_energy,
        last_energy,
        last_plan_expiration_date,
        last_plan_payment_date,
        last_cycle_start,
    ):
        assert meter.tariff.name == tariff
        assert meter.config.state == state

        assert meter.billing.is_running_plan == is_running_plan

        assert meter.credit_wallet.value == pytest.approx(acct_credit)
        assert meter.plan_wallet.value == acct_plan
        assert meter.debt_wallet.value == acct_debt
        assert meter.billing.total_cycle_energy == pytest.approx(total_cycle_energy)
        assert meter.state_value == state_value

        assert reading.acct_debt == acct_debt
        assert reading.acct_credit == pytest.approx(acct_credit)
        assert reading.acct_plan == acct_plan

        assert meter.system_info.last_energy == last_energy
        assert meter.billing.last_plan_expiration_date == last_plan_expiration_date
        assert meter.billing.last_plan_payment_date == last_plan_payment_date
        assert meter.billing.last_cycle_start == last_cycle_start

    def test_calculate_billing_data(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        m = MeterFactory(
            system_info__last_energy=1,
            system_info__last_energy_datetime=datetime.datetime(2013, 1, 1, 0, 15, 0),
        )

        sr = ReadingFactory(
            meter=str(m.code),
            kilowatt_hours=None,
            kilowatt_hours_period=None,
            cost=None,
            acct_credit=0,
            acct_debt=0,
            energy=10,
            voltage_avg=121.0,
            heartbeat_start=datetime.datetime(2013, 1, 1, 0, 30, 0),
            heartbeat_end=datetime.datetime(2013, 1, 1, 0, 45, 0),
            uptime=500,
        )
        self.session.commit()

        process_reading(sr, m, self.session)
        self.session.commit()

        self.session.expire(sr)

        assert sr.kilowatt_hours == 9.0
        assert sr.kilowatt_hours_period == 1800
        assert m.system_info.last_energy == 10
        assert m.system_info.last_energy_datetime == datetime.datetime(2013, 1, 1, 0, 45, 0)
        event_create.assert_called_once_with(
            "customer-low-balance", obj=MockValidator(lambda this, that=m: this.id == that.id)
        )

    def test_calculate_billing_data_first_reading(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        tariff = TariffFactory(flat_price=1.0, tariff_type="flat")

        m = MeterFactory(
            system_info__last_energy=0.0,
            system_info__last_energy_datetime=datetime.datetime(2013, 1, 1, 1, 1, 1),
            tariff=tariff,
        )

        sr = ReadingFactory(
            meter=str(m.code),
            kilowatt_hours=None,
            kilowatt_hours_period=None,
            cost=None,
            acct_credit=0,
            acct_debt=0,
            energy=10,
            voltage_avg=121.0,
            heartbeat_start=datetime.datetime(2013, 1, 1, 1, 1, 1),
            heartbeat_end=datetime.datetime(2013, 1, 1, 1, 1, 3),
            uptime=500,
        )
        self.session.commit()

        process_reading(sr, m, self.session)
        self.session.commit()

        self.session.expire(sr)

        # zero values for first reading
        assert sr.kilowatt_hours == 0

        # period is still calculated
        assert sr.kilowatt_hours_period == 2
        # last long energy still gets updated
        assert m.system_info.last_energy == 10
        assert m.system_info.last_energy_datetime == datetime.datetime(2013, 1, 1, 1, 1, 3)
        event_create.assert_called_once_with(
            "customer-low-balance", obj=MockValidator(lambda this, that=m: this.id == that.id)
        )

    def test_calculate_billing_data_after_reset(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        m = MeterFactory(
            system_info__last_energy=100,
            system_info__last_energy_datetime=datetime.datetime(2013, 1, 1, 1, 1, 1),
        )

        sr = ReadingFactory(
            meter=str(m.code),
            kilowatt_hours=None,
            kilowatt_hours_period=None,
            cost=None,
            acct_credit=0,
            acct_debt=0,
            energy=10,
            voltage_avg=121.0,
            heartbeat_start=datetime.datetime(2013, 1, 1, 1, 1, 1),
            heartbeat_end=datetime.datetime(2013, 1, 1, 1, 1, 3),
            uptime=500,
        )
        self.session.commit()

        process_reading(sr, m, self.session)
        self.session.commit()

        self.session.expire(sr)

        # zero values for first reading after reset
        assert sr.kilowatt_hours == 0

        # period is still calculated
        assert sr.kilowatt_hours_period == 2
        # last long energy still gets updated
        assert m.system_info.last_energy == 10
        assert m.system_info.last_energy_datetime == datetime.datetime(2013, 1, 1, 1, 1, 3)
        event_create.assert_called_once_with(
            "customer-low-balance", obj=MockValidator(lambda this, that=m: this.id == that.id)
        )

    @freeze_time("2010-01-01 12:00")
    def test_tariff_with_blockrate_johan(self):
        tariff = TariffFactory(tariff_type=Tariff.TYPE_BLOCKRATE)
        tariff.blockrates = [
            dict(lower=0, upper=10, value=1),
            dict(lower=10, upper=30, value=2),
            dict(lower=30, upper=100, value=3),
            dict(lower=100, upper=0, value=4),
        ]

        # Test block rate when it's the first reading of the month
        meter = MeterFactory(tariff=tariff, system_info__last_energy=0)
        reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 0, 0),
            heartbeat_end=datetime.datetime(2010, 1, 1, 0, 15),
            meter=str(meter.code),
            energy=1,
            kilowatt_hours=1,
        )
        self.session.commit()
        cb = CalculateBilling(reading, meter, self.session)
        cb.update_tariff_cost()
        assert reading.cost == 1

        reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 0, 15),
            heartbeat_end=datetime.datetime(2010, 1, 1, 0, 30),
            meter=str(meter.code),
            energy=0,
        )
        self.session.commit()
        cb = CalculateBilling(reading, meter, self.session)

        # Simple, within the same block rate
        meter.billing.total_cycle_energy = 1
        reading.kilowatt_hours = 2
        cb.update_tariff_cost()
        assert reading.cost == 2

        # Crossing one boundary (8..10, 10..12)
        meter.billing.total_cycle_energy = 8
        reading.kilowatt_hours = 4
        cb.update_tariff_cost()
        assert reading.cost == 6

        # Crossing two boundaries (8..10, 10..30, 30..33)
        meter.billing.total_cycle_energy = 8
        reading.kilowatt_hours = 25
        cb.update_tariff_cost()
        assert reading.cost == 51  # 2*1 + 10*2 + 3*3

        # Against upper limit (200..300)
        meter.billing.total_cycle_energy = 200
        reading.kilowatt_hours = 100
        cb.update_tariff_cost()
        assert reading.cost == 400

    @freeze_time("2010-01-01 12:00")
    def test_tariff_with_blockrate(self):
        # FIXME: This method is probably useless now.
        # Validates same code as test_tariff_with_blockrate_johan
        tariff = TariffFactory(tariff_type=Tariff.TYPE_BLOCKRATE)
        tariff.blockrates = [
            dict(lower=0, upper=5, value=2),
            dict(lower=5, upper=10, value=1),
            dict(lower=10, upper=0, value=0.5),
        ]

        meter = MeterFactory(tariff=tariff)
        # The reading to process, 30 minutes after it was received
        # energy should be discarded for this reading
        reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 11, 15),
            heartbeat_end=datetime.datetime(2010, 1, 1, 11, 30),
            meter=str(meter.code),
            energy=-2000,
        )
        self.session.commit()

        cb = CalculateBilling(reading, meter, self.session)

        # case consumption inside a block
        meter.billing.total_cycle_energy = 5.3
        reading.kilowatt_hours = 0.5
        cb.update_tariff_cost()
        assert reading.cost == 0.5

        # case consumption over several blocks
        meter.billing.total_cycle_energy = 4.2
        reading.kilowatt_hours = 8.5
        cb.update_tariff_cost()
        # 2 * (5 - 4.2) = 1.6
        # 1 * (10 - 5) = 5
        # 0.5 * (8.5 - (10 - 5) - (5 - 4.2)) = 0.5 * 2.7 = 1.35
        # 1.6 + 5 + 1.35 = 7.95
        # FIXME: Use decimal instead of float, but requires major DB surgery
        pytest.approx(reading.cost, 7.95)

    @freeze_time("2010-01-01 12:00")
    def test_tariff_with_blockrate_break_of_month(self):
        # The goal of these tests is to validate that block rate calculations
        # are correct in most situations that may happen at the beginning of
        # a new month
        # Situations to cover:
        # 1. reading ends at 00:00 on the 1st of month
        #   expected: reading counts towards the month that just ended
        # 2. reading bridges over month break (start < 00:00 and end > 00:00)
        #   expected: first reading of month, energy before this reading is processed
        #             is considered start energy for month,
        #             for this reading and later readings in the month
        # 3. reading starts at 00:00 on the 1st of month
        #   expected: first reading of month, energy before this reading is processed
        #             is considered start energy for month,
        #             for this reading and later readings in the month
        # 4. reading starts after 00:00 on the 1st of month, and there's no other reading
        #   that ends > 00:00
        #   expected: first reading of month, energy before this reading is processed
        #             is considered start energy for month,
        #             for this reading and later readings in the month
        # FIXME: let's make sure timezone don't play a role in this - are we sure that
        # total_cycle_energy and block rate calculations are in sync?
        tariff = TariffFactory(tariff_type=Tariff.TYPE_BLOCKRATE)
        tariff.blockrates = [
            dict(lower=0, upper=5, value=2),
            dict(lower=5, upper=10, value=1),
            dict(lower=10, upper=20, value=0.5),
            dict(lower=20, upper=30, value=0.4),
            dict(lower=30, upper=0, value=0.3),
        ]

        # 1. reading ends at 00:00 on the 1st of month
        #   expected: reading counts towards the month that just ended, using the right blockrate
        #   expected: after the reading is processed, a new plan period starts. The meter is turned
        #             Off due to lack of funds
        meter = MeterFactory(tariff=tariff)
        ReadingFactory(
            heartbeat_start=datetime.datetime(2009, 12, 1, 11, 15),
            heartbeat_end=datetime.datetime(2009, 12, 1, 11, 30),
            meter=str(meter.code),
            energy=100,
            kilowatt_hours=20,
        )
        reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2009, 12, 31, 23, 45),
            heartbeat_end=datetime.datetime(2010, 1, 1, 0, 0),
            meter=str(meter.code),
            energy=110,
        )
        self.session.commit()

        # energy since beginning of month: consumption from previous_reading.
        meter.billing.total_cycle_energy = 20
        # theoretical start for last billing cycle
        meter.billing.last_cycle_start = datetime.datetime(2009, 12, 1, 0, 0)
        meter.system_info.last_energy = 100  # energy at end of previous_reading.
        process_reading(reading, meter, self.session)
        assert reading.cost == 10 * 0.4  # 20..30 kWh
        # Plan is reset
        assert meter.billing.total_cycle_energy == 0
        # cycle starts (i.e. cycle counters are reset) at break of month
        assert meter.billing.last_cycle_start == datetime.datetime(2010, 1, 1, 0, 0)

        # 2. reading bridges over month break (start < 00:00 and end > 00:00)
        #   expected: first reading of month, energy before this reading is processed
        #             is considered start energy for month,
        #             for this reading and later readings in the month
        meter = MeterFactory(tariff=tariff)
        first_reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2009, 12, 31, 23, 0),
            heartbeat_end=datetime.datetime(2010, 1, 1, 3, 0),
            meter=str(meter.code),
            energy=100,
            kilowatt_hours=20,
        )
        self.session.commit()

        meter.billing.total_cycle_energy = 50  # arbitrary (previous cycle)
        # theoretical start for last billing cycle
        meter.billing.last_cycle_start = datetime.datetime(2009, 12, 1, 0, 0)
        # consistent with info in reading: energy (100) - consumption (20)
        meter.system_info.last_energy = 80
        process_reading(first_reading, meter, self.session)
        assert first_reading.cost == 5 * 2 + 5 * 1 + 10 * 0.5  # first reading: 0..20 kWh
        # after processed: consumption for first reading
        assert meter.billing.total_cycle_energy == 20
        # cycle starts (i.e. cycle counters are reset) just before reading is processed
        assert meter.billing.last_cycle_start == datetime.datetime(2010, 1, 1, 2, 59, 59)

        # for the second reading, the start energy taken into account to calculate the block rate
        # should be 20 kWh, e.g. the amount that was read in the first reading considered for the month
        reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 3, 30),
            heartbeat_end=datetime.datetime(2010, 1, 1, 3, 45),
            meter=str(meter.code),
            energy=110,  # previous energy (100) + consumption (10)
            kilowatt_hours=10,
        )
        self.session.commit()

        process_reading(reading, meter, self.session)
        assert reading.cost == 10 * 0.4  # 20..30 kWh
        assert meter.billing.total_cycle_energy == 20 + 10
        assert meter.billing.last_cycle_start == datetime.datetime(2010, 1, 1, 2, 59, 59)

        # 3. reading starts at 00:00 on the 1st of month
        #   expected: first reading of month, energy before this reading is processed
        #             is considered start energy for month,
        #             for this reading and later readings in the month
        meter = MeterFactory(tariff=tariff)
        first_reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 0, 0),
            heartbeat_end=datetime.datetime(2010, 1, 1, 0, 15),
            meter=str(meter.code),
            energy=100,
            kilowatt_hours=20,
        )
        self.session.commit()

        meter.billing.total_cycle_energy = 50  # arbitrary (previous cycle)
        meter.billing.last_cycle_start = datetime.datetime(2009, 12, 1, 0, 0)  # arbitrary (previous cycle)
        meter.system_info.last_energy = 80  # consistent with info in reading: energy (100) - consumption (20)
        process_reading(first_reading, meter, self.session)
        assert first_reading.cost == 5 * 2 + 5 * 1 + 10 * 0.5  # first reading: 0..20 kWh
        assert meter.billing.total_cycle_energy == 20  # after processed: consumption for first reading
        # cycle starts (i.e. cycle counters are reset) just before reading is processed
        assert meter.billing.last_cycle_start == datetime.datetime(2010, 1, 1, 0, 14, 59)

        # for the second reading, the start energy taken into account to calculate the block rate
        # should be 20 kWh, e.g. the amount that was read in the first reading considered for the month
        reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 3, 30),
            heartbeat_end=datetime.datetime(2010, 1, 1, 3, 45),
            meter=str(meter.code),
            energy=110,  # previous energy (100) + consumption (10)
            kilowatt_hours=10,
        )
        self.session.commit()

        process_reading(reading, meter, self.session)
        assert reading.cost == 10 * 0.4  # 20..30 kWh
        assert meter.billing.total_cycle_energy == 20 + 10
        assert meter.billing.last_cycle_start == datetime.datetime(2010, 1, 1, 0, 14, 59)

        # 4. reading starts after 00:00 on the 1st of month, and there's no other reading
        #   that ends > 00:00
        #   expected: first reading of month, energy before this reading is processed
        #             is considered start energy for month,
        #             for this reading and later readings in the month
        meter = MeterFactory(tariff=tariff)
        ReadingFactory(
            heartbeat_start=datetime.datetime(2009, 12, 31, 17, 30),
            heartbeat_end=datetime.datetime(2009, 12, 31, 17, 45),
            meter=str(meter.code),
            energy=100,
            kilowatt_hours=20,
        )
        first_reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 0, 30),
            heartbeat_end=datetime.datetime(2010, 1, 1, 0, 45),
            meter=str(meter.code),
            energy=120,
            kilowatt_hours=20,
        )
        self.session.commit()

        meter.billing.total_cycle_energy = 50  # arbitrary (previous cycle)
        meter.billing.last_cycle_start = datetime.datetime(2009, 12, 1, 0, 0)  # arbitrary (previous cycle)
        meter.system_info.last_energy = 100  # from previous_reading - consistent with first_reading (120-20)
        process_reading(first_reading, meter, self.session)
        assert first_reading.cost == 5 * 2 + 5 * 1 + 10 * 0.5  # first reading: 0..20 kWh
        assert meter.billing.total_cycle_energy == 20  # after processed: consumption for first reading
        # cycle starts (i.e. cycle counters are reset) just before reading is processed
        assert meter.billing.last_cycle_start == datetime.datetime(2010, 1, 1, 0, 44, 59)

        # for the second reading, the start energy taken into account to calculate the block rate
        # should be 20 kWh, e.g. the amount that was read in the first reading considered for the month
        reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 3, 30),
            heartbeat_end=datetime.datetime(2010, 1, 1, 3, 45),
            meter=str(meter.code),
            energy=130,  # previous energy (120) + consumption (10)
            kilowatt_hours=10,
        )
        self.session.commit()

        process_reading(reading, meter, self.session)
        assert reading.cost == 10 * 0.4  # 20..30 kWh
        assert meter.billing.total_cycle_energy == 20 + 10
        assert meter.billing.last_cycle_start == datetime.datetime(2010, 1, 1, 0, 44, 59)

    @mock.patch("sparkmeter.billing.tzlocal", tzutc)
    @mock.patch("sparkmeter.tariff.tariffdomain.tzlocal", tzutc)
    def test_flat_tariff_with_tou(self):
        tariff = TariffFactory(tariff_type=Tariff.TYPE_FLAT, flat_price=1, tou_enabled=True)
        tariff.tous = [
            dict(start="18:00", end="20:00", value=120),
            dict(start="23:00", end="05:00", value=80),
        ]

        meter = MeterFactory(tariff=tariff)
        reading = ReadingFactory(meter=str(meter.code))

        # case single heartbeat
        reading.cost = reading.rate = reading.tou_modifier = None
        meter.system_info.last_energy = 0
        reading.kilowatt_hours = 0.5
        meter.system_info.last_energy_datetime = datetime.datetime(2015, 3, 1, 18)
        reading.heartbeat_end = datetime.datetime(2015, 3, 1, 18, 15)
        cb = CalculateBilling(reading, meter, self.session)
        cb.update_tariff_cost()
        assert reading.cost == 0.6
        assert reading.rate == 1.2
        assert reading.tou_modifier == 1.2

        # case multi-heartbeat inside TOU period
        reading.cost = reading.rate = reading.tou_modifier = None
        meter.system_info.last_energy = 0
        reading.kilowatt_hours = 2
        meter.system_info.last_energy_datetime = datetime.datetime(2015, 3, 1, 23, 15)
        reading.heartbeat_end = datetime.datetime(2015, 3, 2, 3, 30)
        cb = CalculateBilling(reading, meter, self.session)
        cb.update_tariff_cost()
        assert reading.cost == 1.6
        assert reading.rate == 0.8
        assert reading.tou_modifier == 0.8

        # case multi-heartbeat outside TOU period
        reading.cost = reading.rate = reading.tou_modifier = None
        meter.system_info.last_energy = 0
        reading.kilowatt_hours = 1.5
        meter.system_info.last_energy_datetime = datetime.datetime(2015, 3, 2, 17, 15)
        reading.heartbeat_end = datetime.datetime(2015, 3, 2, 18, 15)
        cb = CalculateBilling(reading, meter, self.session)
        cb.update_tariff_cost()

        assert reading.cost == 1.5
        assert reading.rate == 1.0
        assert reading.tou_modifier is None

    @mock.patch("sparkmeter.billing.tzlocal", tzutc)
    @mock.patch("sparkmeter.tariff.tariffdomain.tzlocal", tzutc)
    def test_tariff_tou_bug_ps82(self):
        def verify(day1, hour1, minute1, day2, hour2, minute2, tou):
            reading.cost = reading.rate = reading.tou_modifier = None
            meter.system_info.last_energy = 0
            reading.kilowatt_hours = 1
            meter.system_info.last_energy_datetime = datetime.datetime(2015, 1, day1, hour1, minute1)
            reading.heartbeat_end = datetime.datetime(2015, 1, day2, hour2, minute2)
            cb = CalculateBilling(reading, meter, self.session)
            cb.update_tariff_cost()
            if tou:
                assert reading.tou_modifier == old_div(tou["value"], 100.0)
                assert reading.cost == tariff.flat_price * tou["value"] / 100.0
                assert reading.rate == tariff.flat_price * tou["value"] / 100.0
            else:
                assert reading.tou_modifier is None
                assert reading.cost == tariff.flat_price
                assert reading.rate == tariff.flat_price

        tariff = TariffFactory(tariff_type=Tariff.TYPE_FLAT, flat_price=0.47, tou_enabled=True)
        tou1 = dict(start="15:00", end="16:00", value=90)
        tou2 = dict(start="16:00", end="15:00", value=50)
        tariff.tous = [tou1, tou2]

        meter = MeterFactory(tariff=tariff)
        reading = ReadingFactory(meter=str(meter.code))

        # Four cases
        # 1) 15..16
        verify(1, 15, 15, 1, 15, 30, tou1)

        # 2) 16..0
        verify(1, 16, 0, 1, 16, 15, tou2)
        verify(1, 0, 0, 1, 15, 0, tou2)

        # 3) 0..15
        verify(1, 14, 15, 1, 15, 0, tou2)
        verify(1, 23, 45, 2, 0, 0, tou2)

        # 4) midnight crossing
        verify(1, 16, 0, 2, 15, 0, tou2)
        verify(1, 0, 0, 2, 15, 0, tou2)
        verify(1, 16, 0, 2, 0, 0, tou2)
        verify(1, 15, 45, 2, 0, 15, None)

        verify(1, 0, 0, 1, 15, 0, tou2)
        verify(1, 15, 0, 1, 16, 0, tou1)
        verify(1, 16, 0, 2, 0, 0, tou2)
        verify(1, 23, 0, 2, 0, 0, tou2)
        verify(1, 23, 0, 2, 1, 0, tou2)
        verify(1, 23, 0, 2, 16, 0, None)
        verify(1, 23, 0, 2, 15, 0, tou2)
        verify(1, 14, 0, 1, 15, 0, tou2)
        verify(1, 14, 0, 1, 16, 0, None)
        verify(1, 14, 0, 1, 17, 0, None)
        verify(1, 15, 0, 1, 17, 0, None)
        verify(1, 15, 0, 2, 0, 0, None)
        verify(1, 15, 0, 2, 1, 0, None)

    def test_flat_tariff_with_empty_flat_price(self):
        tariff = TariffFactory(flat_price=None)
        meter = MeterFactory(tariff=tariff)
        reading = ReadingFactory(meter=str(meter.code))

        self._run_billing(reading, meter)
        assert reading.rate == 0.0

    def test_pay_off_customer_debt_from_credit(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        parameters.DEBT_PAYBACK_PERCENT = 50.0
        event_create.reset_mock()
        tariff = TariffFactory(tariff_type=Tariff.TYPE_FLAT, flat_price=1)

        meter = MeterFactory(
            tariff=tariff,
            credit_wallet__value=10,
            debt_wallet__value=3,
        )
        reading = ReadingFactory(meter=str(meter.code))

        # Set up a 5kWh usage in this reading
        meter.system_info.last_energy_datetime = datetime.datetime(2015, 3, 1, 18)
        reading.heartbeat_end = datetime.datetime(2015, 3, 1, 18, 15)

        meter.system_info.last_energy = 1
        reading.energy = 6
        reading.kilowatt_hours = 5

        cb = self._run_billing(reading, meter)

        assert meter.credit_wallet.value == 2.5
        assert meter.plan_wallet.value == 0
        assert meter.debt_wallet.value == 0.5
        assert cb.reading.acct_credit == 2.5
        assert cb.reading.acct_plan == 0.0
        assert cb.reading.acct_debt == 0.5
        assert event_create.mock_calls == []

    def test_pay_off_customer_debt_from_plan(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        parameters.DEBT_PAYBACK_PERCENT = 50.0
        event_create.reset_mock()
        tariff = TariffFactory(tariff_type=Tariff.TYPE_FLAT, plan_enabled=True, plan_price=10, flat_price=1)

        meter = MeterFactory(
            tariff=tariff,
            credit_wallet__value=10,
            debt_wallet__value=10,
        )
        reading = ReadingFactory(meter=str(meter.code))

        # Set up a 5kWh usage in this reading
        meter.system_info.last_energy_datetime = datetime.datetime(2015, 3, 1, 18)
        reading.heartbeat_end = datetime.datetime(2015, 3, 1, 18, 15)

        meter.system_info.last_energy = 1
        reading.energy = 6
        reading.kilowatt_hours = 5

        cb = self._run_billing(reading, meter)

        assert meter.credit_wallet.value == 0
        assert meter.plan_wallet.value == 2.5
        assert meter.debt_wallet.value == 7.5
        assert cb.reading.acct_credit == 0
        assert cb.reading.acct_plan == 2.5
        assert cb.reading.acct_debt == 7.5
        assert event_create.mock_calls == []

    def test_pay_off_customer_debt_from_credit_and_plan(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        parameters.DEBT_PAYBACK_PERCENT = 50.0
        event_create.reset_mock()
        tariff = TariffFactory(tariff_type=Tariff.TYPE_FLAT, flat_price=1, plan_enabled=True, plan_price=14)

        meter = MeterFactory(
            tariff=tariff,
            credit_wallet__value=20,
            debt_wallet__value=10,
        )
        reading = ReadingFactory(meter=str(meter.code))

        # Set up a 5kWh usage in this reading
        meter.system_info.last_energy_datetime = datetime.datetime(2015, 3, 1, 18)
        reading.heartbeat_end = datetime.datetime(2015, 3, 1, 18, 15)

        meter.system_info.last_energy = 1
        reading.energy = 11
        reading.kilowatt_hours = 10

        cb = self._run_billing(reading, meter)

        assert reading.kilowatt_hours == 10
        assert meter.billing.is_running_plan
        # original - plan price - debt repayment
        assert meter.credit_wallet.value == 20 - 14 - 1
        # original - reading cost - debt repayment
        assert meter.plan_wallet.value == 14 - 10 - 4
        # original - 50% of reading cost
        assert meter.debt_wallet.value == 10 - 5
        assert cb.reading.acct_credit == 5
        assert cb.reading.acct_plan == 0
        assert cb.reading.acct_debt == 5
        assert event_create.mock_calls == []

    def test_pay_off_customer_debt_from_credit_and_debt_cleared(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()
        parameters.DEBT_PAYBACK_PERCENT = 50.0
        event_create.reset_mock()
        tariff = TariffFactory(tariff_type=Tariff.TYPE_FLAT, flat_price=1, plan_enabled=True, plan_price=13)

        meter = MeterFactory(
            tariff=tariff,
            credit_wallet__value=20,
            debt_wallet__value=4,
        )
        reading = ReadingFactory(meter=str(meter.code))

        # Set up a 5kWh usage in this reading
        meter.system_info.last_energy_datetime = datetime.datetime(2015, 3, 1, 18)
        reading.heartbeat_end = datetime.datetime(2015, 3, 1, 18, 15)

        meter.system_info.last_energy = 1
        reading.energy = 11
        reading.kilowatt_hours = 10

        cb = self._run_billing(reading, meter)

        assert reading.kilowatt_hours == 10
        assert meter.billing.is_running_plan
        # original - plan price - debt repayment
        # repayment is 1 here because the maximum amount owed is 5, but debt
        # is repayed after paying back 4 (debt wallet is 4)
        assert meter.credit_wallet.value == 20 - 13 - 1
        # original - reading cost - debt repayment
        assert meter.plan_wallet.value == 13 - 10 - 3
        # original - 50% of reading cost
        assert meter.debt_wallet.value == 0
        assert cb.reading.acct_credit == 6
        assert cb.reading.acct_plan == 0
        assert cb.reading.acct_debt == 0
        assert event_create.mock_calls == []

    def test_monthly_plan_with_alternate_start_day(self):
        """Validate use cases related to monthly plan not starting on the 1st of the month"""

        tariff_noplan = TariffFactory(tariff_type=Tariff.TYPE_FLAT, name="No_plan_tariff", flat_price=10)
        tariff_planday1 = TariffFactory(
            tariff_type=Tariff.TYPE_FLAT,
            name="Plan_Tariff_Day1",
            flat_price=40,
            plan_price=400,
            cycle_start_day_of_month=1,
            plan_enabled=True,
        )
        tariff_planday5 = TariffFactory(
            tariff_type=Tariff.TYPE_FLAT,
            name="Plan_Tariff_Day5",
            flat_price=20,
            plan_price=600,
            cycle_start_day_of_month=5,
            plan_enabled=True,
        )
        tariff_planday10 = TariffFactory(
            tariff_type=Tariff.TYPE_FLAT,
            name="Plan_Tariff_Day10",
            flat_price=20,
            plan_price=600,
            cycle_start_day_of_month=10,
            plan_enabled=True,
        )

        m = MeterFactory(
            tariff=tariff_planday10, system_info__last_energy=1, config__state=MeterConfig.STATE_ON
        )
        r = ReadingFactory(meter=str(m.code), energy=1, acct_credit=0, acct_plan=0, acct_debt=0)
        self.session.commit()

        # On month 1 day 11, Meter is assigned Tariff starting on day 10. Validate that
        # - plan is purchased at 00:00 on month 1 day 10, with expiration date at 00:00 on month 2 day 10
        # - plan is reset at 00:00 on month 2 day 10
        # - cycle (including total_cycle_energy) is reset at 00:00 on month 2 day 10
        # - new plan is purchased at 00:00 on day 10, with expiration date at 00:00 on month 3 day 10

        # First reading recorded since beginning of cycle
        self._use_energy(r, m, 1)
        self._set_heartbeat_time(r, datetime.datetime(2018, 1, 11, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day10",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-600,
            acct_plan=580,
            acct_debt=0,
            total_cycle_energy=1,
            last_energy=1 + 1,
            last_cycle_start=datetime.datetime(2018, 1, 10, 23, 59, 59),
            last_plan_payment_date=datetime.datetime(2018, 1, 11, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 2, 10, 0, 0),
        )

        # Reading in the middle of the month, plan is being used
        self._use_energy(r, m, 4)
        self._set_heartbeat_time(r, datetime.datetime(2018, 1, 15, 14, 30))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day10",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-600,
            acct_plan=500,
            acct_debt=0,
            total_cycle_energy=1 + 4,
            last_energy=2 + 4,
            last_cycle_start=datetime.datetime(2018, 1, 10, 23, 59, 59),
            last_plan_payment_date=datetime.datetime(2018, 1, 11, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 2, 10, 0, 0),
        )

        # At expiration date, cycle is reset and a new plan is purchased
        self._use_energy(r, m, 10)
        self._set_heartbeat_time(r, datetime.datetime(2018, 2, 10, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day10",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-600 - 600,
            acct_plan=600,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=6 + 10,
            last_cycle_start=datetime.datetime(2018, 2, 10, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 2, 10, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 3, 10, 0, 0),
        )

        # After meter has purchased plan, tariff is changed on month 2 day 11 to now start on day 5.
        # Validate that
        # - previous plan expires on month 3 day 10 00:00
        # - a new plan is then purchased that expires on month 4 day 5 00:00
        # - plan is reset at 00:00 on month 4 day 5
        # - cycle (including total_cycle_energy) is reset at 00:00 on month 4 day 5
        # - new plan is purchased at 00:00 on month 4 day 5, with expiration date at 00:00 on month 5 day 5

        # tariff start day changed (here we change the tariff assigned to the meter given how tests are run.
        # It shouldn't have an impact on behavior)
        m.tariff = tariff_planday5

        # Reading received on day 11
        self._use_energy(r, m, 5)
        self._set_heartbeat_time(r, datetime.datetime(2018, 2, 11, 14, 15))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-1200,
            acct_plan=600 - 5 * 20,
            acct_debt=0,
            total_cycle_energy=5,
            last_energy=16 + 5,
            last_cycle_start=datetime.datetime(2018, 2, 10, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 2, 10, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 3, 10, 0, 0),
        )

        # Reading received during the month
        self._use_energy(r, m, 10)
        self._set_heartbeat_time(r, datetime.datetime(2018, 2, 21, 12, 30))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-1200,
            acct_plan=500 - 10 * 20,
            acct_debt=0,
            total_cycle_energy=15,
            last_energy=21 + 10,
            last_cycle_start=datetime.datetime(2018, 2, 10, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 2, 10, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 3, 10, 0, 0),
        )

        # At expiration date of the previous plan, cycle is reset and a new plan is purchased,
        # expiring on day 5.
        # Interesting use case here for the cycle start: it should start when the previous plan expires.
        self._use_energy(r, m, 5)
        self._set_heartbeat_time(r, datetime.datetime(2018, 3, 10, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-1200 - 600,
            acct_plan=600,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=31 + 5,
            last_cycle_start=datetime.datetime(2018, 3, 10, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 3, 10, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 4, 5, 0, 0),
        )

        # Reading in the middle of the period, plan is being used
        self._use_energy(r, m, 15)
        self._set_heartbeat_time(r, datetime.datetime(2018, 3, 25, 16, 30))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-1800,
            acct_plan=600 - 15 * 20,
            acct_debt=0,
            total_cycle_energy=15,
            last_energy=36 + 15,
            last_cycle_start=datetime.datetime(2018, 3, 10, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 3, 10, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 4, 5, 0, 0),
        )

        # At expiration date, cycle is reset and a new plan is purchased
        self._use_energy(r, m, 10)
        self._set_heartbeat_time(r, datetime.datetime(2018, 4, 5, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-1800 - 600,
            acct_plan=600,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=51 + 10,
            last_cycle_start=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 5, 5, 0, 0),
        )

        # Before month 5 day 5, meter is changed to various tariffs.
        # No plan, plan with day starting on day 1, back to plan with day starting on day 5. Validate that
        # - cycle is not reset during that time (total_cycle_energy keeps going up, start date doesn't change)
        # - plan expiration date stays month 5 day 00:00 all along
        # - cycle (including total_cycle_energy) is reset at 00:00 on month 5 day 5
        # - new plan is purchased at 00:00 on month 5 day 5, with expiration date at 00:00 on month 6 day 5

        # Change tariff to no plan tariff before expiration date
        m.tariff = tariff_noplan

        # Reading in the middle of the period, plan is being used in priority. Cost of energy changes
        # according to new tariff
        self._use_energy(r, m, 15)
        self._set_heartbeat_time(r, datetime.datetime(2018, 4, 15, 16, 45))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2400,
            acct_plan=600 - 15 * 10,
            acct_debt=0,
            total_cycle_energy=15,
            last_energy=61 + 15,
            last_cycle_start=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 5, 5, 0, 0),
        )

        # Change tariff to no plan tariff before expiration date
        m.tariff = tariff_planday1

        # Reading before day 1 (new start day for the current plan), still using the plan
        # but cost of energy changes (according to new tariff)
        self._use_energy(r, m, 4)
        self._set_heartbeat_time(r, datetime.datetime(2018, 4, 25, 6, 15))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2400,
            acct_plan=450 - 4 * 40,
            acct_debt=0,
            total_cycle_energy=15 + 4,
            last_energy=76 + 4,
            last_cycle_start=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 5, 5, 0, 0),
        )

        # Reading after day 1 but before expiration of existing plan, still same behavior
        self._use_energy(r, m, 5)
        self._set_heartbeat_time(r, datetime.datetime(2018, 5, 2, 14, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2400,
            acct_plan=290 - 5 * 40,
            acct_debt=0,
            total_cycle_energy=19 + 5,
            last_energy=80 + 5,
            last_cycle_start=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 5, 5, 0, 0),
        )

        # Change back to initial tariff before expiration date
        m.tariff = tariff_planday5

        # Reading before expiration, still using same behavior. When plan is depleted, using credits
        self._use_energy(r, m, 5)
        self._set_heartbeat_time(r, datetime.datetime(2018, 5, 4, 16, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2400 - (5 * 20 - 90),
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=24 + 5,
            last_energy=85 + 5,
            last_cycle_start=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 4, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 5, 5, 0, 0),
        )

        # At expiration date, a new plan is purchased as if the plan hadn't been changed during the period.
        # Since the plan had expired, the consumption of that reading is deducted from credits.
        self._use_energy(r, m, 1)
        self._set_heartbeat_time(r, datetime.datetime(2018, 5, 5, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2410 - 20 * 1 - 600,
            acct_plan=600,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=90 + 1,
            last_cycle_start=datetime.datetime(2018, 5, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2018, 5, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2018, 6, 5, 0, 0),
        )

    def test_pay_monthly_plan_fixed_fee_state_auto(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()

        tariff = TariffFactory(
            tariff_type=Tariff.TYPE_FLAT,
            name="Plan_Tariff",
            flat_price=20,
            plan_price=500,
            plan_fixed_fee=100,
            plan_enabled=True,
        )

        m = MeterFactory(
            tariff=tariff,
            system_info__last_energy=1,
            config__state=MeterConfig.STATE_AUTO,
            credit_wallet__value=500,
        )
        r = ReadingFactory(meter=str(m.code), energy=1, acct_credit=0, acct_plan=0, acct_debt=0)
        self.session.commit()

        # Can't buy the plan because there isn't enough credit to cover it
        process_reading(r, m, self.session)
        assert m.credit_wallet.value == 500
        assert m.plan_wallet.value == 0
        assert m.debt_wallet.value == 0

        # Buy plan with just enough funds
        m.credit_wallet.value = 600
        process_reading(r, m, self.session)
        assert m.credit_wallet.value == 0
        assert m.plan_wallet.value == 500
        assert m.debt_wallet.value == 0

    def test_pay_monthly_plan(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()

        # The values in this function are based on a spreadsheet created by Arthur,
        # please keep the testing data in sync with the spreadsheet which is located
        # here: https://docs.google.com/spreadsheets/d/1J4hVZKXndHciZ1kNQ6y4vTL3t-i7eroEVMKY32uPOnU
        # The tests are now comprehensive than the spreadsheet, so it should be taken
        # with a grain of salt.
        parameters.ALLOW_NEGATIVE_BALANCE = True

        tariff0 = TariffFactory(tariff_type=Tariff.TYPE_FLAT, name="No_plan_tariff", flat_price=20)
        tariff1 = TariffFactory(
            tariff_type=Tariff.TYPE_FLAT,
            name="Plan_Tariff1",
            flat_price=40,
            plan_price=400,
            plan_enabled=True,
        )
        tariff2 = TariffFactory(
            tariff_type=Tariff.TYPE_FLAT,
            name="Plan_Tariff2",
            flat_price=20,
            plan_price=600,
            plan_enabled=True,
        )

        logger.info("#00")
        m = MeterFactory(tariff=tariff0, system_info__last_energy=1)
        r = ReadingFactory(meter=str(m.code), energy=1, acct_credit=0, acct_plan=0, acct_debt=0)
        self.session.commit()

        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_OFF,
            is_running_plan=False,
            acct_credit=0,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=1,
            last_cycle_start=None,
            last_plan_payment_date=None,
            last_plan_expiration_date=None,
        )

        logger.info("#01")
        self._add_credits(m, 600)

        logger.info("#02")
        self._set_heartbeat_time(r, datetime.datetime(2015, 1, 10, 10, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=False,
            acct_credit=600,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=1,
            last_cycle_start=datetime.datetime(2015, 1, 10, 9, 59, 59),
            last_plan_payment_date=None,
            last_plan_expiration_date=None,
        )

        logger.info("#03")
        self._set_heartbeat_time(r, datetime.datetime(2015, 1, 12, 7, 45))
        self._use_energy(r, m, 5)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=False,
            acct_credit=500,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=5,
            last_energy=1 + 5,
            last_cycle_start=datetime.datetime(2015, 1, 10, 9, 59, 59),
            last_plan_payment_date=None,
            last_plan_expiration_date=None,
        )

        logger.info("#04")
        m.tariff = tariff1

        logger.info("#05")
        self._set_heartbeat_time(r, datetime.datetime(2015, 1, 12, 8, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff1",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=100,
            acct_plan=400,
            acct_debt=0,
            total_cycle_energy=5,
            last_energy=6,
            last_cycle_start=datetime.datetime(2015, 1, 10, 9, 59, 59),
            last_plan_payment_date=datetime.datetime(2015, 1, 12, 8, 0),
            last_plan_expiration_date=datetime.datetime(2015, 2, 1, 0, 0),
        )

        logger.info("#06")
        self._set_heartbeat_time(r, datetime.datetime(2015, 1, 31, 23, 45))
        self._use_energy(r, m, 8)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff1",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=100,
            acct_plan=80,
            acct_debt=0,
            total_cycle_energy=13,
            last_energy=6 + 8,
            last_cycle_start=datetime.datetime(2015, 1, 10, 9, 59, 59),
            last_plan_payment_date=datetime.datetime(2015, 1, 12, 8, 0),
            last_plan_expiration_date=datetime.datetime(2015, 2, 1, 0, 0),
        )
        self._set_heartbeat_time(r, datetime.datetime(2015, 2, 1, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff1",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_OFF,
            is_running_plan=False,
            acct_credit=100,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=14,
            last_cycle_start=datetime.datetime(2015, 2, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 1, 12, 8, 0),
            last_plan_expiration_date=datetime.datetime(2015, 2, 1, 0, 0),
        )

        logger.info("#07")
        self._add_credits(m, 900)
        logger.info("#08")
        self._set_heartbeat_time(r, datetime.datetime(2015, 2, 3, 9, 45))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff1",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=600,
            acct_plan=400,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=14,
            last_cycle_start=datetime.datetime(2015, 2, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 2, 3, 9, 45),
            last_plan_expiration_date=datetime.datetime(2015, 3, 1, 0, 0),
        )

        logger.info("#09")
        self._set_heartbeat_time(r, datetime.datetime(2015, 2, 3, 10, 0))
        self._use_energy(r, m, 4)  # plan 400 -> 400 - 4*40 = 240
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff1",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=600,
            acct_plan=400 - 4 * 40,
            acct_debt=0,
            total_cycle_energy=4,
            last_energy=14 + 4,
            last_cycle_start=datetime.datetime(2015, 2, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 2, 3, 9, 45),
            last_plan_expiration_date=datetime.datetime(2015, 3, 1, 0, 0),
        )

        logger.info("#10")
        self._set_heartbeat_time(r, datetime.datetime(2015, 2, 20, 14, 0))
        self._use_energy(r, m, 7)  # plan 240 -> 0. credit 600 -> 600 - 40 = 560
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff1",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=600 - 40,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=11,
            last_energy=18 + 7,
            last_cycle_start=datetime.datetime(2015, 2, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 2, 3, 9, 45),
            last_plan_expiration_date=datetime.datetime(2015, 3, 1, 0, 0),
        )

        logger.info("#11")
        self._set_heartbeat_time(r, datetime.datetime(2015, 2, 27, 8, 0))
        self._use_energy(r, m, 10)  # credit 560 -> 560 - 10*40 = 160
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff1",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=160,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=21,
            last_energy=25 + 10,
            last_cycle_start=datetime.datetime(2015, 2, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 2, 3, 9, 45),
            last_plan_expiration_date=datetime.datetime(2015, 3, 1, 0, 0),
        )

        logger.info("#12")
        m.tariff = tariff2

        logger.info("#13")
        self._add_credits(m, 600)  # credit 160 -> 760

        logger.info("#14")
        self._set_heartbeat_time(r, datetime.datetime(2015, 2, 27, 8, 15))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=760,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=21,
            last_energy=35,
            last_cycle_start=datetime.datetime(2015, 2, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 2, 3, 9, 45),
            last_plan_expiration_date=datetime.datetime(2015, 3, 1, 0, 0),
        )

        logger.info("#15")
        self._set_heartbeat_time(r, datetime.datetime(2015, 3, 1, 0, 15))
        self._use_energy(r, m, 5)  # buying plan: credit 760 -> 160.
        # Paying consumption with plan: 0 -> 600 -> 600 - 5*20 = 500
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=160,
            acct_plan=500,
            acct_debt=0,
            total_cycle_energy=5,
            last_energy=35 + 5,
            last_cycle_start=datetime.datetime(2015, 3, 1, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2015, 3, 1, 0, 15),
            last_plan_expiration_date=datetime.datetime(2015, 4, 1, 0, 0),
        )

        logger.info("#16")
        self._set_heartbeat_time(r, datetime.datetime(2015, 3, 15, 14, 0))
        self._use_energy(r, m, 10)  # plan 500 -> 500 - 10*20 = 300
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=160,
            acct_plan=300,
            acct_debt=0,
            total_cycle_energy=15,
            last_energy=40 + 10,
            last_cycle_start=datetime.datetime(2015, 3, 1, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2015, 3, 1, 0, 15),
            last_plan_expiration_date=datetime.datetime(2015, 4, 1, 0, 0),
        )

        logger.info("#17")
        m.config.state = MeterConfig.STATE_OFF
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_OFF,
            state_value=MeterConfig.STATE_OFF,
            is_running_plan=True,
            acct_credit=160,
            acct_plan=300,
            acct_debt=0,
            total_cycle_energy=15,
            last_energy=50,
            last_cycle_start=datetime.datetime(2015, 3, 1, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2015, 3, 1, 0, 15),
            last_plan_expiration_date=datetime.datetime(2015, 4, 1, 0, 0),
        )

        logger.info("#18")
        m.config.state = MeterConfig.STATE_AUTO
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=160,
            acct_plan=300,
            acct_debt=0,
            total_cycle_energy=15,
            last_energy=50,
            last_cycle_start=datetime.datetime(2015, 3, 1, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2015, 3, 1, 0, 15),
            last_plan_expiration_date=datetime.datetime(2015, 4, 1, 0, 0),
        )

        logger.info("#19")
        self._set_heartbeat_time(r, datetime.datetime(2015, 3, 16, 16, 15))
        self._use_energy(r, m, 0.1)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=160,
            acct_plan=298,
            acct_debt=0,
            total_cycle_energy=15.1,
            last_energy=50 + 0.1,
            last_cycle_start=datetime.datetime(2015, 3, 1, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2015, 3, 1, 0, 15),
            last_plan_expiration_date=datetime.datetime(2015, 4, 1, 0, 0),
        )

        logger.info("#20")
        self._set_heartbeat_time(r, datetime.datetime(2015, 3, 22, 14, 30))
        self._use_energy(r, m, 10)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=160,
            acct_plan=98,
            acct_debt=0,
            total_cycle_energy=25.1,
            last_energy=50.1 + 10,
            last_cycle_start=datetime.datetime(2015, 3, 1, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2015, 3, 1, 0, 15),
            last_plan_expiration_date=datetime.datetime(2015, 4, 1, 0, 0),
        )

        logger.info("#21")
        m.config.state = MeterConfig.STATE_ON
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=160,
            acct_plan=98,
            acct_debt=0,
            total_cycle_energy=25.1,
            last_energy=60.1,
            last_cycle_start=datetime.datetime(2015, 3, 1, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2015, 3, 1, 0, 15),
            last_plan_expiration_date=datetime.datetime(2015, 4, 1, 0, 0),
        )

        logger.info("#22")
        self._set_heartbeat_time(r, datetime.datetime(2015, 3, 27, 16, 0))
        self._use_energy(r, m, 15)  # plan 98 -> 0; credit 160 - 15*20 + 98 = -42
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-42,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=40.1,
            last_energy=60.1 + 15,
            last_cycle_start=datetime.datetime(2015, 3, 1, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2015, 3, 1, 0, 15),
            last_plan_expiration_date=datetime.datetime(2015, 4, 1, 0, 0),
        )

        logger.info("#23")
        self._set_heartbeat_time(r, datetime.datetime(2015, 4, 1, 0, 0))
        self._use_energy(r, m, 5)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-742,
            acct_plan=600,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=75.1 + 5,
            last_cycle_start=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#24")
        self._set_heartbeat_time(r, datetime.datetime(2015, 4, 3, 13, 0))
        self._use_energy(r, m, 5)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-742,
            acct_plan=500,
            acct_debt=0,
            total_cycle_energy=5,
            last_energy=80.1 + 5,
            last_cycle_start=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#25")
        self._add_credits(m, 900)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=158,
            acct_plan=500,
            acct_debt=0,
            total_cycle_energy=5,
            last_energy=85.1,
            last_cycle_start=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#26")
        m.config.state = MeterConfig.STATE_AUTO
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=158,
            acct_plan=500,
            acct_debt=0,
            total_cycle_energy=5,
            last_energy=85.1,
            last_cycle_start=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#27")
        self._set_heartbeat_time(r, datetime.datetime(2015, 4, 27, 16, 0))
        self._use_energy(r, m, 20)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=158,
            acct_plan=100,
            acct_debt=0,
            total_cycle_energy=25,
            last_energy=85.1 + 20,
            last_cycle_start=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#28")
        m.config.state = MeterConfig.STATE_OFF
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_OFF,
            state_value=MeterConfig.STATE_OFF,
            is_running_plan=True,
            acct_credit=158,
            acct_plan=100,
            acct_debt=0,
            total_cycle_energy=25,
            last_energy=105.1,
            last_cycle_start=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#29")
        self._set_heartbeat_time(r, datetime.datetime(2015, 5, 1, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_OFF,
            state_value=MeterConfig.STATE_OFF,
            is_running_plan=False,
            acct_credit=158,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=105.1,
            last_cycle_start=datetime.datetime(2015, 5, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )
        self._set_heartbeat_time(r, datetime.datetime(2015, 5, 1, 0, 15))

        logger.info("#29A")
        self._add_credits(m, 1000)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_OFF,
            state_value=MeterConfig.STATE_OFF,
            is_running_plan=False,
            acct_credit=1158,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=105.1,
            last_cycle_start=datetime.datetime(2015, 5, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#30")
        self._set_heartbeat_time(r, datetime.datetime(2015, 5, 3, 16, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff2",
            state=MeterConfig.STATE_OFF,
            state_value=MeterConfig.STATE_OFF,
            is_running_plan=False,
            acct_credit=1158,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=105.1,
            last_cycle_start=datetime.datetime(2015, 5, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#31")
        m.tariff = tariff0
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_OFF,
            state_value=MeterConfig.STATE_OFF,
            is_running_plan=False,
            acct_credit=1158,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=105.1,
            last_cycle_start=datetime.datetime(2015, 5, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#32")
        m.config.state = MeterConfig.STATE_AUTO
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=False,
            acct_credit=1158,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=105.1,
            last_cycle_start=datetime.datetime(2015, 5, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#33")
        self._set_heartbeat_time(r, datetime.datetime(2015, 5, 3, 16, 15))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=False,
            acct_credit=1158,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=105.1,
            last_cycle_start=datetime.datetime(2015, 5, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#34")
        self._set_heartbeat_time(r, datetime.datetime(2015, 6, 1, 0, 0))
        self._use_energy(r, m, 55)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=False,
            acct_credit=58,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=105.1 + 55,
            last_cycle_start=datetime.datetime(2015, 6, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#35")
        self._set_heartbeat_time(r, datetime.datetime(2015, 6, 3, 17, 0))
        self._use_energy(r, m, 3)
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_AUTO,
            state_value=MeterConfig.STATE_OFF,
            is_running_plan=False,
            acct_credit=-2,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=3,
            last_energy=160.1 + 3,
            last_cycle_start=datetime.datetime(2015, 6, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )

        logger.info("#36")
        m.config.state = MeterConfig.STATE_ON
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=False,
            acct_credit=-2,
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=3,
            last_energy=163.1,
            last_cycle_start=datetime.datetime(2015, 6, 1, 0, 0),
            last_plan_payment_date=datetime.datetime(2015, 4, 1, 0, 0),
            last_plan_expiration_date=datetime.datetime(2015, 5, 1, 0, 0),
        )
        assert event_create.mock_calls == [
            mock.call("customer-low-balance", obj=mock.ANY),
        ]

    def test_meter_in_a_different_session(self, mocker):
        event_create = mocker.patch("sparkmeter.event.eventdomain.Event.create")
        event_create.return_value = EventFactory()

        meter = MeterFactory(code=1)
        self.session.commit()
        with session_scope() as session:
            reading = ReadingFactory.build(_meter=None, meter=1)
            session.add(reading)
            session.commit()
            process_reading(reading, meter, session)

        event_create.assert_called_once_with(
            "customer-low-balance", obj=MockValidator(lambda this, that=meter: this.id == that.id)
        )

    @mock.patch("sparkmeter.event.eventdomain.Event.create")
    def test_low_balance_event(self, create, operator_role):
        def create_event(event_type, obj=None):
            e = Event(event_type=event_type, timestamp=datetime.datetime.now())
            if obj:
                e.object = obj
                e.ground_id = obj.ground_id
            return e

        create.side_effect = create_event

        account = SalesAccountFactory(credit_wallet__value=1000, debt_wallet__value=0)
        self.session.commit()
        user = OperatorFactory(accounts=[account], roles=[operator_role], grounds=[account.ground])
        source = TransactionSourceFactory()
        m = MeterFactory(
            system_info__last_energy=1,
            system_info__last_energy_datetime=datetime.datetime(2013, 1, 1, 0, 15, 0),
            credit_wallet__value=10,
            debt_wallet__value=0,
            config__state=MeterConfig.STATE_AUTO,
            billing__tariff__flat_price=1,
            billing__tariff__low_balance_threshold=5,
        )
        self.session.commit()

        # This is placed before the last
        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=m,
            amount=20,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=m.ground,
            session=self.session,
        )
        # Last transaction
        transaction = Transaction.create_transactions(
            from_object=account,
            to_object=m,
            amount=40,
            wallet_type=Wallet.TYPE_CREDIT,
            user=user,
            source=source,
            ground=m.ground,
            session=self.session,
        )
        transaction.state = Transaction.STATE_PROCESSED
        self.session.commit()

        self.total_energy = 1
        self.last_heartbeat = datetime.datetime(2013, 1, 1, 0, 45, 0)

        def add_credit(credit, acct_credit=0):
            m.credit_wallet.value += credit

        def consume(energy):
            self.last_heartbeat += datetime.timedelta(minutes=15)
            self.total_energy += energy
            sr = ReadingFactory(
                meter=str(m.code),
                kilowatt_hours=None,
                kilowatt_hours_period=None,
                cost=None,
                energy=self.total_energy,
                voltage_avg=121.0,
                heartbeat_start=self.last_heartbeat - datetime.timedelta(minutes=15),
                heartbeat_end=self.last_heartbeat,
                uptime=500,
            )
            self.session.commit()

            with freeze_time(self.last_heartbeat):
                process_reading(sr, m, self.session)
                self.session.commit()
                logger.info(
                    "consumed: %f, "
                    "total_energy: %f, "
                    "reading.heartbeat_end: %s "
                    "reading.kilowatt_hours: %f "
                    "reading.acct_credit: %f",
                    energy,
                    self.total_energy,
                    sr.heartbeat_end,
                    sr.kilowatt_hours,
                    sr.acct_credit,
                )
            return sr

        def verify(sr, acct_credit):
            assert sr.acct_credit == acct_credit

        def n_events(n):
            assert Event.query.filter_by(event_type=Event.TYPE_CUSTOMER_LOW_BALANCE).count() == n

        # Fairly comprehensive test to make sure that we do not trigger too many
        # low balance events.
        # tariff threshold = 5
        # price per kWh = 1

        # Pre-check, make sure we have no events
        n_events(0)

        # Consume 10->10 credit, no new events, above threshold (10 > 5)
        sr = consume(0)
        assert sr.acct_credit == 10
        n_events(0)

        # Consume 10->9 credit, no new events, above threshold (9 > 5)
        sr = consume(1)
        assert sr.acct_credit == 9.0
        n_events(0)

        # Consume 9->5 credit, 1 event, on threshold (5 == 5)
        sr = consume(4)
        assert sr.acct_credit == 5
        n_events(1)

        # Consume 5->4->3->2->1->0 credit, no new events, below threshold (1..5 <= 5)
        for i in range(5):
            consume(1)
            n_events(1)

        # Out of credits, add 10
        add_credit(10)

        # Consume 10->9 credit, no new events, above threshold (9 > 5)
        sr = consume(1)
        assert sr.acct_credit == 9
        n_events(1)

        # Consume 9->5 credit, 1 new events, on threshold (5 == 5)
        sr = consume(4)
        assert sr.acct_credit == 5
        n_events(2)

    @freeze_time("2010-01-01 12:00")
    def test_tariff_blockrates_as_string_values(self):
        # See also SW-345
        tariff = TariffFactory(tariff_type=Tariff.TYPE_BLOCKRATE)
        tariff.blockrates = [
            dict(lower="0", upper="10", value="1.5"),
            dict(lower="10", upper="30", value="2.5"),
            dict(lower="30", upper="100", value="3.5"),
            dict(lower="100", upper="0", value="4.5"),
        ]

        # Test block rate when it's the first reading of the month
        meter = MeterFactory(tariff=tariff, system_info__last_energy=0)
        reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 0, 0),
            heartbeat_end=datetime.datetime(2010, 1, 1, 0, 15),
            meter=str(meter.code),
            energy=1,
            kilowatt_hours=1,
        )
        self.session.commit()
        cb = CalculateBilling(reading, meter, self.session)
        cb.update_tariff_cost()
        assert reading.cost == 1.5

        # This reading comes after the first reading of the month. 1 kWh has been consumed
        reading = ReadingFactory(
            heartbeat_start=datetime.datetime(2010, 1, 1, 0, 15),
            heartbeat_end=datetime.datetime(2010, 1, 1, 0, 30),
            meter=str(meter.code),
            energy=0,
        )
        self.session.commit()
        cb = CalculateBilling(reading, meter, self.session)

        # Simple, within the same block rate (1..3)
        meter.billing.total_cycle_energy = 1
        reading.kilowatt_hours = 2
        cb.update_tariff_cost()
        assert reading.cost == 2 * 1.5

        # Crossing one boundary (8..10, 10..12)
        meter.billing.total_cycle_energy = 8
        reading.kilowatt_hours = 4
        cb.update_tariff_cost()
        assert reading.cost == 2 * 1.5 + 2 * 2.5

        # Crossing two boundaries (8..10, 10..30, 30..33)
        meter.billing.total_cycle_energy = 8
        reading.kilowatt_hours = 25
        cb.update_tariff_cost()
        assert reading.cost == 2 * 1.5 + 20 * 2.5 + 3 * 3.5

        # Against upper limit (200..300)
        meter.billing.total_cycle_energy = 200
        reading.kilowatt_hours = 100
        cb.update_tariff_cost()
        assert reading.cost == 100 * 4.5

    def test_daily_plan(self):
        """Validate use cases related to the daily plan."""

        tariff_noplan = TariffFactory(tariff_type=Tariff.TYPE_FLAT, name="No_plan_tariff", flat_price=10)
        tariff_daily = TariffFactory(
            tariff_type=Tariff.TYPE_FLAT,
            name="Plan_Tariff_Day1Flat40",
            flat_price=40,
            plan_price=400,
            cycle_start_day_of_month=1,
            plan_enabled=True,
            plan_duration_unit=Tariff.PLAN_DURATION_UNIT_DAY,
        )
        tariff_monthly = TariffFactory(
            tariff_type=Tariff.TYPE_FLAT,
            name="Plan_Tariff_Day5",
            flat_price=20,
            plan_price=600,
            cycle_start_day_of_month=5,
            plan_enabled=True,
        )

        m = MeterFactory(tariff=tariff_daily, system_info__last_energy=1, config__state=MeterConfig.STATE_ON)
        r = ReadingFactory(meter=str(m.code), energy=1, acct_credit=0, acct_plan=0, acct_debt=0)
        self.session.commit()

        # On day 13, Meter is assigned a daily tariff. Validate that
        # - plan is purchased at 00:15 on day 13, with expiration date at 00:15 on day 14
        # - plan is reset at 00:15 on day 14
        # - new plan is purchased at 00:15 on day 14, with expiration date at 00:15 on day 15
        # - cycle (including total_cycle_energy) is reset at 00:00 on day 1

        # First reading recorded since beginning of cycle
        self._use_energy(r, m, 1)
        self._set_heartbeat_time(r, datetime.datetime(2020, 1, 13, 0, 15))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1Flat40",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-400,
            acct_plan=360,
            acct_debt=0,
            total_cycle_energy=1,
            last_energy=1 + 1,
            last_cycle_start=datetime.datetime(2020, 1, 13, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2020, 1, 13, 0, 15),
            last_plan_expiration_date=datetime.datetime(2020, 1, 14, 0, 15),
        )

        # Reading in the middle of the day, plan is being used
        self._use_energy(r, m, 4)
        self._set_heartbeat_time(r, datetime.datetime(2020, 1, 13, 12, 30))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1Flat40",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-400,
            acct_plan=200,
            acct_debt=0,
            total_cycle_energy=1 + 4,
            last_energy=2 + 4,
            last_cycle_start=datetime.datetime(2020, 1, 13, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2020, 1, 13, 0, 15),
            last_plan_expiration_date=datetime.datetime(2020, 1, 14, 0, 15),
        )

        # At expiration date, plan expires and a new plan is purchased
        self._use_energy(r, m, 10)
        self._set_heartbeat_time(r, datetime.datetime(2020, 1, 14, 0, 15))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1Flat40",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-400 - 600,
            acct_plan=400,
            acct_debt=0,
            total_cycle_energy=5 + 10,
            last_energy=6 + 10,
            last_cycle_start=datetime.datetime(2020, 1, 13, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2020, 1, 14, 0, 15),
            last_plan_expiration_date=datetime.datetime(2020, 1, 15, 0, 15),
        )

        # Meters on a daily plan have their plans expire 24 hours after the plan is purchased. This means
        #  that plans are not bound to day boundaries (i.e., midnight).
        self._use_energy(r, m, 3)
        self._set_heartbeat_time(r, datetime.datetime(2020, 1, 15, 12, 30))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1Flat40",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-1000 - 400,
            acct_plan=400 - (3 * 40),
            acct_debt=0,
            total_cycle_energy=15 + 3,
            last_energy=16 + 3,
            last_cycle_start=datetime.datetime(2020, 1, 13, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2020, 1, 15, 12, 30),
            last_plan_expiration_date=datetime.datetime(2020, 1, 16, 12, 30),
        )

        # After a meter has purchased a daily plan, tariff is changed to a monthly plan
        # Validate that
        # - the previous plan expires on month 1 day 15 00:00
        # - a new plan is then purchased that expires on month 2 day 5 00:00
        # - plan is reset at 00:00 on month 2 day 6
        # - cycle (including total_cycle_energy) is reset at 00:00 on month 2 day 1
        # - new plan is purchased at 00:00 on month 2 day 5, with expiration date at 00:00 on month 3 day 5

        # tariff start day changed (here we change the tariff assigned to the meter given how tests are run.
        # It shouldn't have an impact on behavior)
        m.tariff = tariff_monthly

        # Reading received on day 17
        self._use_energy(r, m, 5)
        self._set_heartbeat_time(r, datetime.datetime(2020, 1, 17, 14, 15))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2000,
            acct_plan=600 - 5 * 20,
            acct_debt=0,
            total_cycle_energy=18 + 5,
            last_energy=19 + 5,
            last_cycle_start=datetime.datetime(2020, 1, 13, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2020, 1, 17, 14, 15),
            last_plan_expiration_date=datetime.datetime(2020, 2, 5, 0, 0),
        )

        # Reading received during the month
        self._use_energy(r, m, 10)
        self._set_heartbeat_time(r, datetime.datetime(2020, 1, 21, 12, 30))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2000,
            acct_plan=500 - 10 * 20,
            acct_debt=0,
            total_cycle_energy=23 + 10,
            last_energy=24 + 10,
            last_cycle_start=datetime.datetime(2020, 1, 13, 0, 14, 59),
            last_plan_payment_date=datetime.datetime(2020, 1, 17, 14, 15),
            last_plan_expiration_date=datetime.datetime(2020, 2, 5, 0, 0),
        )

        # At expiration date of the previous plan, cycle is reset and a new plan is purchased,
        # expiring on day 5.
        # Interesting use case here for the cycle start: it should start when the previous plan expires.
        self._use_energy(r, m, 5)
        self._set_heartbeat_time(r, datetime.datetime(2020, 2, 5, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2000 - 600,
            acct_plan=600,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=34 + 5,
            last_cycle_start=datetime.datetime(2020, 2, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2020, 2, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2020, 3, 5, 0, 0),
        )

        # Reading in the middle of the period, plan is being used
        self._use_energy(r, m, 15)
        self._set_heartbeat_time(r, datetime.datetime(2020, 2, 25, 16, 30))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2600,
            acct_plan=600 - 15 * 20,
            acct_debt=0,
            total_cycle_energy=15,
            last_energy=39 + 15,
            last_cycle_start=datetime.datetime(2020, 2, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2020, 2, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2020, 3, 5, 0, 0),
        )

        # At expiration date, cycle is reset and a new plan is purchased
        self._use_energy(r, m, 10)
        self._set_heartbeat_time(r, datetime.datetime(2020, 3, 5, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day5",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-2600 - 600,
            acct_plan=600,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=54 + 10,
            last_cycle_start=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2020, 4, 5, 0, 0),
        )

        # Before month 4 day 5, meter is changed to various tariffs.
        # No plan, daily plan, back to plan with day starting on day 5. Validate that
        # - cycle is not reset during that time (total_cycle_energy keeps going up, start date doesn't change)
        # - plan expiration date stays month 5 day 00:00 all along
        # - cycle (including total_cycle_energy) is reset at 00:00 on month 5 day 5
        # - new plan is purchased at 00:00 on month 5 day 5, with expiration date at 00:00 on month 6 day 5

        # Change tariff to no plan tariff before expiration date
        m.tariff = tariff_noplan

        # Reading in the middle of the period, plan is being used in priority. Cost of energy changes
        # according to new tariff
        self._use_energy(r, m, 15)
        self._set_heartbeat_time(r, datetime.datetime(2020, 3, 15, 16, 45))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="No_plan_tariff",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-3200,
            acct_plan=600 - 15 * 10,
            acct_debt=0,
            total_cycle_energy=15,
            last_energy=64 + 15,
            last_cycle_start=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2020, 4, 5, 0, 0),
        )

        # Change tariff to daily tariff before expiration date
        m.tariff = tariff_daily

        # Reading still using the main plan but cost of energy changes (according to new tariff)
        self._use_energy(r, m, 4)
        self._set_heartbeat_time(r, datetime.datetime(2020, 3, 25, 6, 15))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1Flat40",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-3200,
            acct_plan=450 - 4 * 40,
            acct_debt=0,
            total_cycle_energy=15 + 4,
            last_energy=79 + 4,
            last_cycle_start=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2020, 4, 5, 0, 0),
        )

        # Reading after next day but before expiration of existing plan, still same behavior
        self._use_energy(r, m, 5)
        self._set_heartbeat_time(r, datetime.datetime(2020, 3, 26, 14, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1Flat40",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-3200,
            acct_plan=290 - 5 * 40,
            acct_debt=0,
            total_cycle_energy=19 + 5,
            last_energy=83 + 5,
            last_cycle_start=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2020, 4, 5, 0, 0),
        )

        # Change back to initial daily tariff before expiration date

        # Reading before expiration, still using same behavior. When plan is depleted, using credits
        self._use_energy(r, m, 5)
        self._set_heartbeat_time(r, datetime.datetime(2020, 4, 4, 16, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1Flat40",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            # The '90' reflects the balance of the plan wallet that is zeroed before
            # credit is applied
            acct_credit=-3200 - (5 * 40 - 90),
            acct_plan=0,
            acct_debt=0,
            total_cycle_energy=24 + 5,
            last_energy=88 + 5,
            last_cycle_start=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2020, 3, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2020, 4, 5, 0, 0),
        )

        # At expiration date, a new plan is purchased as if the plan hadn't been changed during the period.
        # Since the plan has expired, the consumption of that reading is deducted from credits.
        self._use_energy(r, m, 1)
        self._set_heartbeat_time(r, datetime.datetime(2020, 4, 5, 0, 0))
        process_reading(r, m, self.session)
        self._assert_meter_values(
            meter=m,
            reading=r,
            tariff="Plan_Tariff_Day1Flat40",
            state=MeterConfig.STATE_ON,
            state_value=MeterConfig.STATE_ON,
            is_running_plan=True,
            acct_credit=-3310 - (40 * 1) - 400,
            acct_plan=400,
            acct_debt=0,
            total_cycle_energy=0,
            last_energy=93 + 1,
            last_cycle_start=datetime.datetime(2020, 4, 5, 0, 0),
            last_plan_payment_date=datetime.datetime(2020, 4, 5, 0, 0),
            last_plan_expiration_date=datetime.datetime(2020, 4, 6, 0, 0),
        )
