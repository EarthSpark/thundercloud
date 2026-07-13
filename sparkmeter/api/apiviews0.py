# -*- coding: utf-8 -*-
# Copyright © 2013-2025 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 views."""

import http.client
import logging

from flask.globals import request

from sparkmeter.exceptions import APIError
from sparkmeter.misc.jsonutils import jsonify
from sparkmeter.misc.pythonutils import unset
from sparkmeter.web.blueprint import APIBlueprint

api = APIBlueprint(__name__, version=0)
logger = logging.getLogger(__name__)


@api.app_errorhandler(APIError)
def handle_apierror(exc):
    """Transform an APIError into a JSON error object."""
    r = jsonify(exc.to_dict())
    r.status_code = exc.status_code
    return r


def get_params():
    """Retrieve request parameters based on the request's Content-Type

    :returns: A dict-like collection of parameters of the request parameters.
    """
    if request.mimetype == "application/x-www-form-urlencoded":
        params = request.form
        if len(params) == 1 and list(params.keys())[0][0] in ("{", "["):
            raise APIError("bad mimetype, JSON data must use the application/json Content-Type")
    elif request.mimetype == "application/json":
        params = request.get_json(silent=True) or {}
    else:
        raise APIError(
            "bad mimetype, must be application/x-www-form-urlencoded or application/json",
            status_code=http.client.UNSUPPORTED_MEDIA_TYPE,
        )

    return params


def _type_name(t):
    """Get a user friendly type name for a variable/type.

    This is used for display purposes when mentioning a type to the user.
    `str` and `unicode` are converted to 'string'.
    Everything else is just the lower case class name.
    Lower case is there to make `UUID` come out as 'uuid' which is what we expect elsewhere in the code.

    :param t: The variable or type that we want the name of
    :returns: The user friendly name (int, string, float, uuid...)
    :rtype: str
    """

    # if an instance was passed, get the instances type
    if not isinstance(t, type):
        t = type(t)

    # handle string/unicode as strings for the sake of error messages
    if t.__name__ in ("str", "unicode"):
        return "string"

    # return the lower case name of the type
    return t.__name__.lower()


def check_param(
    params, param, param_type=None, name=None, default=unset, required=True, allow_empty=False, strict=False
):
    """Safely retrieve a parameter from a the parameter list.

    :param params: The dictionary of request parameters.
    :param param: The name of the parameter to retrieve.
    :param param_type: (optional) the Python type to which the parameter should be converted.
    :param name: (optional) a pretty name for custom param types
    :param default: (optional) the value to return if the parameter isn't in the request parameter dict.
    :param required: (optional) `True` if the parameter is required, `False` otherwise.
    :param allow_empty: (optional) `True` if the parameter is permitted to be empty, `False` otherwise.
    :param strict: (optional) `True` if the param must be an instance of the param_type, `False` otherwise.
    :returns: The parameter value.
    """
    params = params or {}
    if param in params:
        value = params[param]
    elif default is not unset:
        value = default
    elif not required:
        return
    else:
        raise APIError("missing parameter: %s" % (param,))

    if value == "" and not allow_empty:
        raise APIError("bad parameter: %s, cannot be empty" % (param,))

    # provide a default friendly param type name if none is provided
    if name is None:
        name = _type_name(param_type)

    # enforce checking the exact param_type, not just if it is parsable by the param type
    if strict and not isinstance(value, param_type):
        raise APIError(
            "bad parameter: {}, expected {} type, got {}".format(
                param,
                name,
                _type_name(value),
            )
        )

    if param_type is str:
        if value is None:
            return None
        elif type(value) not in [str]:
            raise APIError("bad type, expected string, got {}".format(type(value).__name__))
        else:
            return value
    elif param_type is bool:
        if type(value) is bool:
            return value
        if isinstance(value, str):
            if value.lower() in ["true", "1"]:
                return True
            elif value.lower() in ["false", "0"]:
                return False
        raise APIError("failed to parse boolean parameter: %s" % (value,))
    elif param_type is list:
        if not isinstance(value, list):
            raise APIError("bad parameter: %s, must be a list" % (param,))

    if param_type is not None and value is not default:
        # if the param_type here is int, but the value is a float,
        # this will not raise an exception. This can then go down the line,
        # be converted into a string, and then no longer be parsable as an int.
        # this can be enforced using the strict param.
        try:
            value = param_type(value)
        except (ValueError, TypeError):
            raise APIError("bad parameter: %s, must be a %s" % (param, name))

    return value


def assert_one_of_params(provided_params, accepted_params):
    """Raise an exception if none of the parameters supplied match what is accepted by an endpoint.

    :param provided_params: The request-provided parameters
    :param accepted_params: The endpoint-accepted parameters
    :returns:
    """
    if not frozenset(accepted_params).intersection(frozenset(provided_params or tuple())):
        raise APIError(
            "no valid parameters found, expected one or many from: %s" % (", ".join(accepted_params),)
        )


def success(**kwargs):
    return jsonify(error=None, status=kwargs.get("status", "success"), **kwargs)


def register_api_blueprint(app):
    """Register all blueprints for the API v0."""
    import sparkmeter.api.configviews0  # noqa
    import sparkmeter.api.customerviews0  # noqa
    import sparkmeter.api.eventviews0  # noqa

    if app.config.get("S3_HISTORY_BUCKET") and app.config.get("S3_SITE"):
        import sparkmeter.api.historyviews0  # noqa
    import sparkmeter.api.groundviews0  # noqa
    import sparkmeter.api.meterviews0  # noqa
    import sparkmeter.api.salesaccountviews0  # noqa
    import sparkmeter.api.smsviews0  # noqa
    import sparkmeter.api.systemviews0  # noqa
    import sparkmeter.api.tariffviews0  # noqa
    import sparkmeter.api.totalizerviews0  # noqa
    import sparkmeter.api.transactionviews0  # noqa

    app.register_blueprint(api)
