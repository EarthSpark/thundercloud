# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 sms views."""
import datetime
import http.client
import uuid

from flask_security import roles_accepted

from sparkmeter.api.apiviews0 import api, check_param, get_params, success
from sparkmeter.database.alchemy import sql
from sparkmeter.event.eventdomain import SMSMessage
from sparkmeter.exceptions import APIError, IncomingMessageReplyError
from sparkmeter.misc.datetimeutils import datetime_as_utc, parse_datetime
from sparkmeter.misc.phoneutils import format_phone_number, parse_phone_number


def _format_message(message):
    return dict(
        id=message.id,
        text=message.text,
        phone_number=message.phone_number,
        timestamp=message.timestamp,
    )


@api.route('/sms/outgoing', methods=['GET'])
@roles_accepted('api')
def sms_list_outgoing():
    """List outgoing SMS messages."""
    params = get_params()
    mark_delivered = check_param(params, 'mark_delivered', bool, default=True)

    messages = []
    for message in SMSMessage.get_outgoing():
        return_message = _format_message(message)
        if mark_delivered:
            message.processed = True
            sql.session.add(message)
        messages.append(return_message)

    if not messages:
        raise APIError("No outgoing messages in the queue",
                       status_code=http.client.NOT_FOUND)
    elif mark_delivered:
        sql.session.commit()
    return success(messages=messages)


@api.route('/sms/mark-delivered', methods=['PUT'])
@roles_accepted('api')
def sms_mark_delivered():
    """Mark messages as delivered."""
    params = get_params()
    param_messages = check_param(params, 'messages')
    message_ids = [uuid.UUID(m) for m in param_messages]
    if not message_ids:
        raise APIError("No outgoing messages specified",
                       status_code=http.client.BAD_REQUEST)
    messages = []
    for message in SMSMessage.get_outgoing(message_ids=message_ids):
        message.processed = True
        sql.session.add(message)
        messages.append({'id': message.id, 'status': "removed"})
        message_ids.remove(message.id)
    for message_id in message_ids:
        messages.append({'id': message_id, 'status': "not-found"})
    sql.session.commit()

    return success(messages=messages)


@api.route('/sms/incoming', methods=['POST'])
@roles_accepted('api')
def sms_add_incoming():
    """Add a new incoming SMS message"""
    params = get_params()
    external_id = check_param(params, 'id', required=False)
    phone_number = check_param(params, 'phone_number', parse_phone_number,
                               name='phone number')
    text = check_param(params, 'text')
    timestamp = check_param(params, 'timestamp', parse_datetime, name='datetime',
                            default=None)
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()
    else:
        timestamp = datetime_as_utc(timestamp)

    if external_id and SMSMessage.get_by_external_id(external_id):
        # FIXME: Change this status code httplib.CONFLICT when API can be broken
        raise APIError("message already exists", status_code=http.client.LOCKED)

    message = SMSMessage(
        direction=SMSMessage.DIRECTION_IN,
        external_id=external_id,
        processed=True,
        phone_number=format_phone_number(phone_number, format='E164'),
        text=text,
        timestamp=timestamp)
    sql.session.add(message)

    try:
        reply = message.handle_incoming()
        status_code = http.client.CREATED
    except IncomingMessageReplyError as e:
        reply = e.reply
        status_code = http.client.ACCEPTED

    #: The reply is returned synchronously from this method, mark it as processed.
    #: This also means that the caller of this function needs to send a message.
    reply.processed = True
    sql.session.add(reply)

    # If we can find a customer, fetch the ground from the customer
    # and update the reply with the ground id set
    if reply.ground:
        message.ground = reply.ground
        sql.session.add(message)

    sql.session.commit()

    r = success(message=_format_message(reply))
    r.status_code = status_code
    return r
