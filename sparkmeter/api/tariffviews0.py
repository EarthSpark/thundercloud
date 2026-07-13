# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 system views."""

import http.client
import json
import logging
import uuid

from flask import request
from flask_security import roles_accepted
from werkzeug.datastructures import MultiDict

from sparkmeter.api.apiviews0 import api, check_param, get_params, success
from sparkmeter.exceptions import APIError
from sparkmeter.tariff.tariffdomain import Tariff, parse_plan_duration_and_start_day_string
from sparkmeter.tariff.tariffform import TariffForm
from sparkmeter.tariff.tariffutils import add_tariff_from_form, update_tariff_from_form

logger = logging.getLogger(__name__)


def _format_tariff(tariff):
    tariff = dict(
        blockrates=tariff.blockrates,
        flat_price=tariff.flat_price,
        id=tariff.id,
        flat_load_limit=tariff.flat_load_limit,
        load_limits=tariff.load_limits,
        load_limit_type=tariff.load_limit_type,
        plan_duration="{}{}".format(tariff.plan_duration_span, tariff.plan_duration_unit),
        plan_enabled=tariff.plan_enabled,
        plan_price=tariff.plan_price,
        plan_fixed_fee=tariff.plan_fixed_fee,
        cycle_start_day_of_month=tariff.cycle_start_day_of_month,
        name=tariff.name,
        tariff_type=tariff.tariff_type,
        tou_enabled=tariff.tou_enabled,
        tous=tariff.tous,
        low_balance_threshold=tariff.low_balance_threshold,
        daily_energy_limit_enabled=tariff.daily_energy_limit_enabled,
        daily_energy_limit_reset_hour=tariff.daily_energy_limit_reset_hour,
        daily_energy_limit_value=tariff.daily_energy_limit_value,
    )
    return tariff


def _format_tariff_form_errors(form):
    """Get a nice dict of stringified error messages"""
    errors = {field: [str(msg) for msg in errors] for field, errors in form.errors.items()}
    if errors.get("plan_duration_and_start_day"):
        if errors["plan_duration_and_start_day"][0] == "Not a valid choice.":
            new_message = "Invalid 'cycle_start_day_of_month' or 'plan_duration'"
            try:
                parse_plan_duration_and_start_day_string(form.plan_duration_and_start_day.data)
            except ValueError as valerr:  # pragma: nocoverage
                new_message = str(valerr)
            errors["plan_duration_and_start_day"][0] = new_message
    return errors


def _transform_incoming_json_fields(params):
    """Stringify JSON fields so WTForms can handle them.

    :param params: The request parameters.
    :returns: The in-place transformed parameters.
    """
    for field in (
        "tous",
        "blockrates",
        "load_limits",
    ):
        if field in params:
            params[field] = json.dumps(params[field])
    plan_duration = params.pop("plan_duration", "1m")
    plan_start_day = params.get("cycle_start_day_of_month", 1)
    params["plan_duration_and_start_day"] = "{}{}".format(plan_duration, plan_start_day)


