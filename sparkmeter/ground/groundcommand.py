# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Ground manage commands."""

import click
from flask.cli import with_appcontext
from zope.component import getUtility

from sparkmeter.interface import IApplication


@click.command("create-ground")
@click.option("-s", "--serial", default=None, help="Serial of ground")
@click.option("-n", "--name", default=None, help="Name of ground")
@click.option("-k", "--secret-key", default=None, help="Secret API key")
@with_appcontext
def create_ground(serial, name, secret_key):
    """Create and save a new ground instance, along with tariffs."""
    from sparkmeter.ground.grounddomain import Ground
    from sparkmeter.models import session_scope

    app = getUtility(IApplication)
    app.setup_databases()
    with session_scope() as session:
        try:
            Ground.create_empty(
                session,
                serial=serial,
                name=name,
                secret_key=secret_key,
            )
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
