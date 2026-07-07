# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Event manage commands.py."""

import datetime
import logging

import click
from flask.cli import with_appcontext
from zope.component import getUtility

from sparkmeter.interface import IApplication

logger = logging.getLogger(__name__)

event = click.Group('event', help='Event management commands.')


@event.command('create-sms')
@click.option('--text', required=True, help='SMS text')
@click.option('--phone-number', required=True, help='Phone number')
@click.option('--direction', type=click.Choice(['in', 'out']), default='in', help='Direction')
@with_appcontext
def create_sms_message(text, phone_number, direction='in'):
    """Add an SMS message."""
    from sparkmeter.event.eventdomain import SMSMessage
    from sparkmeter.exceptions import IncomingMessageReplyError
    from sparkmeter.models import session_scope
    app = getUtility(IApplication)
    app.setup_databases()
    with session_scope() as session:
        message = SMSMessage(
            text=text,
            phone_number=phone_number,
            direction=direction,
            timestamp=datetime.datetime.utcnow(),
            processed=True)
        logging.info('Created incoming %s' % (message.text, ))
        session.add(message)

        if message.direction == SMSMessage.DIRECTION_IN:
            try:
                reply = message.handle_incoming()
            except IncomingMessageReplyError as e:
                reply = e.reply
                e.processed = True
            session.add(reply)

            logging.info('Created outgoing %s' % (reply.text, ))
            session.commit()


@event.command('process')
@with_appcontext
def process_events():
    """Process all pending SMS messages."""
    from sparkmeter.tasks import process_events
    app = getUtility(IApplication)
    app.setup_databases()

    process_events()