def _patch_tariff(
    form,
    name=None,
    cycle_start_day_of_month=None,
    load_limit_type=None,
    flat_load_limit=None,
    load_limits=None,
    low_balance_threshold=None,
    plan_enabled=None,
    plan_duration=None,
    plan_fixed_fee=None,
    plan_price=None,
    tariff_type=None,
    flat_price=None,
    blockrates=None,
    tou_enabled=None,
    tous=None,
    daily_energy_limit_enabled=None,
    daily_energy_limit_reset_hour=None,
    daily_energy_limit_value=None,
):
    """Partially update (and validate) a TariffForm.

    :param form: The form to patch
    :type form: TariffForm
    :returns: None
    """
    if name is not None:
        form.name.data = name

    if cycle_start_day_of_month is not None:
        duration = plan_duration or form.plan_duration_and_start_day.data
        if duration.startswith("1m"):
            form.plan_duration_and_start_day.data = "1m{}".format(cycle_start_day_of_month)
        elif duration.startswith("1d"):
            form.plan_duration_and_start_day.data = "1d1"
        else:
            raise ValueError("Invalid existing plan duration")

    if plan_duration is not None:
        if plan_duration == "1d":
            form.plan_duration_and_start_day.data = "1d1"
        else:
            form.plan_duration_and_start_day.data = "{}{}".format(
                plan_duration, form.plan_duration_and_start_day.data[2:]
            )

    if load_limit_type is not None and load_limit_type != form.load_limit_type.data:
        form.flat_load_limit.data = 0
        form.load_limits.data = []
        form.load_limit_type.data = load_limit_type

    if flat_load_limit is not None and form.load_limit_type.data == Tariff.LOAD_LIMIT_TYPE_FLAT:
        form.flat_load_limit.data = flat_load_limit

    if load_limits is not None and form.load_limit_type.data == Tariff.LOAD_LIMIT_TYPE_SCHEDULED:
        form.load_limits.data = load_limits

    if low_balance_threshold is not None:
        form.low_balance_threshold.data = low_balance_threshold

    if plan_enabled is not None and plan_enabled != form.plan_enabled.data:
        form.plan_fixed_fee.data = 0
        form.plan_price.data = 0
        form.plan_enabled.data = plan_enabled

    if form.plan_enabled.data:
        if plan_fixed_fee is not None:
            form.plan_fixed_fee.data = plan_fixed_fee

        if plan_price is not None:
            form.plan_price.data = plan_price

    if tariff_type is not None and tariff_type != form.tariff_type.data:
        form.flat_price.data = 0
        form.blockrates.data = []
        form.tariff_type.data = tariff_type

    if flat_price is not None and form.tariff_type.data == Tariff.TYPE_FLAT:
        form.flat_price.data = flat_price

    if blockrates is not None and form.tariff_type.data == Tariff.TYPE_BLOCKRATE:
        form.blockrates.data = blockrates

    if tou_enabled is not None and tou_enabled != form.tou_enabled.data:
        form.tous.data = []
        form.tou_enabled.data = tou_enabled

    if tous is not None and form.tou_enabled.data:
        form.tous.data = tous

    if daily_energy_limit_enabled is not None:
        if daily_energy_limit_enabled != form.daily_energy_limit_enabled.data:
            form.daily_energy_limit_reset_hour.data = 0
            form.daily_energy_limit_value.data = 0
            form.daily_energy_limit_enabled.data = daily_energy_limit_enabled

    if form.daily_energy_limit_enabled.data:
        if daily_energy_limit_reset_hour is not None:
            form.daily_energy_limit_reset_hour.data = daily_energy_limit_reset_hour

        if daily_energy_limit_value is not None:
            form.daily_energy_limit_value.data = daily_energy_limit_value


