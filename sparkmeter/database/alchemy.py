# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Flask-SQLAlchemy integration."""

import os
import sys
import traceback

from flask import request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

from sparkmeter.config.configdict import config
from sparkmeter.misc.jsonutils import json_dumps


def get_app_name(argv):
    """Create a formatted PostgreSQL application name.

    This will create an application name that is passed on to PostgreSQL
    based on the command line arguments, eg how it was invoked.
    This will be visible as the 'application_name' column in the
    pg_stats_activity table and will help to know more about the context
    of each PostgreSQL connection.
    :param argv: command line arguments passed in, usually sys.argv.
    """
    args = []
    if 'hypercorn' in argv[0]:
        args = ['hypercorn']
    elif 'gunicorn' in argv[0]:
        args = ['gunicorn']
    elif 'uwsgi' in argv[0]:
        args = ['uwsgi']
    elif 'main.py' in argv[0] or 'asgi.py' in argv[0]:
        args = ['dev']
    else:
        args = argv
    # We have 63 characters available in the application name,
    # postgresql truncates everything beyond that, so we have to
    # use a couple of acronyms
    return 'sm-{args:.54}-{pid}'.format(
        args='-'.join(args),
        pid=os.getpid())


class SparkmeterSQLAlchemy(SQLAlchemy):

    """SQLAlchemy subclass with our own engine options."""

    def __init__(self, *args, **kwargs):
        """Initialize the app."""
        self.app_name = None
        super(SparkmeterSQLAlchemy, self).__init__(*args, **kwargs)

    def init_app(self, app):
        """Store app name."""
        super(SparkmeterSQLAlchemy, self).init_app(app)
        self.app_name = app.name

    def apply_driver_hacks(self, app, info, options):
        """Overridden from base class."""
        super(SparkmeterSQLAlchemy, self).apply_driver_hacks(app, info, options)
        options['connect_args'] = dict(application_name=get_app_name(sys.argv))
        options['json_serializer'] = json_dumps


sql = SparkmeterSQLAlchemy(session_options={"autoflush": False})


def format_sql_stack(stack):
    """Get a formatted callstack for query debugging."""
    lines = []
    for filename, linenum, funcname, _ in stack:
        if funcname == "sqlalchemy_query_tagger" or funcname == "__call__":
            continue
        if 'sparkmeter/' in filename:
            path = filename.split('sparkmeter/')[1]
            lines.append("{}:{}:{}".format(path, linenum, funcname))
    return "->".join(lines)


@event.listens_for(Engine, "before_cursor_execute", retval=True)
def sqlalchemy_query_tagger(conn, cursor, statement, parameters, context, executemany):
    """Tag outgoing SQLAlchemy queries with their origin."""
    format_string = config.get('QUERY_TAGGING_FORMAT')
    if format_string is None:
        return statement, parameters
    endpoint = None
    try:
        endpoint = request.endpoint
    except RuntimeError:  # If we're not running in Flask...
        pass
    comment = " /* {} */".format(format_string).format(
        app_name=sql.app_name, endpoint=endpoint, stack=format_sql_stack(traceback.extract_stack()))
    return statement + comment, parameters
