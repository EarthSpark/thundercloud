# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Billing related functionality."""
from __future__ import division

import datetime
import logging
from builtins import object

from dateutil.tz import tzlocal, tzutc
from past.utils import old_div

from sparkmeter.config.configparameter import parameters
from sparkmeter.event.eventdomain import Event
from sparkmeter.meter.meterdomain import Meter, MeterConfig
from sparkmeter.reading.readingdomain import Reading
from sparkmeter.tariff.tariffdomain import Tariff

logger = logging.getLogger(__name__)


class CalculateBilling(object):

    """
    Calculate a readings billing data.

    For customers with KWH based tariff plans we change them by energy usage.
    This is calculated by taking the current readings energy, and using
    the delta between max long_energy and the saved previous long_energy as
    the number of watt-hours used in that 5 minute time period.

    This also sets the new long_energy and datetime on the meter.

    It calculates the cost based on the tariff, and deducts the cost
    from the meters account.
    """

    def __init__(self, reading, meter, session):
        """Create a new CalculateBilling object.

        :param reading: reading to process
        :param meter: the meter to process readings for
        :type meter: a Meter
        :param session: an sql session
        """
        if not isinstance(meter, Meter):  # pragma: nocoverage
            raise TypeError("CalculateBilling needs a Meter, not %s" % (
                repr(meter)))
        self.reading = reading
        self.meter = meter
        self.session = session
        # Dates from postgres lacks tzinfo but are in UTC
        self.sr_heartbeat_end_utc = self.reading.heartbeat_end.replace(tzinfo=tzutc())
        self.last_energy_datetime_utc = self.meter.system_info.last_energy_datetime.replace(
            tzinfo=tzutc())

    def update_tariff_cost(self):
        """Update the cost of a reading delta based on a tariff."""
        tariff = self.meter.tariff

        # a) Calculate the base cost for each kWh, flat or block rate
        if tariff.tariff_type == Tariff.TYPE_FLAT:
            rate = self._calculate_flat_rate(tariff)
        elif tariff.tariff_type == Tariff.TYPE_BLOCKRATE:
            rate = self._calculate_block_rate(tariff)
        else:  # pragma: nocoverage
            raise AssertionError(tariff.tariff_type)

        # b) apply TOU period modifier, if any.
        # NOTE: current rules only applies a TOU if both the time between the
        # last energy reading and the actual one is within a TOU period.
        if tariff.tou_enabled and rate > 0.0:
            for tou_period in tariff.get_tous():
                # If the current hr_start..hr_end maps a specific TOU period
                start = self.last_energy_datetime_utc.astimezone(tzlocal())
                end = self.sr_heartbeat_end_utc.astimezone(tzlocal())
                if tou_period.superset_of(start, end):
                    logger.info("Applying TOU period modifier %.4f%% to rate %.4f" % (
                        tou_period.value, rate))
                    modifier = old_div(tou_period.value, 100.0)
                    rate *= modifier
                    self.reading.tou_modifier = modifier
                    break
            else:
                logger.info("Not applying TOU period modifier, %s->%s" % (
                    start, end))

        # Multiply the cost by the number of kWh that was used in the current period
        cost = rate * self.reading.kilowatt_hours
        self.reading.cost = cost
        self.reading.rate = rate
        logger.info("Reading cost is %.4f at a rate of %.4fkWh" % (cost, rate))

    def _calculate_flat_rate(self, tariff):
        rate = tariff.flat_price
        logger.info("Using tariff '%s' with a flat rate of %r" % (
            tariff.name, rate, ))
        # None currently means free, perhaps we want a NOT NULL in the database
        if rate is None:
            rate = 0.0
        return rate

    def _calculate_block_rate(self, tariff):
        # To calculate the blockrate, we need to know how much energy has been consumed
        # between two different points in time.

        # We use the total_cycle_energy value stored in the meter object as our starting point
        start_energy = self.meter.billing.total_cycle_energy

        # The end point of the blockrate calculation is how much energy we have
        # consumed since the beginning of the cycle, including this heartbeat
        end_energy = start_energy + self.reading.kilowatt_hours

        # A reading might cross the blockrate boundaries during one heartbeat
        # so it is needed to calculate the proportionally average rate
        # Example:
        # Let's say we have two blockrates:
        # - Blockrate #1: up until 10 kWh per month is $1/kWh,
        # - Blockrate #2: 10 kWh and above per month is $2/kWh
        # So let's say we have used 20 kWh during this month, then we will calculate the
        # rate in the following way:
        #   - Blockrate #1: 10 kWh * $1/kWh = $10 (first 10 kWh used)
        #   - Blockrate #2: 10 kWh * $2/kWh = $20 (subsequent 10 kWh used)
        #   - Total: $30
        # get_average_block_rate() will return the average: 1.5 (total/usage) which
        # will be multiplied by the actual usage below
        rate = tariff.get_average_block_rate(start_energy, end_energy)
        logger.info("Using tariff '%s' with an average block rate of %.4f (%.4f->%.4f) " % (
            tariff.name, rate, start_energy, end_energy))
        return rate

    def _pay_off_customer_debt(self):
        """Pay off customer debt."""
        # don't overcharge them as they approach payoff
        financing_charge = self.reading.cost * parameters.DEBT_PAYBACK_PERCENT * 1.0 / 100
        for wallet in (self.meter.plan_wallet, self.meter.credit_wallet):
            # clamp the deduction
            deduction = max(
                0.0,
                min(financing_charge, wallet.value, self.meter.debt_wallet.value))
            financing_charge -= deduction
            if deduction > 0:
                logger.info(
                    'Paying a debt of %.4f from %s wallet',
                    deduction,
                    wallet.wallet_type)
                wallet.value -= deduction
                self.meter.debt_wallet.value -= deduction
                self.session.merge(wallet)
                self.session.merge(self.meter.debt_wallet)

    def _update_customer_credit(self):
        """Decrease the meters account credit by the amount used in this minute."""
        logger.info('Paying the reading cost of %.4f, reducing credit %.4f->%.4f' % (
            self.reading.cost,
            self.meter.credit_wallet.value,
            self.meter.credit_wallet.value - self.reading.cost))

        plan_cost = min(self.reading.cost, self.meter.plan_wallet.value)
        self.meter.credit_wallet.value -= (self.reading.cost - plan_cost)
        self.meter.plan_wallet.value -= plan_cost
        self.meter.maybe_convert_negative_balance_to_debt()

        self.session.merge(self.meter.debt_wallet)
        self.session.merge(self.meter.credit_wallet)
        self.session.merge(self.meter.plan_wallet)

    def _maybe_start_new_cycle(self, date):
        """If the previous cycle has ended, start a new periodic billing cycle.

        :param date: datetime for which to check if a new cycle has started
        :returns: `True` if plan has been reset, `False` otherwise
        """
        if not self.meter.is_new_cycle(date):
            return False

        if self.meter.billing.last_cycle_start is not None:
            logger.info("Start a new billing periodic cycle. Last cycle start date was %s",
                        self.meter.billing.last_cycle_start.isoformat())
        else:
            logger.info("Start a new billing periodic cycle. First cycle recorded.")

        # Start a new cycle. The cycle start indicates a reset of total_cycle_energy.
        self.meter.billing.last_cycle_start = date
        logger.info("New cycle start date is %s",
                    self.meter.billing.last_cycle_start.isoformat())

        self.meter.billing.total_cycle_energy = 0
        # Apply changes
        self.session.merge(self.meter)
        self.session.merge(self.meter.plan_wallet)
        return True

    def _maybe_expire_plan(self, date):
        """Reset the plan values if last expiration date is reached.

        :param date: datetime to compare the plan expiration date with
        :returns: `True` if plan has been reset, `False` otherwise
        """
        if not self.meter.tariff.plan_enabled:
            return False

        if (self.meter.billing.is_running_plan
                and date >= self.meter.billing.last_plan_expiration_date):

            self.meter.billing.is_running_plan = False
            self.meter.plan_wallet.value = 0
            return True

        return False

    def _maybe_purchase_new_plan(self):
        """Purchase a new plan with credit wallet if the right conditions apply.

        :returns: `True` if a new plan has been purchased, `False` otherwise
        """
        # If we're using a monthly plan, we might deduct that
        meter = self.meter
        tariff = meter.tariff

        # The Plan Account is filled up automatically on 4 conditions:
        # - the meter's tariff enables a Monthly Plan AND
        # - the meter is not currently running a plan AND
        # - (the meter is mode On OR
        # -  the meter is mode Auto and prepay Credits Account has enough credits to pay for the plan)
        if tariff.plan_enabled and not meter.billing.is_running_plan:
            tariff_cost = tariff.plan_price + tariff.plan_fixed_fee
            if (meter.config.state == MeterConfig.STATE_ON
                or (meter.config.state == MeterConfig.STATE_AUTO
                    and meter.credit_wallet.value >= tariff_cost)):
                logger.info("Filling up plan with %.4f", tariff.plan_price)
                logger.info("Deducting %.4f for cost of plan", tariff.plan_fixed_fee)
                meter.billing.is_running_plan = True
                meter.billing.last_plan_payment_date = self.reading.heartbeat_end
                meter.billing.last_plan_expiration_date = tariff.get_next_cycle_start(
                    self.reading.heartbeat_end)
                meter.credit_wallet.value -= tariff.plan_fixed_fee
                meter.credit_wallet.value -= tariff.plan_price
                meter.plan_wallet.value += tariff.plan_price

                self.session.merge(meter)
                self.session.merge(meter.credit_wallet)
                self.session.merge(meter.plan_wallet)

                return True

        return False

    def _maybe_trigger_low_balance(self):
        meter = self.meter
        tariff = meter.tariff

        # First check if we are currently below the low balance threshold
        if tariff.low_balance_threshold is None:
            return

        credit_plan_total = meter.get_total_balance()
        if not meter.has_low_balance():
            return

        # Secondly, check if we have ever been above the low balance threshold since
        # the last low balance event
        last_event = Event.get_last_event_by(Event.TYPE_CUSTOMER_LOW_BALANCE, meter)
        if last_event is not None:
            max_total_balance = Reading.get_max_total_balance_since(meter, last_event.timestamp)
            if max_total_balance <= tariff.low_balance_threshold:
                return

        logger.info(
            'Customer balance ({balance:.4f}) is below tariff ({tariff:s}) '
            'threshold ({threshold:.4f}), creating an event.'.format(
                balance=credit_plan_total,
                tariff=repr(tariff.name),
                threshold=tariff.low_balance_threshold))
        event = Event.create(Event.TYPE_CUSTOMER_LOW_BALANCE, obj=meter)
        self.session.add(event)

    def _check_balance(self):
        meter = self.meter

        # Don't bother with events/logging if the billing isn't used
        if meter.config.state != MeterConfig.STATE_AUTO:
            return

        self._maybe_trigger_low_balance()

        # FIXME it's strange logic to have this logging here, almost wishful thinking.
        # the actual rule to turn off the meter is managed via property Meter.state_value,
        # called independently. There's no guarantee that this action will result in the
        # meter being turned Off, or that it would not be turned Off in other cases.
        if ((meter.tariff.plan_enabled
            and not meter.billing.is_running_plan)
            or (meter.credit_wallet.value <= 0
                and meter.plan_wallet.value <= 0)):
            logger.info("Turning off meter due to lack of funds.")

    def calculate(self):
        """Do the actual calculations, read data from readings and update the meter."""
        # first of all, we check if we're in a new billing cycle before processing the reading.
        self._maybe_start_new_cycle(self.reading.heartbeat_end - datetime.timedelta(seconds=1))
        # then we take care of the plan. Try to expire the last plan and to purchase a new one.
        # This will ensure that the energy consumed during the current reading
        # will be counted in the plan if a plan can be purchased
        self._maybe_expire_plan(self.reading.heartbeat_end - datetime.timedelta(seconds=1))
        self._maybe_purchase_new_plan()

        self.update_tariff_cost()

        # apply reading cost to meter wallets
        self._update_customer_credit()
        # if the customer has a financing debt, maybe pay some off
        if self.meter.debt_wallet.value > 0:
            self._pay_off_customer_debt()

        # update meter energy values after the reading has been processed
        self.meter.billing.total_cycle_energy += self.reading.kilowatt_hours
        self.session.merge(self.meter)

        # after processing the reading, assess if a new plan period starts just after this reading.
        # if it does, we invalidate the previous plan and try to purchase a new plan
        self._maybe_start_new_cycle(self.reading.heartbeat_end)
        self._maybe_expire_plan(self.reading.heartbeat_end)
        self._maybe_purchase_new_plan()

        # generate low balance event
        self._check_balance()

        self.reading.acct_credit = self.meter.credit_wallet.value
        self.reading.acct_debt = self.meter.debt_wallet.value
        self.reading.acct_plan = self.meter.plan_wallet.value
