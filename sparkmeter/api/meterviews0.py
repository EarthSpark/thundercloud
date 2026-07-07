# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 meter views."""
import http.client

from flask_security import roles_accepted

from sparkmeter.api.apiviews0 import api, check_param, get_params, success
from sparkmeter.database.alchemy import sql
from sparkmeter.exceptions import APIError
from sparkmeter.meter.meterdomain import Meter, MeterModels


# FIXME: Change this to a PUT method API can be broken
@api.route("/meter/<string:meter_serial>/set-operating-mode", methods=['POST'])
@roles_accepted('api')
def meter_set_operating_mode(meter_serial):
    """Change Meter Operating Mode."""
    # State
    params = get_params()
    state = check_param(params, 'state')
    try:
        state = Meter.state_from_string(state)
    except ValueError:
        raise APIError("bad parameter: state, bad value")

    # Meter serial
    meter = Meter.get_by_serial(meter_serial)
    if meter is None:
        raise APIError("no such meter", status_code=http.client.NOT_FOUND)

    if not meter.is_customer_meter():
        raise APIError("invalid meter", status_code=http.client.NOT_FOUND)

    sql.session.add(meter)
    meter.set_state(state)
    sql.session.commit()

    return success()


@api.route('/meters/models', methods=['GET'])
@roles_accepted('api', 'operator')
def list_meter_models():
    """List meter models"""
    models = []
    for result in sql.session.execute(MeterModels.get_model_counts()):
        models.append({
            'name': result.name,
            'continuous_limit': result.continuous_limit,
            'inrush_limit': result.inrush_limit,
            'phase_count': result.phase_count,
            'count': result.count,
        })
    return success(models=models)
