# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Flask CLI command registration.

All commands are defined in their respective domain modules.
This module registers them with the Flask app.
"""

from zope.component import getUtility

from sparkmeter.interface import IApplication


def register_cli_commands(app):
    """Register all CLI commands with the Flask app."""
    from sparkmeter.dashboard.dashboardcommand import dashboard
    from sparkmeter.database.databasecommand import database, demo, initdb, resetdb
    from sparkmeter.event.eventcommand import event
    from sparkmeter.ground.groundcommand import create_ground
    from sparkmeter.meter.metercommand import meter
    from sparkmeter.metering.cli import metering
    from sparkmeter.reading.readingcommand import reading
    from sparkmeter.salesaccount.salesaccountcommand import salesaccount
    from sparkmeter.servercommand import server, shell
    from sparkmeter.system.systemcommand import status, system
    from sparkmeter.tariff.tariffcommand import tariff
    from sparkmeter.transaction.transactioncommand import transaction
    from sparkmeter.user.usercommand import user

    # Command groups
    app.cli.add_command(dashboard)
    app.cli.add_command(database)
    app.cli.add_command(event)
    app.cli.add_command(meter)
    app.cli.add_command(metering)
    app.cli.add_command(reading)
    app.cli.add_command(salesaccount)
    app.cli.add_command(server)
    app.cli.add_command(system)
    app.cli.add_command(tariff)
    app.cli.add_command(transaction)
    app.cli.add_command(user)

    # Standalone commands
    app.cli.add_command(create_ground)
    app.cli.add_command(shell)
    app.cli.add_command(status)

    # Backwards-compatible aliases for old Flask-Script commands
    app.cli.add_command(initdb)
    app.cli.add_command(resetdb)
    app.cli.add_command(demo)

    # Shell context for the built-in `flask shell` command
    @app.shell_context_processor
    def make_shell_context():
        """Add useful objects to the flask shell context."""
        from sparkmeter.controller import get_ground
        from sparkmeter.database.alchemy import sql
        from sparkmeter.models import BaseDomain

        ns = dict(
            app=getUtility(IApplication),
            ground=get_ground(),
            sql=sql,
        )
        # Add all domain models
        ns.update({m.__name__: m for m in BaseDomain.__subclasses__()})
        return ns