@api.route("/tariff/<string:tariff_id>", methods=["GET", "PUT", "PATCH"])
@roles_accepted("api", "operator")
def tariff_view(tariff_id):
    """Get or edit tariff info.
    ---
    parameters:
      - name: tariff_id
        in: path
        description: the system ID of the tariff
        required: true
        schema:
          type: string
          format: uuid
    get:
      summary: get a tariff
      responses:
        200:
          description: the tariff having the provided ID
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ExistingTariffModel'
        404:
          description: no tariff with the specified ID exists
    put:
      summary: update a tariff
      description: >
        This call updates a tariff with the values specified in the request. `name`
        must be unique to the system.
      requestBody:
        description: the updated tariff object
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/NewTariffModel'
      responses:
        200:
          description: the updated tariff
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ExistingTariffModel'
        400:
          description: Bad request
    """
    try:
        tariff = Tariff.get_by_id(uuid.UUID(tariff_id))
    except ValueError:
        tariff = None
    if tariff is None:
        raise APIError("no such tariff", status_code=http.client.NOT_FOUND)
    if request.method == "GET":
        return success(tariff=_format_tariff(tariff))
    params = get_params()
    if request.method == "PATCH":
        form = TariffForm(MultiDict(), obj=tariff)
        try:
            _patch_tariff(
                form,
                name=check_param(params, "name", default=None),
                cycle_start_day_of_month=check_param(params, "cycle_start_day_of_month", default=None),
                load_limit_type=check_param(params, "load_limit_type", default=None),
                flat_load_limit=check_param(params, "flat_load_limit", default=None),
                load_limits=check_param(params, "load_limits", default=None),
                low_balance_threshold=check_param(params, "low_balance_threshold", default=None),
                plan_enabled=check_param(params, "plan_enabled", default=None),
                plan_duration=check_param(params, "plan_duration", default=None),
                plan_fixed_fee=check_param(params, "plan_fixed_fee", default=None),
                plan_price=check_param(params, "plan_price", default=None),
                tariff_type=check_param(params, "tariff_type", default=None),
                flat_price=check_param(params, "flat_price", default=None),
                blockrates=check_param(params, "blockrates", default=None),
                tou_enabled=check_param(params, "tou_enabled", default=None),
                tous=check_param(params, "tous", default=None),
                daily_energy_limit_enabled=check_param(params, "daily_energy_limit_enabled", default=None),
                daily_energy_limit_reset_hour=check_param(
                    params, "daily_energy_limit_reset_hour", default=None
                ),
                daily_energy_limit_value=check_param(params, "daily_energy_limit_value", default=None),
            )
        except ValueError as valerr:
            raise APIError(
                "There was an error updating the tariff: {}".format(str(valerr)),
                status_code=http.client.BAD_REQUEST,
            )
    else:  # PUT
        _validate_dependent_fields(params)
        _transform_incoming_json_fields(params)
        for param_name in ("name", "cycle_start_day_of_month", "load_limit_type", "tariff_type"):
            check_param(params, param_name)
        form = TariffForm.from_json(params, obj=tariff)
    try:
        tariff = update_tariff_from_form(tariff, form)
    except ValueError as valerr:
        raise APIError(
            "There was an error updating the tariff: {}".format(str(valerr)),
            status_code=http.client.BAD_REQUEST,
        )
    if tariff:
        return success(tariff=_format_tariff(tariff))
    raise APIError(
        "There was an error updating the tariff.",
        status_code=http.client.BAD_REQUEST,
        payload=_format_tariff_form_errors(form),
    )


@api.route("/tariffs", methods=["GET", "POST"])
@roles_accepted("api", "operator")
def list_or_add_tariff():
    """Add a tariff
    ---
    get:
      summary: list all tariffs
      responses:
        200:
          description: all tariffs
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/ExistingTariffModel'
    post:
      summary: create a new tariff
      description: >
        This call creates a tariff in the SparkMeter system. `name` is a
        required field, and must be unique to the system.
      requestBody:
        description: tariff to add to the system
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/NewTariffModel'
            examples:
              'basic tariff':
                value:
                  name: Small Household Tariff
                  flat_load_limit: 150
                  plan_price: 0
                  cycle_start_day_of_month: 1
                  tariff_type: flat
                  flat_price: 4
                  tous: []
      responses:
        201:
          description: the newly created tariff
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ExistingTariffModel'
        400:
          description: Bad request
    """
    if request.method == "GET":
        tariffs = []
        for tariff in Tariff.get_all():
            tariffs.append(_format_tariff(tariff))
        return success(tariffs=tariffs)

    params = get_params()
    _validate_dependent_fields(params)
    _transform_incoming_json_fields(params)
    form = TariffForm.from_json(params)
    try:
        tariff = add_tariff_from_form(form)
    except ValueError as valerr:
        raise APIError(
            "There was an error updating the tariff: {}".format(str(valerr)),
            status_code=http.client.BAD_REQUEST,
        )
    if tariff:
        r = success(tariff=_format_tariff(tariff))
        r.status_code = http.client.CREATED
        return r
    raise APIError(
        "There was an error creating the tariff.",
        status_code=http.client.BAD_REQUEST,
        payload=_format_tariff_form_errors(form),
    )


