# -*- coding: utf-8 -*-
# Copyright © 2013-2019 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 customer views."""
import http.client
import json
import logging
import uuid

from flask import current_app, request, stream_with_context, url_for
from flask_security import roles_accepted
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import NoResultFound

from sparkmeter.api.apiviews0 import api, assert_one_of_params, check_param, get_params, success
from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.event.eventdomain import Event
from sparkmeter.exceptions import APIError, MeterError, TransactionError
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterdomain import Meter, MeterTag, MeterView
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.misc.phoneutils import format_phone_number, parse_phone_number
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.transaction.transactiondomain import Wallet
from sparkmeter.user.userutils import get_current_user

logger = logging.getLogger(__name__)


def _format_customer(meter_view, fetch_latest_reading=False):
    """Format a customer according to a query result

    :param meter_view: query result
    :type meter_view: MeterView

    :param fetch_latest_reading: whether or not the latest reading should be fetched/included
    :type fetch_latest_reading: bool

    :return: a formatted dictionary
    :rtype: dict
    """
    if meter_view.customer_phone_number:
        phone_number = parse_phone_number(meter_view.customer_phone_number)
        phone_number = format_phone_number(phone_number, format='E164')
    else:
        phone_number = None
    meter = sql.session.query(Meter).options(
        joinedload(Meter.system_info),
        joinedload(Meter.billing)
    ).get(meter_view.id)
    address_parts = [
        meter_view.address_street1,
        meter_view.address_street2,
        meter_view.address_city,
        meter_view.address_postalcode,
        meter_view.address_state,
        meter_view.address_country,
    ]

    meter_object = dict(
        active=meter_view.active,
        address=', '.join([p for p in address_parts if p]),
        street1=meter_view.address_street1,
        street2=meter_view.address_street2,
        city=meter_view.address_city,
        postalcode=meter_view.address_postalcode,
        state=meter_view.address_state,
        country=meter_view.address_country,
        coords=meter_view.address_coords,
        current_daily_energy=meter.current_daily_energy,
        current_tariff_name=meter_view.tariff_name,
        is_running_plan=meter_view.is_running_plan,
        last_config_datetime=meter.system_info.last_config_datetime,
        last_energy=meter_view.last_energy,
        last_energy_datetime=meter_view.last_energy_datetime,
        last_meter_state_code=meter_view.current_state,
        firmware=meter.system_info.firmware,
        bootloader=meter.system_info.bootloader,
        operating_mode=meter_view.state,
        plan_balance=meter_view.plan_value,
        serial=meter_view.serial,
        model=meter.model.name,
        total_cycle_energy=meter_view.total_cycle_energy,
        tags=meter_view.tags,
    )

    # only customer meters have billing info
    if meter.meter_type == Meter.TYPE_CUSTOMER:
        meter_billing_attr = dict(
            last_plan_expiration_date=meter.billing.last_plan_expiration_date,
            last_plan_payment_date=meter.billing.last_plan_payment_date,
            last_cycle_start=meter.billing.last_cycle_start,
        )
        meter_object.update(meter_billing_attr)

    if fetch_latest_reading:
        latest_reading = meter.get_latest_reading()
        if latest_reading:
            reading_object = _format_reading(latest_reading)
            meter_object['latest_reading'] = reading_object

    return dict(
        code=meter_view.customer_code,
        credit_balance=meter_view.credit_value,
        debt_balance=meter_view.debt_value,
        id=meter_view.customer_id,
        ground=dict(
            id=meter_view.ground_id,
            name=meter_view.ground_name,
        ),
        meters=[meter_object],
        name=meter_view.customer_name,
        phone_number=phone_number,
        phone_number_verified=meter_view.customer_phone_number_verified,
    )


