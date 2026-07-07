# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Meter manage commands."""

import functools
import logging
import pprint
import time
from builtins import input

import click
from flask.cli import with_appcontext
from sqlalchemy.orm.exc import NoResultFound
from zope.component import getUtility

from sparkmeter.exceptions import MeterError
from sparkmeter.interface import IApplication
from sparkmeter.meter.meterdomain import Meter, MeterView

logger = logging.getLogger(__name__)

meter = click.Group('meter', help='Meter management commands.')


def with_forever(fn):
    """Decorator that adds --forever and --delay options to a Click command.

    Without --forever, the wrapped function runs once and returns.
    With --forever, it runs in a loop with --delay seconds between iterations.
    """
    @click.option('--delay', type=int, default=1, help='Seconds between iterations')
    @click.option('--forever', is_flag=True, help='Run in a loop')
    @functools.wraps(fn)
    def wrapper(*args, forever=False, delay=1, **kwargs):
        while True:
            fn(*args, **kwargs)
            if not forever:
                return
            time.sleep(delay)
    return wrapper


@meter.command('convert-to-totalizer')
@click.option('-s', '--serial', required=True, help='Serial of meter to convert')
@with_appcontext
def convert_customer_meter(serial):
    """Convert a customer to a totalizer meter."""
    from sparkmeter.database.alchemy import sql
    from sparkmeter.meter.meterdomain import Meter
    app = getUtility(IApplication)
    app.setup_databases()

    meter = Meter.get_by_serial(serial)
    if meter is None:
        logger.error("meter does not exist")
        raise SystemExit(1)
    if meter.meter_type != Meter.TYPE_CUSTOMER:
        logger.error("meter must be a customer meter")
        raise SystemExit(1)
    meter.meter_type = Meter.TYPE_TOTALIZER
    meter.convert_to_totalizer_meter()
    sql.session.add(meter)
    sql.session.commit()
    return 0


@meter.command('convert-to-customer')
@click.option('-s', '--serial', required=True, help='Serial of meter to convert')
@click.option('-t', '--tariff', required=True, help='Tariff of meter to convert')
@with_appcontext
def convert_totalizer_meter(serial, tariff):
    """Convert a totalizer to a customer meter."""
    from sparkmeter.database.alchemy import sql
    from sparkmeter.meter.meterdomain import Meter
    from sparkmeter.tariff.tariffdomain import Tariff
    app = getUtility(IApplication)
    app.setup_databases()

    meter = Meter.get_by_serial(serial)
    if meter is None:
        logger.error("meter does not exist")
        raise SystemExit(1)
    if meter.meter_type != Meter.TYPE_TOTALIZER:
        logger.error("meter must be a totalizer meter")
        raise SystemExit(1)
    try:
        tariff = Tariff.get_by_name(tariff)
    except NoResultFound:
        logger.error("tariff does not exist")
        raise SystemExit(1)
    meter.meter_type = Meter.TYPE_CUSTOMER
    meter.convert_to_customer_meter(tariff)
    sql.session.add(meter)
    sql.session.commit()
    return 0


@meter.command('create')
@click.option('-s', '--serial', required=True, help='Serial of meter to create')
@click.option('-m', '--mac', default=None, help='MAC of meter to create')
@click.option('--street1', default=None, help='Street1 of meter to create')
@with_appcontext
def create(serial, mac=None, street1=None):
    """Create and save a new meter."""
    from sparkmeter.config.configdict import config
    from sparkmeter.database.alchemy import sql
    from sparkmeter.ground.grounddomain import Ground
    from sparkmeter.tariff.tariffdomain import Tariff
    app = getUtility(IApplication)
    app.setup_databases()

    ground = Ground.get_default()
    try:
        meter_view = MeterView.create_meter(meter_type=Meter.TYPE_CUSTOMER,
                                            ground=ground,
                                            serial=serial)
    except MeterError as e:
        logger.error('ERROR: {}'.format(e.message))
        raise SystemExit(1)

    meter_view.address_street1 = street1
    meter_view.tariff = Tariff.get_by_name(name=config.get('NEW_METER_TARIFF', 'ET1'))
    sql.session.add(meter_view)
    meter_view.finish_creation()
    sql.session.commit()
    return 0


