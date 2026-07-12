# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Tariff forms."""

from flask_babel import lazy_gettext as _
from wtforms.fields import (
    BooleanField,
    FloatField,
    HiddenField,
    IntegerField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, NumberRange

from sparkmeter.misc.jsonutils import json_loads
from sparkmeter.web.fields import HiddenIdField
from sparkmeter.web.forms import BaseForm


class HiddenJSONField(HiddenField):
    """
    A JSON field that is not rendered in form.
    """

    def process_formdata(self, valuelist):
        """Don't process any data from the user."""
        if valuelist:
            self.data = json_loads(valuelist[0])
        else:
            self.data = []

    def populate_obj(self, obj, name):
        """Don't populate the object with form data."""
        setattr(obj, name, self.data)


class TariffFormBase(BaseForm):
    """Tariff Base Form."""

    template_filename = "tariff-form.html"

    #: we need to access the id to be able to create blockrate/tou objects
    id = HiddenIdField()

    #: Table of blockrates, in JSON, constructed manually in HTML
    blockrates = HiddenJSONField()

    #: Table of TOUs, in JSON, constructed manually in HTML
    tous = HiddenJSONField()

    #: If TOU should be used, constructed manually in HTML
    tou_enabled = BooleanField(_("Time of Use (TOU) Pricing"))

    #: name of the tariff
    name = StringField(
        _("Name"),
        [DataRequired(_("You must enter a tariff name"))],
        default="",
        description=_("The name of this tariff"),
    )

    #: if a monthly plan should be enabled
    plan_enabled = BooleanField(
        _("Plan"),
        default=False,
        description=_(
            "Turning on a Plan allows the utility to charge customers "
            "a minimum monthly fee for electricity to be used during the "
            "current period of time. This charge may include a fixed fee and a "
            "minimum spend on energy consumption. A plan automatically renews "
            "at the start day every month (if monthly) or at the start of the "
            "next day (if daily) if the meter is in On mode, or in "
            "Auto and the customer has enough credits to pay for the full "
            "plan (fixed fee + minimum spend). Payment for consumption of "
            "electricity during the current plan period is charged from the "
            "Plan balance at the tariff rate until the balance "
            "reaches zero. Any consumption of electricity in the current "
            "period beyond this is charged from pre-pay credits that may have "
            "been purchased by the customer during the period. At the end of "
            "the period, a new Plan balance is automatically filled "
            "for customers who have more pre-pay credit in their account "
            "than the Plan minimum spend + fixed fee."
        ),
    )

    plan_duration_and_start_day = SelectField(
        _("Plan Duration and Start Day"),
        choices=[("1d1", "1 day")]
        + [("1m{}".format(i), "1 month, starting day {}".format(i)) for i in range(1, 29)],
        default="1m1",
        description=_(
            "The plan duration and start day defines the duration of the billing "
            "cycle, and what day of month the billing cycle will reset for this "
            "tariff. The block rate calculation resets on this day, as well as "
            "the monthly plan if a plan is enabled."
        ),
    )

    #: price of the current plan, eg credits per plan duration (month)
    plan_price = FloatField(
        _("Plan Minimum Spend"),
        [NumberRange(min=0)],
        default=0,
        description=_(
            "The minimum spend is transferred from the customer's credit "
            "wallet to the plan when the plan is purchased and is used to pay "
            "for electricity consumption at the tariff price until the plan "
            "balance reaches zero or its expiration date is reached."
        ),
    )

    #: fixed fee required to purchase the plan
    plan_fixed_fee = FloatField(
        _("Plan Fixed Fee"),
        [NumberRange(min=0)],
        default=0,
        description=_(
            "The fixed fee is deducted from the customer's credits wallet "
            "when the plan is purchased and is not converted to electricity."
        ),
    )

    #: Kind of tariff, flat/scheduled, constructed manually in HTML
    load_limit_type = RadioField(
        _("Load Limit Type"), default="flat", choices=[("flat", _("Flat")), ("scheduled", _("Scheduled"))]
    )

    #: flat load limit, in watts. 4800W is 20A/240V, which is out current hardware capacity
    flat_load_limit = IntegerField(
        _("Load Limit"), [NumberRange(min=1, max=4800, message=_("Must be higher than 0"))], default=0
    )

    #: Table of Load Limits, in JSON, constructed manually in HTML
    load_limits = HiddenJSONField()

    #: Flat fee, constructed manually in HTML
    flat_price = FloatField(_("Flat Rate"), default=0.0)

    #: Kind of tariff, flat/blockrate, constructed manually in HTML
    tariff_type = RadioField(
        _("Tariff Type"), default="flat", choices=[("flat", _("Flat rate")), ("blockrate", _("Block rate"))]
    )

    #: Low balance threshold
    low_balance_threshold = FloatField(
        _("Warning On Low Balance"),
        default=0.0,
        description=_("An alert can be sent if available credits go under this threshold."),
    )

    #: If daily_energy_limit_enabled should be used, constructed manually in HTML
    daily_energy_limit_enabled = BooleanField(_("Daily Energy Limit"))

    #: the hour in local time that the daily energy limit resets
    daily_energy_limit_reset_hour = SelectField(
        _("Daily Energy Limit Reset Hour"),
        default=0,
        choices=[(str(i), "{:02d}:00".format(i)) for i in range(24)],
        description=_(
            "The Daily Energy Limit Reset Hour defines when the counter will reset "
            "for this meter's Daily Energy Limit"
        ),
    )

    #: the number of kwh that can be consumed during the daily period
    daily_energy_limit_value = FloatField(
        _("Daily Energy Limit"),
        default=0.0,
        description=_("The maximum amount of energy that can be consumed in a day."),
    )


class TariffForm(TariffFormBase):
    """Tariff Form."""

    save_button = SubmitField(_("Save"))
