# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 ground views."""

import http.client

from flask_security import roles_accepted

from sparkmeter.api.apiviews0 import api, check_param, get_params, success
from sparkmeter.database.alchemy import sql
from sparkmeter.exceptions import APIError
from sparkmeter.ground.grounddomain import Ground


# FIXME: Change this to a PUT method API can be broken
@api.route("/ground/<string:ground_serial>/set-override-meter-state", methods=["POST"])
@roles_accepted("api")
def ground_set_override_meter_state(ground_serial):
    """Change Ground override meter state."""
    # State
    params = get_params()
    state = check_param(params, "state", bool)
    # Ground serial
    ground = Ground.get_by_serial(ground_serial)
    if ground is None:
        raise APIError("no such ground", status_code=http.client.NOT_FOUND)

    sql.session.add(ground)
    ground.private.queue_override_meter_state(state)
    sql.session.commit()

    return success()