def _update_customer(
        meter_view,
        active,
        name,
        code,
        phone_number,
        meter_tariff_name,
        operating_mode,
        address,
        events,
        coords,
        tags):
    # Meter active/hidden
    if active is not None:
        meter_view.active = active

    # Customer name
    if name is not None:
        meter_view.customer_name = name

    # Customer code
    if code is not None:
        existing_meter = Meter.get_by_customer_code(code)
        if existing_meter and existing_meter.id != meter_view.id:
            raise APIError("customer already exists with same code", status_code=http.client.LOCKED)
        meter_view.customer_code = code

    # Customer Phone number
    if phone_number is not None:
        number = format_phone_number(phone_number, format='E164')
        meter_view.customer_phone_number = number
        meter_view.customer_phone_number_verified = True

    # Tariff
    if meter_tariff_name is not None:
        try:
            tariff = Tariff.get_by_name(meter_tariff_name)
        except NoResultFound:
            raise APIError("no such tariff", status_code=http.client.NOT_FOUND)
        if events is not None and meter_view.id is not None and meter_view.tariff.id != tariff.id:
            event = Event.create(Event.TYPE_METER_TARIFF_CHANGED, obj=meter_view.meter)
            sql.session.add(event)
            events.append(event)
        meter_view.tariff = tariff

    # Operating mode
    if operating_mode is not None:
        try:
            state = Meter.state_from_string(operating_mode)
        except ValueError:
            raise APIError("invalid operating_mode, must be on/off or auto")
        if events is not None and meter_view.id is not None and meter_view.state != state:
            event = Event.create(Event.TYPE_METER_STATE_CHANGED, obj=meter_view.meter)
            sql.session.add(event)
            events.append(event)
        meter_view.state = state

    # Address
    if isinstance(address, dict):
        meter_view.address_street1 = address['street1']
        meter_view.address_street2 = address['street2']
        meter_view.address_city = address['city']
        meter_view.address_state = address['state']
        meter_view.address_postalcode = address['postalcode']
        meter_view.address_country = address['country']
    elif address is not None:
        meter_view.address_street1 = address
    if coords is not None:
        meter_view.address_coords = coords

    if tags is not None:
        _update_tags(meter_view, tags)


def _update_tags(meter_view, tags):
    """Update tags field for a meter.

    Any existing tags not included in the meter's tags will be removed,
    while those present will remain unchanged. New tags will be added.
    In the event an empty tags array is submitted, all tags will be cleared.

    :param meter_view: a meter view for the meter in hand
    :type meter_view: MeterView

    :param tags: A list of tags to be associated with the meter
    :param tags: list
    """
    _validate_tags(tags)
    tags = [_encode_tag(tag) for tag in tags]

    if meter_view.meter:
        meter_tags = [] if meter_view.tags is None else meter_view.tags
        added_tags = _diff_tagsets(tags, meter_tags)
        removed_tags = _diff_tagsets(meter_tags, tags)
        for tag in added_tags:
            MeterTag.add(tag, meter_view.meter)
        for tag in removed_tags:
            MeterTag.remove(tag, meter_view.meter)
    else:
        meter_view.tags = tags


def _get_address(params):
    """Get the appropriate address from a list of parameters.

    :returns: A string if an address singleton, a dict of address fields if all are present, or None.
    """
    address_fields = frozenset(['street1', 'street2', 'city', 'state', 'postalcode', 'country'])
    common = set(params.keys()) & address_fields
    if len(common) == len(address_fields):
        return {
            field_name: check_param(params, field_name, str, allow_empty=True)
            for field_name in address_fields
        }
    elif common:
        raise APIError('must specify all address fields. Missing: {}'.format(
            ', '.join(sorted(address_fields - common))))
    elif 'address' in params:
        if isinstance(params['address'], str) or params['address'] is None:
            return params['address']
        raise APIError('The address field must be a string')
    return None


def _validate_tags(tags):
    """Validates that tags are strings that don't include commas or spaces.

    :param tags: list of tags
    :type tags: list
    :raises APIError: This error is raise case one or more tags are invalid
    """
    invalid_tags = []
    for tag in tags:
        if (
            not isinstance(tag, str)
            or ',' in tag
            or ' ' in tag
            or tag == ''
        ):
            invalid_tags.append(tag)
    if invalid_tags:
        error_message = "the tags '{}' are invalid. ".format(", ".join([str(tag) for tag in invalid_tags]))\
            + "Tags must be strings, and cannot contain commas or spaces."

        raise APIError(error_message)


def _encode_tag(tag):
    """Encode a tag by escaping control characters to their backslash representations.

    Control characters (tab, newline, etc.) are replaced with their escaped
    form (\\t, \\n, etc.) for safe storage. Existing backslashes are preserved as-is.

    :param tag: a tag
    :type tag: str
    :returns: an escaped tag string
    :rtype: str
    """
    replacements = {
        chr(7): r'\a',    # BELL
        chr(8): r'\b',    # BACKSPACE
        '\t': r'\t',
        '\r': r'\r',
        '\n': r'\n',
        '\f': r'\f',
    }
    for char, escaped in replacements.items():
        tag = tag.replace(char, escaped)
    return tag


