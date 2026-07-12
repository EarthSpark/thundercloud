# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Forms module for the ground web interface."""

from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from wtforms import ValidationError
from wtforms.fields import FormField, IntegerField, StringField, SubmitField

from sparkmeter.constants import MAX_SIGNED_INT
from sparkmeter.web.forms import BaseForm


class AddressForm(FlaskForm):
    """Address Form."""

    street1 = StringField(_("Street1"))
    street2 = StringField(_("Street2"))
    city = StringField(_("City"))
    state = StringField(_("State"))
    postalcode = StringField(_("Postal code"))
    country = StringField(_("Country"))
    coords = StringField(_("Coordinates"))


class GroundForm(BaseForm):
    """Ground Form."""

    redirect_url = "ground.index"
    template_filename = "ground-form.html"

    name = StringField(_("Name"))
    address = FormField(AddressForm)
    max_capacity = IntegerField(_("Max capacity"), default=1000)
    save_button = SubmitField(_("Save"))

    def validate_max_capacity(self, field):
        """Validate Max capacity field."""
        if field.data is None:
            raise ValidationError(_("The Ground must have a max capacity set."))
        if field.data > MAX_SIGNED_INT:
            raise ValidationError(
                _("Max capacity must be less than or equal to %(max_int)s.", max_int=MAX_SIGNED_INT)
            )
        if field.data < 0:
            raise ValidationError(_("Max capacity cannot be negative."))

    def notification_message(self, ground):
        """Build a message to be displayed when a ground is updated."""
        return _("Ground updated.")
