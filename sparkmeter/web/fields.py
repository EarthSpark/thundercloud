# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Contains custom WTForms fields."""

from wtforms.fields import HiddenField, SelectField, StringField

from sparkmeter.config.configdict import config
from sparkmeter.misc.phoneutils import list_country_codes
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.widgets import ReadOnlyTextInput


class HiddenIdField(HiddenField):

    """Shows an hidden id field, that must be stored as None instead of ""."""

    def process_formdata(self, valuelist):
        """Override HiddenField.process_formdata."""
        if valuelist:
            if valuelist[0] != "":
                self.data = valuelist[0]
            else:
                self.data = config['DEFAULT_PHONE_COUNTRY_CODE']


class ReadOnlyStringField(StringField):

    """
    Read-only String Field.

    This field presents itself as a readonly text input, but even if the user
    plays with the form data, the result will be discarded when populating
    the object.
    """

    widget = ReadOnlyTextInput()

    def process_formdata(self, valuelist):
        """Don't process any data from the user."""

    def populate_obj(self, obj, name):
        """Don't populate the object with form data."""


class CountryCodeField(SelectField):

    """
    Country code field.

    This field presents an select field where you can select a country
    phone code like +1 (United States).
    """

    @property
    def choices(self):
        """Iterate the list of country code."""
        return list_country_codes(locale=get_current_user().locale)

    @choices.setter
    def choices(self, value):
        """Noop setter."""
        #: Override setter as a NOOP, since the SelectField constructor will
        #: set the variable, but we don't care about it.