def _decode_tag(tag):
    """Decode an encoded tag back to its original form.

    Reverses the escaping done by _encode_tag.

    :param tag: an encoded tag
    :type tag: str
    :rtype: str
    """
    return json.loads('"{}"'.format(tag))


def _diff_tagsets(tagset1, tagset2):
    """Returns elements which exist in the first set only.

    :param tagset1: The first tagset is a list of tags
    :param tagset1: list

    :param tagset2: The second tagset is a list of tags
    :param tagset2: list

    :returns: A list containing of tags that exist in the first set only
    :rtype: list
    """
    return list(set(tagset1) - set(tagset2))


def _format_reading(reading):
    """Format a reading

    :param reading: A reading object
    :type reading: Reading

    :returns: A dictionary of selected values to be returned in an API response describing a reading
    :rtype: dict
    """
    if reading:
        return dict(
            timestamp=reading.heartbeat_end,
            min_voltage=reading.voltage_min,
            max_voltage=reading.voltage_max,
            avg_voltage=reading.voltage_avg,
            min_current=reading.current_min,
            max_current=reading.current_max,
            avg_current=reading.current_avg,
            avg_true_power=reading.true_power_avg,
            avg_power_factor=reading.power_factor_avg,
            avg_apparent_power=reading.apparent_power_avg,
            instantaneous_true_power=reading.true_power_inst,
            uptime=reading.uptime,
            kilowatt_hours=reading.kilowatt_hours,
            rate=reading.rate,
            tou_modifier=reading.tou_modifier,
            cost=reading.cost,
            frequency=reading.frequency
        )


@api.route('/customer/', methods=['POST'])
@roles_accepted('api')
def customer_add():
    """Create customer."""
    params = get_params()

    # Ground serial
    ground_serial = check_param(
        params, 'ground_serial', required=False)
    if ground_serial is not None:
        ground = Ground.get_by_serial(ground_serial)
    else:
        grounds = Ground.get_all()
        if len(grounds) == 1:
            ground = grounds[0]
        else:
            raise APIError("missing ground")
    if ground is None:
        raise APIError("no such ground", status_code=http.client.NOT_FOUND)

    # Serial & Code
    serial = check_param(
        params, 'serial', required=True)
    try:
        meter_view = MeterView.create_meter(meter_type=Meter.TYPE_CUSTOMER,
                                            ground=ground,
                                            serial=serial)
    except MeterError as e:
        if e.code == MeterError.INVALID_SERIAL:
            raise APIError("Invalid meter serial, must look like 'SMXXX-XX-XXXXXXXX'.")
        elif e.code == MeterError.DUPLICATE_SERIAL:
            raise APIError("customer already exists with same meter serial",
                           status_code=http.client.LOCKED)
        else:
            raise APIError("server error: {}".format(e.code))

    address = _get_address(params)

    _update_customer(
        meter_view,
        # Meters should be created active, thus not requiring any additional
        # actions via the normal Web UI.
        active=True,
        name=check_param(
            params, 'name', required=False),
        code=check_param(
            params, 'code', str, required=False),
        phone_number=check_param(
            params, 'phone_number', parse_phone_number,
            name='phone number', required=False),
        meter_tariff_name=check_param(
            params, 'meter_tariff_name', required=True),
        operating_mode=check_param(
            params, 'operating_mode', default='off', required=False),
        address=address,
        events=None,
        coords=check_param(
            params, 'coords', str, required=False),
        tags=check_param(params, 'tags', list, required=False),
    )

    # Start credit balance
    meter_view.credit_value = check_param(
        params, 'starting_credit_balance', float,
        name='number', default=0.0, required=False)

    sql.session.add(meter_view)
    meter_view.finish_creation()
    sql.session.commit()

    r = success(customer_id=meter_view.customer_id)
    r.status_code = http.client.CREATED
    r.headers['Location'] = url_for('.customer_view',
                                    customer_id=str(meter_view.customer_id))
    return r


