# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Views for the meter web interface."""
import datetime
import http.client
import io
import logging

import dateutil
from dateutil.tz import tzlocal, tzutc
from flask.globals import request
from flask.helpers import flash, send_file, url_for
from flask.templating import render_template
from flask.wrappers import Response
from flask_babel import lazy_gettext as _
from flask_security import roles_accepted
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from sparkmeter.config.configdict import config
from sparkmeter.config.configparameter import parameters
from sparkmeter.database.alchemy import sql
from sparkmeter.event.eventdomain import SMSMessage
from sparkmeter.event.eventviews import Event, format_messages
from sparkmeter.event.eventviews import iter_csv as iter_message_csv
from sparkmeter.event.eventviews import parse_datatables_args as parse_datables_message_args
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterdomain import Meter, MeterView
from sparkmeter.meter.meterform import ChartForm, MeterAddForm, MeterEditForm
from sparkmeter.misc.jsonutils import jsonify
from sparkmeter.reading.readingdomain import Reading
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.transaction.transactiondomain import TransactionView
from sparkmeter.transaction.transactionview import format_transaction_views
from sparkmeter.transaction.transactionview import iter_csv as iter_transaction_csv
from sparkmeter.transaction.transactionview import \
    parse_datatables_args as parse_datatables_transaction_args
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.blueprint import AuthBlueprint
from sparkmeter.web.permission import verify_permission

logger = logging.getLogger(__name__)
meter = AuthBlueprint('meter', __name__)


# Redirect for for backwards compatibility added in 1.4
@meter.route("/microgrid/<ground_serial>/<string:meter_serial>/<path:path>")
@meter.route("/microgrid/<ground_serial>/<string:meter_serial>/")
# Redirect for backwards compatibility added in 1.1
@meter.route("/microgrid/<ground_serial>/<int:meter_code>/")
@meter.route("/microgrid/<ground_serial>/<int:meter_code>/<path:path>")
def code_redirect(ground_serial, meter_serial=None, meter_code=None, path=""):
    """
    Permanent redirect for urls using the old int:meter_code urls.

    This is only for backwards compatability with grids that had the old urls.
    """
    ground = Ground.get_by_serial(ground_serial)
    if ground is None:  # pragma: nocoverage
        abort(http.client.NOT_FOUND)
    meter = None
    if meter_code is not None:
        meter = Meter.get_by_code(ground, meter_code)
    elif meter_serial is not None:
        meter = Meter.get_by_serial(meter_serial)
    if meter is None:
        abort(http.client.NOT_FOUND)
    return redirect(
        "/meter/%s/%s" % (meter.serial, path),
        http.client.MOVED_PERMANENTLY,
    )


@meter.route("/meter/meters.json")
@roles_accepted('operator', 'vendor')
def meters_json():
    """Ground transaction data."""
    meter_type = request.args.get('meter_type', Meter.TYPE_CUSTOMER)
    if meter_type not in [Meter.TYPE_CUSTOMER,
                          Meter.TYPE_TOTALIZER]:
        abort(http.client.BAD_REQUEST)
    if config['HEROKU']:
        ground = None
    else:
        ground = Ground.get_by_serial(config.get('SERIAL'))

    meter_views = MeterView.get_view(
        meter_type=meter_type,
        ground=ground,
        user=get_current_user())
    return jsonify(meters=format_meter_view(meter_views))


@meter.route("/meter/add-meter/<string:meter_type>",
             methods=['GET', 'POST'])
@meter.route("/meter/add-meter",
             methods=['GET', 'POST'])
@verify_permission('meter', 'add', status=http.client.FORBIDDEN)
def add(meter_type=Meter.TYPE_CUSTOMER):
    """Register a new meter."""
    if meter_type not in [Meter.TYPE_CUSTOMER, Meter.TYPE_TOTALIZER]:
        abort(http.client.BAD_REQUEST)

    ground = Ground.get_default()
    form = MeterAddForm(
        formdata=request.form,
        meter_type=meter_type,
    )
    if request.method == 'POST' and form.validate():
        meter_view = MeterView.create_meter(meter_type, ground, form.serial.data)
        sql.session.add(meter_view)
        form.save(meter_view)
        meter_view.finish_creation()
        sql.session.commit()
        return form.notify_and_redirect(meter_view)
    return form.render(meter_type=meter_type,
                       ground=ground)