def _validate_dependent_fields(params):
    """Raise errors if fields being updated don't have companion values."""
    for param_name in ("name", "cycle_start_day_of_month"):
        check_param(params, param_name)

    if check_param(params, "load_limit_type") == Tariff.LOAD_LIMIT_TYPE_FLAT:
        check_param(params, "flat_load_limit")
    elif check_param(params, "load_limit_type") == Tariff.LOAD_LIMIT_TYPE_SCHEDULED:
        check_param(params, "load_limits", param_type=list)

    if check_param(params, "tariff_type") == Tariff.TYPE_FLAT:
        check_param(params, "flat_price")
    elif check_param(params, "tariff_type") == Tariff.TYPE_BLOCKRATE:
        check_param(params, "blockrates", param_type=list)

    if check_param(params, "tou_enabled", param_type=bool, default=False):
        check_param(params, "tous", param_type=list)

    if check_param(params, "plan_enabled", param_type=bool, default=False):
        check_param(params, "plan_fixed_fee")
        check_param(params, "plan_price")

    if check_param(params, "daily_energy_limit_enabled", param_type=bool, default=False):
        check_param(params, "daily_energy_limit_reset_hour", param_type=int, strict=True)
        check_param(params, "daily_energy_limit_value", param_type=float)


# These are OpenAPI docs for the various model objects. Once we pick a doc framework to use, they should be
# integrated.
"""
components:
  schemas:
    NewTariffModel:
      type: object
      required:
        - name
      properties:
        name:
          type: string
          description: the name of the tariff
        cycle_start_day_of_month:
          type: number
          description: the day of the month on which the tariff cycle starts
        tariff_type:
          type: string
          enum:
            - flat
            - blockrate
        flat_price:
          type: number
          description: the unit price (per kWh)
        load_limit_type:
          type: string
          description: the load limit schedule for the tariff
          enum:
            - flat
            - scheduled
        low_balance_threshold:
          type: number
          description: the balance at which customers should be notified that their funds are running low
        tou_enabled:
          type: boolean
          description: whether time of use pricing should be enabled
        tous:
          type: array
          description: time of use period definitions
          items:
            type: object
            properties:
              start:
                type: string
                description: the start time, in HH:mm
              end:
                type: string
                description: the end time, in HH:mm
              value:
                type: number
                description: the pricing modifier (% of normal tariff)
        blockrates:
          type: array
          description: billing rate tiers
          items:
            type: object
            properties:
              lower:
                type: number
                description: the lower bound of power consumption (in kWh)
              upper:
                type: number
                description: the upper bound of power consumption (in kWh)
              value:
                type: number
                description: the unit price (per kWh)
        flat_load_limit:
          type: number
          description: the constant load limit for this tariff (in Watts)
        load_limits:
          type: array
          description: the load limit periods
          items:
            type: object
            properties:
              start:
                type: string
                description: the start time, in HH:mm
              end:
                type: string
                description: the end time, in HH:mm
              value:
                type: number
                description: the load limit (in Watts)
        monthly_plan_enabled:
          type: boolean
          description: whether or not a monthly plan should be in effect
        plan_fixed_fee:
          type: number
          description: >
            the amount deducted from the customer's credit wallet when the plan is purchased. This
            not converted to electricity.
        plan_price:
          type: number
          description: >
              the minimum spend transferred from the customer's credit wallet to the plan when the
              plan is purchased until the plan balance reaches zero or its expiration date is reached.
        daily_energy_limit_enabled:
          type: boolean
          description: whether daily energy limit should be enabled
        daily_energy_limit_reset_hour:
          type: number
          description: >
            The hour in localtime that the daily limit should reset.
        daily_energy_limit_value:
          type: number
          description: >
            The daily energy limit in kWh.
    ExistingTariffModel:
      description: a tariff that exists in the system
      allOf:
        - $ref: '#/components/schemas/NewTariffModel'
        - type: object
          properties:
            id:
              type: string
              format: uuid
              description: the system ID of the tariff object
      required:
        - id
"""
