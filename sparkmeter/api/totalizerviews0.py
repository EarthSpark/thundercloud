# -*- coding: utf-8 -*-
# Copyright © 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 customer views."""

import http.client

from flask import request
from flask_security import roles_accepted

from sparkmeter.api.apiviews0 import api, check_param, success
from sparkmeter.exceptions import APIError
from sparkmeter.meter.meterdomain import Meter, MeterView


def _format_totalizer(meter_view):
    """Format a totalizer according to a query result

    :param meter_view: query result
    :type meter_view: MeterView
    :return: a formatted dictionary
    :rtype: dict
    """
    meter = Meter.get_by_id(meter_view.id)
    return {
        "active": meter_view.active,
        "address": {
            "street1": meter_view.address_street1,
            "street2": meter_view.address_street2,
            "city": meter_view.address_city,
            "postalcode": meter_view.address_postalcode,
            "state": meter_view.address_state,
            "country": meter_view.address_country,
            "coords": meter_view.address_coords,
        },
        "is_running_plan": meter_view.is_running_plan,
        "last_config_datetime": meter.system_info.last_config_datetime,
        "last_energy": meter_view.last_energy,
        "last_energy_datetime": meter_view.last_energy_datetime,
        "last_meter_state_code": meter_view.current_state,
        "operating_mode": meter_view.state,
        "serial": meter_view.serial,
        "total_cycle_energy": meter_view.total_cycle_energy,
        "tags": meter_view.tags,
        "ground": {
            "id": meter_view.ground_id,
            "name": meter_view.ground_name,
        },
    }


@api.route("/totalizers")
@roles_accepted("api")
def totalizer_list():
    params = request.args.copy()
    meter_serial = check_param(params, "meter_serial", required=False)

    for name in ["meter_serial"]:
        params.pop(name, None)
    if params:
        raise APIError("unknown parameter(s): %r" % (list(params.keys()),))

    # Meter
    meter = None
    if meter_serial:
        meter = Meter.get_by_serial(meter_serial)
        if meter is None:
            raise APIError("no such meter", status_code=http.client.NOT_FOUND)
        if not meter.is_totalizer_meter():
            raise APIError("no such totalizer", status_code=http.client.NOT_FOUND)

    totalizers = []
    for meter_view in MeterView.get_view(meter_type=Meter.TYPE_TOTALIZER, meter=meter):
        totalizers.append(_format_totalizer(meter_view))
    return success(totalizers=totalizers)