@api.route('/customers/<uuid:customer_id>', methods=['PUT'])
@roles_accepted('api')
def customer_edit(customer_id):
    """Edit Customer."""
    params = get_params()
    meter_view = MeterView.get_by_customer_id(customer_id)
    if meter_view is None:
        raise APIError("no such customer", status_code=http.client.NOT_FOUND)
    assert_one_of_params(
        params,
        ('active', 'name', 'code', 'phone_number', 'meter_tariff_name',
         'operating_mode', 'address', 'street1', 'street2', 'city', 'state',
         'postalcode', 'country', 'coords', 'tags'))
    events = []
    address = _get_address(params)

    _update_customer(
        meter_view,
        active=check_param(params, 'active', bool, required=False),
        name=check_param(
            params, 'name', required=False),
        code=check_param(
            params, 'code', str, required=False),
        phone_number=check_param(
            params, 'phone_number', parse_phone_number,
            name='phone number', required=False),
        meter_tariff_name=check_param(
            params, 'meter_tariff_name', required=False),
        operating_mode=check_param(
            params, 'operating_mode', required=False),
        address=address,
        events=events,
        coords=check_param(
            params, 'coords', str, required=False),
        tags=check_param(params, 'tags', list, required=False),
    )

    sql.session.add(meter_view)
    if not config['HEROKU']:
        for event in events:
            event.process()
    sql.session.commit()

    r = success(customer_id=customer_id)
    r.status_code = http.client.OK
    r.headers['Location'] = url_for('.customer_view',
                                    customer_id=str(customer_id))
    return r


@api.route('/customers')
@roles_accepted('api')
def customer_list():
    params = request.args.copy()
    customer_code = check_param(params, 'customer_code', required=False)
    customer_phone_number = check_param(params, 'customer_phone_number', required=False)
    meter_serial = check_param(params, 'meter_serial', required=False)
    meter_tariff_name = check_param(params, 'meter_tariff_name', required=False)
    ground_id = check_param(params, 'ground_id', required=False, param_type=uuid.UUID, name='uuid')
    ground_name = check_param(params, 'ground_name', required=False)
    customers_only = check_param(params, 'customers_only', param_type=bool, default=False)
    reading_details = check_param(params, 'reading_details', param_type=bool, required=False)

    for name in ['customer_code', 'customer_phone_number', 'meter_serial', 'meter_tariff_name',
                 'ground_id', 'ground_name', 'customers_only', 'reading_details']:
        params.pop(name, None)
    if params:
        raise APIError("unknown parameter(s): %r" % (list(params.keys()),))

    # Ground
    ground = None
    if ground_id or ground_name:
        if ground_id and ground_name:
            raise APIError("can't pass in both ground_id and ground_name")
        elif ground_id:
            ground = Ground.get_by_id(ground_id)
        else:
            ground = Ground.get_by_name(ground_name)
        if ground is None:
            raise APIError("no such ground", status_code=http.client.NOT_FOUND)

    # Meter
    meter = None
    if meter_serial:
        meter = Meter.get_by_serial(meter_serial)
        if meter is None:
            raise APIError("no such meter", status_code=http.client.NOT_FOUND)

    # Tariff
    tariff = None
    if meter_tariff_name:
        try:
            tariff = Tariff.get_by_name(meter_tariff_name)
        except NoResultFound:
            raise APIError("no such tariff", status_code=http.client.NOT_FOUND)

    meters = MeterView.get_view(customer_code=customer_code,
                                customer_phone_number=customer_phone_number,
                                meter=meter,
                                meter_type=Meter.TYPE_CUSTOMER if customers_only else None,
                                tariff=tariff,
                                ground=ground)
    total_meters = meters.count()
    if not total_meters:
        raise APIError("no such customer", status_code=http.client.NOT_FOUND)
    # The `direct_passthrough` kwarg is needed to bypass gzip compression so the response can be streamed to
    #  API clients. Otherwise, ThunderCloud will block until the generator exhausts itself, defeating the
    #  purpose of streaming this endpoint's response.
    return current_app.response_class(stream_with_context(iter_customers(meters, reading_details)),
                                      mimetype="application/json",
                                      direct_passthrough=True)


def iter_customers(meters, reading_details):
    """Build each customer record.

    :param meters: The customer meterview records.
    :params reading_details: `True` if reading details should be included, `False` otherwise.
    :returns: A generator customers
    """
    has_customers = False
    yield '{"customers":['
    for meter_view in meters:
        prefix = ",\n" if has_customers else "\n"
        yield prefix + json_dumps(_format_customer(meter_view, fetch_latest_reading=reading_details))
        has_customers = True
    yield '\n], "error": null, "status": "success"}'


