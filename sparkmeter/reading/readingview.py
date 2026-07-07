# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Views for the reading web interface."""
import csv
import datetime
import io
import logging
from builtins import str

from flask.globals import request
from flask.helpers import make_response
from flask.templating import render_template
from flask_security import roles_accepted

from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterstate import MeterState
from sparkmeter.misc.jsonutils import jsonify
from sparkmeter.reading.readingdomain import Reading, ReadingViewResult
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.blueprint import AuthBlueprint

logger = logging.getLogger(__name__)
reading = AuthBlueprint('reading', __name__)
ReadingViewResult = ReadingViewResult  # noqa


@reading.route("/readings/latest")
@roles_accepted('operator')
def latest():
    """Ground latest readings table."""
    return render_template('reading-latest.html')


@reading.route("/readings/latest.json")
@roles_accepted('operator')
def latest_data_json():
    """Ground latest readings data."""
    ground_serial = request.args.get('ground_serial')
    readings = _query_latest_readings(ground_serial)
    return jsonify(
        heartbeat_seconds=config['HEARTBEAT_PERIOD'] * 60,
        readings=readings,
    )


@reading.route("/readings/latest.csv")
@roles_accepted('operator')
def latest_data_csv():
    ground_serial = request.args.get('ground_serial')
    now = datetime.datetime.utcnow()
    readings = _query_latest_readings(ground_serial)
    si = io.StringIO()
    fields = [
        'serial',
        'customer_name',
        'customer_code',
        'state',
        'frequency',
        'voltage_avg',
        'current_avg',
        'true_power_inst',
        'energy',
        'uptime',
        'user_power_limit',
        'age',
        'prr',
        'address',
    ]
    cw = csv.DictWriter(si, extrasaction='ignore', fieldnames=fields,
                        lineterminator='\n')
    cw.writeheader()
    for row in readings:
        if row['heartbeat_end']:
            row['age'] = int((now - row['heartbeat_end']).total_seconds())
        else:
            row['age'] = ''

        if not row['customer_code']:
            row['customer_code'] = ''

        if not row['customer_name']:
            row['customer_name'] = ''
        cw.writerow(
            {k: str(v) for k, v in row.items()}
        )
    output = make_response(si.getvalue())
    filename = "latest-readings-%s.csv" % now.strftime('%Y%m%d%H%M')
    output.headers["Content-Disposition"] = "attachment; filename=%s" % filename
    output.headers["Content-type"] = "text/csv"
    return output


def _format_reading_view(result):
    """
    :param result:
    :type result: sparkmeter.reading.readingdomain.ReadingViewResult
    :return:
    """
    # If the meter has ever received a reading
    if result.reading_id:
        data = dict(
            current_avg=result.current_avg,
            current_max=result.current_max,
            current_min=result.current_min,
            energy=result.energy,
            frequency=result.frequency,
            heartbeat_end=result.heartbeat_end,
            state=MeterState.get_state_translation_from_id(result.reading_state),
            true_power_inst=int(round(result.true_power_inst)),
            uptime=result.uptime,
            user_power_limit=result.user_power_limit,
            voltage_avg=result.voltage_avg,
            voltage_max=result.voltage_max,
            voltage_min=result.voltage_min,
        )
    else:
        # add a placeholder reading for meters we have not yet heard from
        data = dict(
            age='',
            current_avg='',
            current_max='',
            current_min='',
            energy='',
            frequency='',
            heartbeat_end='',
            state='',
            true_power_inst='',
            uptime='',
            user_power_limit='',
            voltage_avg='',
            voltage_max='',
            voltage_min='',
        )

    parts = [result.street1, result.street2, result.city, result.state]
    data['address'] = u' '.join([str(p) for p in parts if p])
    data['ground_name'] = result.ground_name
    data['ground_serial'] = result.ground_serial
    data['serial'] = result.serial
    data['customer_name'] = result.customer_name
    data['customer_code'] = result.customer_code

    return data


def _query_latest_readings(ground_serial):
    if not config['HEROKU']:
        ground_serial = config.get('SERIAL')
    if ground_serial:
        ground = Ground.get_by_serial(ground_serial)
    else:
        ground = None
    user = get_current_user()

    readings = []
    # This will fetch the latest readings for all meters in the select ground
    query = Reading.get_latest_reading_view(ground, user)
    result = sql.session.execute(query)  # type: list[ReadingViewResult]
    for result in result:
        data = _format_reading_view(result)
        readings.append(data)
    return readings
