# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""System manage commands.py."""
from __future__ import print_function

import json
import logging
from collections import OrderedDict

import click
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError
from zope.component import getUtility

from sparkmeter.__version__ import version as current_version
from sparkmeter.config.configdict import config
from sparkmeter.interface import IApplication

logger = logging.getLogger(__name__)

system = click.Group('system', help='System management commands.')


@system.command('register')
@click.option('--version', 'version', default=None, help='Version to register')
@with_appcontext
def register(version):
    """Add an application version to the system_version table."""
    from sparkmeter.database.alchemy import sql
    from sparkmeter.system.systemdomain import SystemState, SystemVersion
    if version is None:
        version = current_version
    app = getUtility(IApplication)
    app.setup_databases()

    # verify that this is only run on the ground
    if config.is_cloud():
        logger.error("This command can only be run on the ground")
        raise SystemExit(1)

    sv = SystemVersion()
    # according to pkg_resources.parse_version, any string seems to be a valid version
    sv.version = str(version)
    sql.session.add(sv)

    ss = None

    # if sv is newer than the current version, then we should state transtion to UPGRADABLE
    if sv.status == SystemVersion.STATUS_NEW:
        ss = SystemState.set_state(
            state=SystemState.STATE_UPGRADABLE,
            action="version {} prereleased on ground".format(sv.version),
            version=sv.version,
        )

    try:
        sql.session.commit()
    except IntegrityError:
        logger.warning("version %s is already in the database.", sv.version)
        return 0

    logger.info("Added version %s to database.", sv.version)
    if ss:
        logger.info("System state transitioned to %s.", ss.state)
    return 0


@system.command('versions')
@with_appcontext
def versions():
    """Print the versions installed on the basestation and the date installed."""
    from sparkmeter.system.systemdomain import SystemVersion
    app = getUtility(IApplication)
    app.setup_databases()

    versions = SystemVersion.query.all()

    json_data = json.dumps(
        OrderedDict([
            (
                v.version,
                OrderedDict([
                    ("status", v.status),
                    ("installed", v.timestamp.isoformat()),
                ])
            )
            for v in sorted(versions)
        ]),
        indent=4,
        separators=(',', ': '),
    )

    print(json_data)
    return 0


@click.command()
@click.option('--format', 'output_format', default='table',
              type=click.Choice(['table', 'json', 'csv']),
              help='Output format')
@with_appcontext
def status(output_format):
    """Show application status and health information."""
    click.echo('Sparkmeter Application Status')
    click.echo('=' * 30)

    app = getUtility(IApplication)

    status_info = {
        'Mode': app.mode,
        'Debug': app.debug,
        'Developer Mode': app.developer_mode,
        'Read-only Mode': app.readonly_mode,
        'Static Folder': app.static_folder,
    }

    if output_format == 'json':
        import json as json_mod
        click.echo(json_mod.dumps(status_info, indent=2))
    elif output_format == 'csv':
        for key, value in status_info.items():
            click.echo(f"{key},{value}")
    else:  # table format
        for key, value in status_info.items():
            click.echo(f"{key:20}: {value}")