@meter.route("/meter/<string:meter_serial>/edit",
             methods=['GET', 'POST'])
@verify_permission('meter', 'edit', status=http.client.FORBIDDEN)
def edit(meter_serial, phase=None):
    """Meter edit page."""
    meter = Meter.get_by_serial(meter_serial)
    if meter is None:
        abort(http.client.NOT_FOUND)
    if meter.is_customer_meter():
        if meter.customer.country_code is None:
            meter.customer.country_code = config['DEFAULT_PHONE_COUNTRY_CODE']

    meter_view = MeterView.get_by_id(meter.id)
    form = MeterEditForm(
        formdata=request.form,
        obj=meter_view,
        meter_type=meter.meter_type,
    )
    if request.method == 'POST' and form.validate():
        events = []
        if meter.is_customer_meter():
            if form.state.data != meter.config.state:
                event = Event.create(Event.TYPE_METER_STATE_CHANGED, obj=meter)
                meter.session.add(event)
                events.append(event)
            if form.tariff.data != meter.tariff:
                event = Event.create(Event.TYPE_METER_TARIFF_CHANGED, obj=meter)
                meter.session.add(event)
                events.append(event)
        if not config['HEROKU']:
            for event in events:
                event.process()
        form.save(meter_view)
        return form.notify_and_redirect(meter_view)

    return form.render(meter=meter,
                       meter_type=meter.meter_type,
                       ground=meter.ground)


@meter.route("/meter/<string:meter_serial>/")
@verify_permission('meter', 'view')
def view(meter_serial):
    """Meter base page."""
    meter = Meter.get_by_serial(meter_serial)
    if meter is None:
        abort(http.client.NOT_FOUND)
    user = get_current_user()
    if meter.is_totalizer_meter() and user.is_vendor():
        abort(http.client.FORBIDDEN)
    has_accounts = SalesAccount.get_accounts_by_user_ground(
        user,
        meter.ground,
    ).count() > 0
    meter_power_limit = meter.continuous_current_limit * parameters.NOMINAL_VOLTAGE
    load_limit_capped = (
        meter.is_customer_meter() and meter_power_limit < meter.tariff.get_current_load_limit() and (
            meter_power_limit == meter.system_info.current_user_power_limit))
    return render_template(
        'meter-view.html',
        meter=meter,
        meter_type=meter.meter_type,
        has_accounts=has_accounts,
        load_limit_capped=load_limit_capped
    )


@meter.route("/meter/<string:meter_serial>/transactions.json")
@verify_permission('meter', 'view')
def transactions(meter_serial):
    """User transactions data."""
    meter = Meter.get_by_serial(meter_serial)
    if meter is None or meter.is_totalizer_meter():
        abort(http.client.NOT_FOUND)
    user = get_current_user()
    filter_args = parse_datatables_transaction_args()
    transaction_views = TransactionView.get_transaction_view(meter=meter,
                                                             user=user,
                                                             order=filter_args['order']['column_name'],
                                                             ascending=filter_args['order']['dir'] == 'asc',
                                                             offset=filter_args['start'],
                                                             limit=filter_args['length'],
                                                             query_string=filter_args['search']['value'])
    return jsonify(**format_transaction_views(transaction_views, filter_args['draw']))


