# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""JSON (de)serialization utilities."""

import datetime
import json
import uuid
from builtins import str

from flask import current_app


class JsonEncoder(json.JSONEncoder):
    """Class for custom encoding of our data to json."""

    item_separator = ","
    key_separator = ": "

    def default(self, obj):
        """Process objects into json."""
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        elif type(obj).__name__.endswith("LazyString"):
            return str(obj)
        elif type(obj).__name__ == "Choice":
            return str(obj.code)
        elif type(obj).__name__ == "Decimal":
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif hasattr(obj, "__json__"):
            return obj.__json__()
        else:  # pragma: nocoverage
            return super().default(obj)


def json_loads(payload):
    """Json deserializer."""
    return json.loads(payload)


def json_dumps(obj, sort_keys=True, indent=None, separators=None):
    """Json serializer."""
    return json.dumps(obj, cls=JsonEncoder, sort_keys=sort_keys, indent=indent, separators=separators)


def json_dump(obj, fp):  # pragma: nocoverage
    """Json serializer to file."""
    return json.dump(obj, fp, cls=JsonEncoder)


def jsonify(*args, **kwargs):
    """Serialize to a Flask response."""
    if len(args) == 1:  # single args are passed directly to dumps()
        data = args[0]
    else:
        data = args or kwargs

    # FIXME: This should probably be minified properly
    return current_app.response_class(
        (json_dumps(data, indent=2, separators=(",", ": ")), ""),
        mimetype="application/json",
    )
