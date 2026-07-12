# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Tariff manage commands."""

import logging

import click
from flask.cli import with_appcontext
from zope.component import getUtility

from sparkmeter.cli_prompts import prompt_bool
from sparkmeter.interface import IApplication

logger = logging.getLogger(__name__)

tariff = click.Group("tariff", help="Tariff management commands.")


@tariff.command("create")
@click.option("-n", "--name", required=True, help="Name of the tariff")
@click.option("-r", "--rate", type=float, required=True, help="Flat rate price")
@click.option("-l", "--load-limit", type=int, default=0, help="Load limit in watts (default: 0)")
@with_appcontext
def create(name, rate, load_limit):
    """Create a new tariff."""
    from sparkmeter.database.alchemy import sql
    from sparkmeter.tariff.tariffdomain import Tariff

    app = getUtility(IApplication)
    app.setup_databases()

    existing = Tariff.query.filter_by(name=name).first()
    if existing:
        click.echo(f"Tariff '{name}' already exists", err=True)
        raise SystemExit(1)

    created, tariff_obj = Tariff.get_one_or_create(session=sql.session, name=name)
    tariff_obj.flat_price = rate
    tariff_obj.flat_load_limit = load_limit
    tariff_obj.tariff_type = Tariff.TYPE_FLAT
    sql.session.commit()
    click.echo(f"Tariff '{name}' created (rate={rate}, load_limit={load_limit})")
    return 0


@tariff.command("list")
@with_appcontext
def list_tariffs():
    """List all tariffs by ground."""
    from sparkmeter.meter.meterdomain import MeterBilling
    from sparkmeter.tariff.tariffdomain import Tariff

    app = getUtility(IApplication)
    app.setup_databases()

    fmt = "%36s | %30s | %10s | %12s | %10s | %18s |  %12s | %6s"
    logger.info(fmt % ("ID", "NAME", "LOAD LIMIT", "MONTHLY PLAN", "RATE TYPE", "RATE", "TOUS", "METERS"))
    logger.info("=" * 160)

    for tariff in Tariff.query.order_by(Tariff.name, Tariff.id):
        meter_count = MeterBilling.query.filter_by(tariff_id=tariff.id).count()
        logger.info(
            fmt
            % (
                tariff.id,
                tariff.name,
                tariff.flat_load_limit,
                tariff.plan_price,
                tariff.tariff_type,
                tariff.display_rate(),
                tariff.display_tou(),
                meter_count,
            )
        )


@tariff.command("merge")
@click.option("-a", "--merge-tariff", "tariff_id_a", required=True, help="Tariff to keep")
@click.option("-b", "--delete-tariff", "tariff_id_b", required=True, help="Tariff to delete")
@click.option("-y", "--assume-yes", "force", is_flag=True, help="Skip confirmation")
@with_appcontext
def merge(tariff_id_a, tariff_id_b, force=False):
    """Merge two tariffs."""
    from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
    from sparkmeter.database.alchemy import sql
    from sparkmeter.meter.meterdomain import MeterBilling
    from sparkmeter.tariff.tariffdomain import Tariff

    app = getUtility(IApplication)
    app.setup_databases()

    if tariff_id_a == tariff_id_b:
        logger.error("please enter two different tariffs")
        raise SystemExit(1)

    tariff_a = Tariff.get_by_id(tariff_id_a)
    if tariff_a is None:
        logger.error("tariff %s does not exist", tariff_id_a)
        raise SystemExit(1)

    tariff_b = Tariff.get_by_id(tariff_id_b)
    if tariff_b is None:
        logger.error("tariff %s does not exist", tariff_id_b)
        raise SystemExit(1)

    logger.info("Tariff remaining: %s (%s)", tariff_a.name, tariff_a.id)
    logger.info("Tariff to delete: %s (%s)", tariff_b.name, tariff_b.id)

    # all meters and dashboard summaries with tariff_b
    tariffb_meters = MeterBilling.query.filter_by(tariff_id=tariff_b.id)
    logger.warning("%d meters are associated with tariff %s", tariffb_meters.count(), tariff_b.name)

    tariffb_dashboards = DashboardDailyTariffSummary.query.filter_by(tariff_id=tariff_b.id)
    logger.warning(
        "%d dashboard summaries are associated with tariff %s", tariffb_dashboards.count(), tariff_b.name
    )

    # update tariffb meters and dashboard summaries with tariffa
    tariffb_meters.update(dict(tariff_id=tariff_a.id))
    tariffb_dashboards.update(dict(tariff_id=tariff_a.id))
    sql.session.commit()

    # delete tariffb
    msg = "Tariff %s will be deleted, are you sure" % (tariff_b.name,)
    if not force and not prompt_bool(msg, default=True):
        logger.info("tariff merge aborted")
        raise SystemExit(1)

    sql.session.delete(tariff_b)
    sql.session.commit()
    logger.info("tariff %s was deleted", tariff_b.name)

    return 0
