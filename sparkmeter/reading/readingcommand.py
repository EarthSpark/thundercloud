# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Reading manage commands.py."""
from __future__ import division

import datetime
import logging
import random
import time
from builtins import object, range, str

import click
from flask.cli import with_appcontext
from past.utils import old_div
from zope.component import getUtility

from sparkmeter.interface import IApplication

logger = logging.getLogger(__name__)

reading = click.Group('reading', help='Reading management commands.')


class DisableLogger(object):
    def __enter__(self):
        logging.disable(logging.CRITICAL)

    def __exit__(self, a, b, c):
        logging.disable(logging.NOTSET)


class ReadingGenerator(object):
    def __init__(self, energy_watts, cycle_length):
        self.energy_watts = energy_watts
        self.cycle_length = cycle_length

    def run_cycle_loop(self):
        from dateutil.relativedelta import relativedelta

        from sparkmeter.meter.meterdomain import Meter
        from sparkmeter.models import session_scope

        with session_scope():
            all_meters = Meter.get_all()
        now = datetime.datetime.utcnow()
        heartbeat_start = now.replace(
            microsecond=0,
            second=0,
            minute=(old_div(now.minute, self.cycle_length)) * self.cycle_length)

        while True:
            heartbeat_end = heartbeat_start + relativedelta(minutes=self.cycle_length)
            logging.info('* heartbeat period %s TO %s' % (heartbeat_start,
                                                          heartbeat_end))
            meters = self.get_meters(all_meters)
            self.heartbeat(meters,
                           start=heartbeat_start,
                           end=heartbeat_end)
            heartbeat_start = heartbeat_end

    def create_for_meter(self, serial):
        from sparkmeter.meter.meterdomain import Meter
        from sparkmeter.models import session_scope
        with session_scope():
            meter = Meter.get_by_serial(serial)
            if meter is None:
                logger.error("Meter does not exist: %s" % (serial, ))
                raise SystemExit(1)
            self.create_reading(meter)

    def heartbeat(self, meters, start, end):
        from sparkmeter.models import session_scope
        interval = old_div((end - start).seconds, 60)
        for i in range(interval):
            t = time.time()
            n_readings = 0
            if i < len(meters):
                with session_scope(), DisableLogger():
                    for meter in meters[i]:
                        n_readings += self.create_reading(
                            meter,
                            heartbeat_length=interval,
                            heartbeat_start=start,
                            heartbeat_end=end)

            delta = time.time() - t
            sleep_period = int(old_div(float(self.cycle_length * 60), interval))
            logger.info('Added %d readings in %ds (sleeping %ds)' % (
                n_readings,
                delta,
                sleep_period - delta))
            time.sleep(sleep_period)

    def create_reading(self, meter, heartbeat_length=15,
                       heartbeat_start=None,
                       heartbeat_end=None):
        """
        Create a new reading.

        :param meter: meter to create reading for
        :type meter: Meter
        :param heartbeat_length: length of the heart beat (the period), in minutes
        :type heartbeat_length: int
        :param heartbeat_start: beginning of the heartbeat
        :type heartbeat_start: datetime.datetime
        :param heartbeat_end: end of the heartbeat
        :type heartbeat_end: datetime.datetime
        :return:
        """
        from dateutil.relativedelta import relativedelta

        from sparkmeter.controller import add_reading
        voltages = [random.uniform(118.0, 122.0) for _ in range(10)]

        if meter.system_info.reading is None:
            now = datetime.datetime.now()
            last_datetime = now.replace(
                microsecond=0,
                second=0,
                minute=(old_div(now.minute, heartbeat_length)) * heartbeat_length)
        else:
            last_datetime = meter.system_info.reading.heartbeat_end
            if heartbeat_end is not None and heartbeat_end == last_datetime:
                return 0

        last_energy = meter.system_info.last_energy
        cycles_per_hour = (old_div(60., self.cycle_length))
        consumption_in_kwh = old_div(self.energy_watts, (cycles_per_hour * 1000.))
        new_energy = last_energy + consumption_in_kwh
        if heartbeat_start is None:
            heartbeat_start = last_datetime
        if heartbeat_end is None:
            heartbeat_end = heartbeat_start + relativedelta(minutes=15)
        assert heartbeat_start != heartbeat_end
        data = {
            'meter': str(meter.code),
            'heartbeat_start': heartbeat_start,
            'heartbeat_end': heartbeat_end,
            'frequency': round(random.uniform(60.5, 60.6), 2),
            'state': "on",
            'uptime': 100,
            'voltage_min': round(min(voltages), 2),
            'voltage_max': round(max(voltages), 2),
            'voltage_avg': round(old_div(sum(voltages), 10.0), 2),
            'current_min': 1.0,
            'current_max': 1.0,
            'current_avg': 1.0,
            'energy': old_div(new_energy, meter.scalars.energy_scalar),
            'true_power_inst': 1.0,
            'true_power_avg': 1.0,
            'apparent_power_avg': 1.0,
            'power_factor_avg': 1.0,
            'user_power_limit': 12000,
        }
        add_reading(data, update_meter_state=False)
        return 1

    def get_meters(self, all_meters):
        left = len(all_meters)
        parts = []
        while left:
            if left <= 10:
                parts.append(left)
                break
            part = random.uniform(0.5, 0.8)
            value = int(left * part)
            left -= value
            parts.append(value)

        meters = all_meters[:]
        meterss = []
        random.shuffle(meters)
        for part in parts:
            meterss.append(meters[:part])
            meters[:] = meters[part:]
        return meterss


@reading.command('create-fake')
@click.option('-s', '--serial', default=None, help='Serial of meter')
@click.option('-c', '--cycle', type=int, default=0, help='Run in a cycle of n minutes')
@click.option('-e', '--energy', 'energy_watts', type=int, default=60, help='Energy in watts')
@with_appcontext
def create_fake(serial, cycle=0, energy_watts=60):
    """Add a random reading for this meter."""
    app = getUtility(IApplication)
    app.setup_databases()

    if cycle:
        generator = ReadingGenerator(energy_watts, cycle_length=cycle)
        return generator.run_cycle_loop()
    else:
        generator = ReadingGenerator(energy_watts, cycle_length=15)
        return generator.create_for_meter(serial)
