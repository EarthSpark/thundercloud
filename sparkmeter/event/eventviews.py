# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Alert api views."""

import csv
import operator
from collections import OrderedDict
from io import StringIO

from flask import request
from flask.templating import render_template
from flask.wrappers import Response
from flask_security import roles_accepted

from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.event.eventdomain import Event, SMSConfigMessage, SMSMessage
from sparkmeter.event.eventspecs import EventSpec
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.misc.jsonutils import jsonify
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.apiutils import success
from sparkmeter.web.blueprint import AuthBlueprint

event = AuthBlueprint("event", __name__)


@event.route("/event/event-types")
@roles_accepted("operator")
def event_types():
    """List of available event types that can be sent as SMS messages."""
    event_types = []
    for spec in EventSpec.get_all():
        if spec.object_table not in ["meter", "transactions"]:
            continue
        event_types.append(format_event_type(spec.event_type))
    event_types.sort(key=operator.itemgetter("label"))
    return success(event_types=event_types)


@event.route("/event/message-types")
@roles_accepted("operator")
def message_types():
    """List of available message types."""
    message_labels = {}
    message_types = []
    for key, mti in list(SMSConfigMessage.messages.items()):
        message_type = dict(value=key, label=str(mti.label), description=str(mti.description))
        message_types.append(message_type)
        message_labels[key] = str(mti.label)
    message_types.sort(key=operator.itemgetter("label"))
    return success(message_labels=message_labels, message_types=message_types)


@event.route("/event/messages")
@roles_accepted("operator")
def messages():
    """Ground messages table."""
    return render_template(
        "messages-list.html",
        ground=Ground.get_current(),
    )


# Whitelist and map orderable column names
DATATABLE_COLUMN_MAP = {
    "1": "sms_type",
    "3": "customer_name",
    "timestamp": "timestamp",
    "direction": "direction",
    "text": "text",
    "processed": "processed_fmt",
    "ground_name": "ground_name",
}


def parse_datatables_args():
    """Parse the relevant datatables parameters."""
    params = {
        "draw": int(request.args.get("draw", "1")),
        "start": int(request.args.get("start", "0")),
        "length": int(request.args.get("length", "100")),
        "order": {
            "column_idx": int(request.args.get("order[0][column]", "-1")),
            "column_name": None,
            "dir": request.args.get("order[0][dir]", "desc"),
        },
        "search": {
            "value": request.args.get("search[value]", ""),
            "regex": request.args.get("search[regex]", "false") == "true",
        },
    }
    column_name = request.args.get("columns[{}][data]".format(params["order"]["column_idx"]), "timestamp")
    # Map ALL columns to serve as a SQL injection whitelist
    params["order"]["column_name"] = DATATABLE_COLUMN_MAP[column_name]
    return params


@event.route("/event/messages.json")
@roles_accepted("operator")
def messages_data():
    """Ground messages data."""
    ground = Ground.get_current()
    user = get_current_user()
    filter_args = parse_datatables_args()
    query = SMSMessage.get_messages_view(
        ground=ground,
        user=user,
        order=filter_args["order"]["column_name"],
        ascending=filter_args["order"]["dir"] == "asc",
        offset=filter_args["start"],
        limit=filter_args["length"],
        query_string=filter_args["search"]["value"],
    )
    results = sql.session.execute(query)
    return jsonify(**format_messages(results, filter_args["draw"]))


def iter_csv(data):
    """A generator that converts a message object to CSV."""
    mapping = OrderedDict(
        [
            ("Date", "timestamp"),
            ("Type", "sms_type"),
            ("In/Out", "direction"),
            ("Customer Name", "customer_name"),
            ("Phone Number", "phone_number"),
            ("Message", "text"),
            ("Processed", "processed_fmt"),
            ("Event Type", "event_type"),
            ("Message Type", "message_type"),
            ("Origin", "origin"),
            ("Ground", "ground_name"),
        ]
    )
    line = StringIO()
    writer = csv.DictWriter(line, fieldnames=mapping.keys(), extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    line.seek(0)
    yield line.read()
    for record in data:
        line.truncate(0)
        line.seek(0)
        message = {}
        row = record._mapping
        for key, fieldname in mapping.items():
            message[key] = row[fieldname]
        writer.writerow(message)
        line.seek(0)
        yield line.read()


@event.route("/event/messages.csv")
@roles_accepted("operator")
def messages_export():
    """Ground messages data."""
    ground = Ground.get_current()
    user = get_current_user()
    filter_args = parse_datatables_args()
    query = SMSMessage.get_messages_view(
        ground=ground,
        user=user,
        order=filter_args["order"]["column_name"],
        ascending=filter_args["order"]["dir"] == "asc",
        offset=None,
        limit=None,
        query_string=filter_args["search"]["value"],
    )
    results = sql.session.execute(query)
    response = Response(iter_csv(results), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=messages.csv"
    return response


def format_event_type(event_type):
    """
    Format an event type for JSON serialization

    :param event_type: event type to format
    :return: dictionary
    """
    locale = config.get_current_locale()
    spec = EventSpec.get_by_event_type(event_type)
    keywords = []
    for keyword in spec.keywords:
        # Extract only the necessary data to avoid circular references
        keyword_data = {
            "name": str(keyword.name),
            "description": str(keyword.description),
            "example": str(keyword.format(keyword.example, locale)),
        }
        keywords.append(keyword_data)
    event_type = dict(
        value=spec.event_type,
        label=str(Event.events[spec.event_type].label),
        keywords=keywords,
    )
    return event_type


def format_messages(results, draw):
    """Format a messages query result.

    Format a query result from SMSMessage.get_messages() and make it
    suitable for displaying in a JSON api.
    :param results: the query results
    :returns: an iterator of dictionaries
    """
    total = 0
    rv = []
    for r in results:
        alert_label = None
        if r.event_type:
            # FIXME: Maybe this is too slow for large lists of messages,
            #        If so, move this to use EventTypeService on the client side.
            spec = EventSpec.get_by_event_type(r.event_type)
            if spec:
                alert_label = Event.events[r.event_type].label
        rv.append(
            dict(
                alert_label=alert_label,
                event_type=r.event_type,
                code=r.code,
                customer_name=r.customer_name,
                origin=r.origin,
                direction=r.direction,
                message_type=r.message_type,
                ground_name=r.ground_name,
                ground_serial=r.ground_serial,
                phone_number=r.phone_number,
                processed=r.processed,
                timestamp=r.timestamp,
                text=r.text,
            )
        )
        total = r.total
    return {"total": total, "draw": draw, "messages": rv}