@meter.command('remove')
@click.option('-s', '--serial', required=True, help='Serial of meter to remove')
@with_appcontext
def remove(serial):
    """Remove a meter from the system."""
    from sparkmeter.database.alchemy import sql
    from sparkmeter.meter.meterdomain import Meter
    app = getUtility(IApplication)
    app.setup_databases()

    meter = Meter.get_by_serial(serial)
    if meter is None:
        logger.error("No such meter with serial: %s" % (serial, ))
        raise SystemExit(1)

    logger.info('Meter: %s' % (meter.serial, ))
    logger.info('Customer: %s' % (meter.customer.name, ))
    if meter.credit_wallet.value != 0:
        logger.warning('Credit balance: %f' % (meter.credit_wallet.value, ))
    if meter.debt_wallet.value != 0:
        logger.warning('Debt balance: %f' % (meter.debt_wallet.value, ))
    if meter.plan_wallet.value != 0:
        logger.warning('Plan balance: %f' % (meter.plan_wallet.value, ))
    for trans, _ in meter.get_transaction_view():
        logger.warning('Transaction %s %s %s %s' % (trans.id, trans.created, trans.amount,
                                                    trans.acct_type))

    c = input("Press Y to confirm removal of meter: (y/N) ")
    if c.lower() != 'y':
        logger.info('Okay, aborting')
        raise SystemExit(1)

    meter.remove()
    sql.session.commit()
    return 0


@meter.command('send-config')
@click.option('-m', '--mac', default=None, help='MAC of meter')
@click.option('-a', '--all', 'all_meters', is_flag=True, help='Send to all meters')
@with_appcontext
def send_config(mac=None, all_meters=False):
    """Send updated meter config to meter(s) with a sparkmac UpdateRequest packet."""
    from sparkmeter.meter.meterdomain import Meter
    app = getUtility(IApplication)
    app.setup_databases()
    if all_meters:
        meters = Meter.query.all()
    elif mac is not None:
        meters = [Meter.query.filter_by(code=mac).one()]
    else:
        logger.info("must supply either --all or a --mac parameter")
        raise SystemExit(1)

    for meter in meters:
        meter.send_set_config_unconditionally()
    return 0


@meter.command('get-heartbeat')
@click.option('-m', '--mac', required=True, help='MAC of meter to query')
@with_appcontext
def get_heartbeat_reading(mac):
    """Print the most recent stored reading for a meter."""
    from sparkmeter.reading.readingdomain import Reading
    app = getUtility(IApplication)
    app.setup_databases()
    reading = (
        Reading.query
        .filter_by(meter=mac)
        .order_by(Reading.heartbeat_end.desc())
        .first()
    )
    if reading is None:
        click.echo(f"no readings recorded for meter {mac}", err=True)
        raise SystemExit(1)
    pprint.pprint({c.name: getattr(reading, c.name) for c in reading.__table__.columns})


@meter.command('ping')
@click.option('-m', '--mac', default=None, help='MAC of meter to ping')
@with_appcontext
def ping(mac=None):
    """Send a per-meter ping via the metering provider.

    If `--mac` is omitted, pings every customer meter.
    """
    import asyncio

    from sparkmeter.meter.meterdomain import Meter
    from sparkmeter.metering.tools.cli_client import run_per_meter_command, submit_ping

    if mac is not None:
        meter_ids = [str(mac)]
    else:
        meter_ids = [str(m.code) for m in Meter.query.all()]

    asyncio.run(run_per_meter_command(submit_ping, meter_ids))


@meter.command('get-neighborlists')
@with_appcontext
def get_neighborlists():
    """Query each meter for its view of its radio neighbors."""
    import asyncio

    from sparkmeter.meter.meterdomain import Meter
    from sparkmeter.metering.tools.cli_client import run_per_meter_command, submit_query_neighbors

    meter_ids = [str(m.code) for m in Meter.query.all()]
    asyncio.run(run_per_meter_command(submit_query_neighbors, meter_ids))
