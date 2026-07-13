# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 system views."""

from flask_security import roles_accepted

from sparkmeter.api.apiviews0 import api, success
from sparkmeter.ground.grounddomain import Ground


@api.route("/system-info")
@roles_accepted("api")
def system_info():
    """Get System Info."""
    grids = []
    for ground in Ground.get_all():
        grids.append(
            dict(
                id=ground.id,
                name=ground.name,
                serial=ground.serial,
                last_sync_date=ground.get_last_sync_date(),
                override_meter_state=ground.private.override_meter_state,
                override_meter_state_modified=ground.private.override_meter_state_modified,
            )
        )
    return success(grids=grids)