@meter.route("/meter/<string:meter_serial>/transactions.csv")
@verify_permission('meter', 'view')
def transactions_export(meter_serial):
    """User transactions data."""
    meter = Meter.get_by_serial(meter_serial)
    if meter is None or meter.is_totalizer_meter():
        abort(http.client.NOT_FOUND)
    user = get_current_user()
    filter_args = parse_datatables_transaction_args()
    transaction_views = TransactionView.get_transaction_view(meter=meter,
                                                             user=user,
                                                             order=filter_args['order']['column_name'],
                                                             ascending=filter_args['order']['dir'] == 'asc',
                                                             offset=None,
                                                             limit=None,
                                                             query_string=filter_args['search']['value'])
    response = Response(iter_transaction_csv(transaction_views), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=transactions.csv'
    return response


@meter.route("/meter/<string:meter_serial>/messages.csv")
@verify_permission('meter', 'view')
def messages_export(meter_serial):
    """Ground messages data."""
    meter = Meter.get_by_serial(meter_serial)
    if meter is None or meter.is_totalizer_meter():
        abort(http.client.NOT_FOUND)
    user = get_current_user()
    filter_args = parse_datables_message_args()
    query = SMSMessage.get_messages_view(meter=meter,
                                         user=user,
                                         order=filter_args['order']['column_name'],
                                         ascending=filter_args['order']['dir'] == 'asc',
                                         offset=None,
                                         limit=None,
                                         query_string=filter_args['search']['value'])
    results = sql.session.execute(query)
    response = Response(iter_message_csv(results), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=messages.csv'
    return response


@meter.route("/meter/<string:meter_serial>/messages.json")
@verify_permission('meter', 'view')
def messages(meter_serial):
    """User messages data."""
    meter = Meter.get_by_serial(meter_serial)
    if meter is None or meter.is_totalizer_meter():
        abort(http.client.NOT_FOUND)
    user = get_current_user()
    filter_args = parse_datables_message_args()
    query = SMSMessage.get_messages_view(meter=meter,
                                         user=user,
                                         order=filter_args['order']['column_name'],
                                         ascending=filter_args['order']['dir'] == 'asc',
                                         offset=filter_args['start'],
                                         limit=filter_args['length'],
                                         query_string=filter_args['search']['value'])
    results = sql.session.execute(query)
    return jsonify(**format_messages(results, filter_args['draw']))


#
#    METER VIEWS
#

@meter.route("/meter/<string:meter_serial>/set-state",
             methods=['POST'])
@verify_permission('meter', 'edit', http.client.FORBIDDEN)
def set_state(meter_serial):
    """Turn the meter on."""
    state = request.get_json().get('state')
    try:
        config_state = Meter.state_from_string(state)
    except ValueError:
        abort(http.client.BAD_REQUEST)

    meter = Meter.get_by_serial(meter_serial)
    if meter is None:
        abort(http.client.NOT_FOUND)
    sql.session.add(meter)
    meter.set_state(config_state)
    sql.session.commit()

    return jsonify(state_value=meter.state_value,
                   state_text=str(meter.state_text))


@meter.route("/meter/<string:meter_serial>/verify-phone-number",
             methods=['PUT'])
@verify_permission('meter', 'edit')
def verify_phone_number(meter_serial):
    """Verify the customer's phone number."""
    meter = Meter.get_by_serial(meter_serial)
    if meter is None or meter.is_totalizer_meter():
        abort(http.client.NOT_FOUND)
    message = meter.customer.send_phone_number_verification()
    sql.session.add(message)
    sql.session.commit()
    return jsonify(phone_number=message.phone_number)


@meter.route("/meter/<string:meter_serial>/reset-meter")
def reset_meter(meter_serial):
    """
    Push the meter config to the meter.

    This will clear the meters error state (throttle error or protect) if one exists.
    """
    meter = Meter.get_by_serial(meter_serial)
    if meter is None:
        abort(http.client.NOT_FOUND)
    if meter.is_totalizer_meter():
        abort(http.client.FORBIDDEN)

    meter.reset_state()
    sql.session.commit()
    flash(_("Meter reset command queued"), "success")

    return redirect(
        url_for(
            'meter.view',
            meter_serial=meter.serial,
        )
    )


@meter.route("/meter/<string:meter_serial>/chart")
@verify_permission('meter', 'view')
def chart(meter_serial):
    """Edit chart parameters."""
    meter = Meter.get_by_serial(meter_serial)
    if meter is None:
        abort(http.client.NOT_FOUND)
    user = get_current_user()
    if meter.is_totalizer_meter() and user.is_vendor():
        abort(http.client.FORBIDDEN)
    exclude_fields = [
        'heartbeat_start',
        'heartbeat_end',
        'meter',
        'kilowatt_hours_period',
        'snapshot_id',
    ]
    if meter.is_totalizer_meter():
        exclude_fields.extend([
            "cost",
            "acct_credit",
            "acct_plan",
            "acct_debt",
            "rate",
            "tou_modifier"
        ])

    form = ChartForm(request.args, meta={'csrf': False})
    form.fields.choices = Reading.column_labels(exclude=exclude_fields)

    if not form.start.data:
        form.start.data = (
            datetime.datetime.utcnow().date() - datetime.timedelta(days=5)).strftime('%Y/%m/%d')
    if not form.end.data:
        form.end.data = datetime.datetime.utcnow().date().strftime('%Y/%m/%d')
    return form.render(meter=meter)


@meter.route("/meter/<string:meter_serial>/chart/data.<format>")
@verify_permission('meter', 'view')
def data_view(meter_serial, format):
    """Data for the charts."""
    import numpy  # lazy load numpy to avoid loading it into memory when not needed
    meter = Meter.get_by_serial(meter_serial)
    if meter is None:
        abort(http.client.NOT_FOUND)
    user = get_current_user()
    if meter.is_totalizer_meter() and user.is_vendor():
        abort(http.client.FORBIDDEN)
    start = dateutil.parser.parse(request.args.get('start')).date()
    end = dateutil.parser.parse(request.args.get('end')).date()
    group_by = request.args.get('group_by', None)
    group_by_function_name = request.args.get('group_by_function', 'sum')
    group_by_functions = {
        'sum': numpy.sum,
        'min': numpy.min,
        'avg': numpy.average,
        'max': numpy.max,
    }
    try:
        group_by_function = group_by_functions[group_by_function_name]
    except KeyError:
        logger.exception('invalid grouping function: %s' % group_by_function_name)
        abort(http.client.BAD_REQUEST)

    # the ending date should be inclusive, otherwise it is a little confusing in the UI
    end += datetime.timedelta(days=1)

    df = meter.get_dataframe(
        since=start,
        before=end,
        fields=request.args.getlist('fields'),
    )

    # localize the UTC datetimes from the DB, then convert them to local time for display in the UI.
    df = df.tz_localize(tzutc())
    df = df.tz_convert(tzlocal())

    if group_by in ['H', 'D', 'W', 'M']:
        df = df.resample(group_by).apply(group_by_function)
        # reindexing causes problems, but if there are gaps in the data,
        # not reindexing will make the charts look weird
        # idx = pandas.date_range(start=start, end=end, freq=group_by)
        # df = df.reindex(idx)
        df = df.fillna(0)

    if format == 'json':
        import vincent  # lazy load vincent to avoid loading it into memory when not needed
        chart_types = {
            'line': vincent.Line,
            'bar': vincent.Bar,
        }

        # no access from the UI, but leaving this here for uri access
        chart_type = request.args.get('chart_type', 'line')

        bar = chart_types[chart_type](df)

        # bar.axis_titles(x=chart.x, y=chart.y)
        bar.legend(title='Legend')
        # bar.name = 'thechart'
        # print bar.scales['x']
        # bar.scales['x'].type = 'utc'
        # bar.scales['x'].type = 'utc'
        # bar.scales['x'].nice = 'day'
        # bar.scales['x'].zero = True
        # if group_by == 'date':
        #    bar.scales['x'].nice = 'day'
        # bar.scales['x'].nice = 'hour'
        if chart_type == 'line':
            bar.scales['y'].zero = False
        return Response(bar.to_json(), mimetype='application/json')
    elif format == 'csv':
        strIO = io.BytesIO()
        df.to_csv(strIO, index_label='datetime')
        strIO.seek(0)
        return send_file(
            strIO,
            download_name="meter%s_data.csv" % (meter.serial),
            as_attachment=True,
        )
    else:
        abort(http.client.BAD_REQUEST)


def format_meter_view(results):
    """Format a meter view query result.

    Format a query result from a meter view and make it
    suitable for displaying in a JSON api.
    :param results: the query results
    :returns: an iterator of dictionaries
    :rtype: list[Dict]
    """
    rv = []
    for r in results:
        rv.append(dict(
            meter_serial=r.serial,
            meter_state=r.state,
            meter_active=r.active,
            meter_is_running_plan=r.is_running_plan,
            meter_plan_value=r.plan_value,
            meter_credit_value=r.credit_value,
            meter_debt_value=r.debt_value,
            meter_tags=', '.join(r.tags),
            tariff_name=r.tariff_name,
            tariff_plan_enabled=r.tariff_plan_enabled,
            customer_name=r.customer_name,
            customer_code=r.customer_code,
            customer_phone_number=r.customer_phone_number,
            customer_phone_number_verified=r.customer_phone_number_verified,
            address_street1=r.address_street1,
            address_street2=r.address_street2,
            address_city=r.address_city,
            address_state=r.address_state,
            address_coords=r.address_coords,
            ground_name=r.ground_name,
            ground_serial=r.ground_serial,
        ))
    return rv
