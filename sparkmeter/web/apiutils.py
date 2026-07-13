# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""API utilities.

These methods should be used for internal API only, external API should implement their own
version(s) of these utilities to emphasize API stability.
"""

import http.client

from flask.globals import request

from sparkmeter.exceptions import APIError
from sparkmeter.misc.jsonutils import jsonify
from sparkmeter.misc.pythonutils import unset


def success(**kwargs):
    """Return a successful JSON response."""
    return jsonify(error=None, status="success", **kwargs)


def get_params():
    """Parse the request and get parameters depending on the mime type."""
    if request.mimetype == "application/x-www-form-urlencoded":
        params = request.form
    elif request.mimetype == "application/json":
        params = request.get_json()
    else:
        raise APIError(
            "bad mimetype, must be application/x-www-form-urlencoded or application/json",
            status_code=http.client.UNSUPPORTED_MEDIA_TYPE,
        )

    return params


def check_param(params, param, param_type=None, name=None, default=unset):
    """Check a parameter.

    :param params: return value of get_params()
    :param param: param name
    :param param_type: param type
    :param name: param type name
    :param default: default value

    :raises APIError 400 (bad request): missing parameter
    :raises APIError 400 (bad request): bad parameter foo, cannot be empty
    :raises APIError 400 (bad request): bad parameter foo, must be a str
    """
    params = params or {}
    if param in params:
        value = params[param]
    elif default is not unset:
        value = default
    else:
        raise APIError("missing parameter: %s" % (param,))

    if value == "":
        raise APIError("bad parameter: %s, cannot be empty" % (param,))

    if param_type is not None:
        try:
            value = param_type(value)
        except ValueError:
            raise APIError("bad parameter: %s, must be a %s" % (param, name or param_type.__name__))

    return value