@api.route('/customers/<uuid:customer_id>')
@roles_accepted('api')
def customer_view(customer_id):
    """Get Customer Info."""
    params = request.args
    reading_details = check_param(params, 'reading_details', param_type=bool, required=False, default=False)
    customer = MeterView.get_by_customer_id(customer_id)
    if customer is None:
        raise APIError("no such customer", status_code=http.client.NOT_FOUND)
    return success(customer=_format_customer(customer, fetch_latest_reading=reading_details))


@api.route('/customer/<string:customer_code>')
@roles_accepted('api')
def customer_code_view(customer_code):
    """Get Customer Info."""
    params = request.args.copy()
    reading_details = check_param(params, 'reading_details', param_type=bool, required=False, default=False)
    customers = []

    for meter_view in MeterView.get_view(customer_code=customer_code):
        customers.append(_format_customer(meter_view, fetch_latest_reading=reading_details))
    if not customers:
        raise APIError("no such customer", status_code=http.client.NOT_FOUND)
    return success(customers=customers)


@api.route('/customers/<uuid:customer_id>/wallet/<string:wallet_type>/zero-balance', methods=['POST'])
@roles_accepted('api')
def zero_customer_wallet(customer_id, wallet_type):
    """Zero the balance of the specified customer wallet.
    ---
    parameters:
      - name: customer_id
        in: path
        description: The system ID for the customer
        required: true
        schema:
          type: string
          format: uuid
      - name: wallet_type
        in: path
        description: The name of the wallet to zero
        required: true
        schema:
          type: string
          enum: ['credit', 'debt', 'plan']
    post:
      summary: zero the balance of the wallet
      description: >
        This call requests that the specified customer wallet balance be
        zeroed. When processed, a transaction will be applied to the meter to
        negate the wallet balance.


        _Typical use cases:_

        * Provisioning a meter for a new customer.

        * Resetting a customer after a trial period ends.
      responses:
        201:
          description: the ID of the created zeroing event
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ZeroResponseModel'
              example:
                error: null
                status: success
                event_id: e2b94357-4b34-4871-86ef-51745a6247d4
        400:
          description: Bad request
        404:
          description: Customer not found
    """
    user = get_current_user()
    try:
        SalesAccount.get_system().check_can_sell_from(user)
    except TransactionError as e:
        raise APIError(e.code + '-' + e.message)
    customer = MeterView.get_by_customer_id(customer_id)
    if customer is None:
        raise APIError("no such customer", status_code=http.client.NOT_FOUND)
    if wallet_type not in Wallet.TYPES:
        raise APIError("invalid wallet type {}, must be one of: {}".format(
            wallet_type, ", ".join(Wallet.TYPES)))
    wallet = customer.meter.get_wallet(wallet_type)
    event = wallet.request_zero()
    sql.session.commit()
    r = success(event_id=event.id)
    r.status_code = http.client.CREATED
    return r


@api.route('/customers/<uuid:customer_id>/reset-meter', methods=['POST'])
@roles_accepted('api')
def reset_meter(customer_id):
    """
    Reset meter state.

    This will clear the meters error state (throttle error or protect) if one exists.
    """
    customer = MeterView.get_by_customer_id(customer_id)
    if customer is None:
        raise APIError("no such customer", status_code=http.client.NOT_FOUND)

    meter = customer.meter
    if not meter.is_customer_meter():
        raise APIError("invalid meter type. Only customer meters can be reset",
                       status_code=http.client.FORBIDDEN)

    meter.reset_state()
    sql.session.commit()

    return success()


# These are OpenAPI docs for assorted model objects. Once we pick a doc framework to use, they should
#   be integrated.
"""
components:
  schemas:
    ResponseModel:
      type: object
      required:
        - error
        - status
      properties:
        error:
          type: string
          nullable: true
          description: an optional error message
        status:
          type: string
          description: whether or not the request was successful
          enum: ['success', 'error']
    ZeroResponseModel:
      type: object
      description: a successful wallet zeroing request was submitted
      allOf:
        - $ref: '#/components/schemas/ResponseModel'
        - type: object
          required:
            - event_id
          properties:
            event_id:
              type: string
              format: uuid
              description: the system ID of the event object
      required:
        - id
"""
