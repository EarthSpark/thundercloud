# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 configuration parameter views."""
import http.client
from collections import OrderedDict

from flask_security import roles_accepted

from sparkmeter.api.apiviews0 import api, check_param, get_params, success
from sparkmeter.config.configdomain import ConfigParameter
from sparkmeter.config.configparameter import ParameterObject
from sparkmeter.database.alchemy import sql
from sparkmeter.exceptions import APIError


@api.route("/config/", methods=['GET'])
@roles_accepted('api', 'operator')
def config_parameter_list():
    """List parameters."""

    parameters = []
    for attribute in sorted(ParameterObject.attributes):
        parameter = attribute.parameter
        parameters.append(
            (attribute.name,
             dict(
                 label=attribute.label,
                 last_modified=parameter.last_modified,
                 tooltip=attribute.tooltip,
                 value_type=attribute.param_type.type_name,
                 value=parameter.value,
             ))
        )
    return success(parameters=OrderedDict(parameters))


@api.route("/config/<string:parameter>", methods=['PUT'])
@roles_accepted('api', 'operator')
def config_parameter_update(parameter):
    """Update parameter."""
    params = get_params()

    # Parameter name
    param = ConfigParameter.get_by_name(parameter)
    if param is None:
        raise APIError("no such parameter", status_code=http.client.NOT_FOUND)

    parameter_type = param.parameter_type
    value = check_param(params, 'value',
                        name=parameter_type.type_name,
                        param_type=parameter_type.python_type)

    sql.session.add(param)
    param.value = value
    sql.session.commit()

    return success()
