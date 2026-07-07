# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Transaction manage commands.py."""

import click
from flask.cli import with_appcontext
from zope.component import getUtility

from sparkmeter.config.configdict import config
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.interface import IApplication

transaction = click.Group('transaction', help='Transaction management commands.')


@transaction.command('process')
@with_appcontext
def process():
    """Process all pending transactions immediately."""
    from sparkmeter.controller import process_transaction
    from sparkmeter.transaction.transactiondomain import Transaction
    app = getUtility(IApplication)
    app.setup_databases()

    ground = Ground.get_by_serial(config['SERIAL'])
    for transaction in Transaction.get_unprocessed(ground):
        process_transaction(transaction.id)
