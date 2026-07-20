# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Forms module for the meter web interface."""

from builtins import range

from flask.helpers import url_for
from flask_babel import lazy_gettext as _
from markupsafe import Markup
from werkzeug.utils import redirect
from wtforms.fields import BooleanField, SelectField, SelectMultipleField, StringField, SubmitField, TelField
from wtforms.validators import StopValidation, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

from sparkmeter.config.configdict import config
from sparkmeter.exceptions import MeterError
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterdomain import Meter, MeterTag, MeterView
from sparkmeter.misc.htmlutils import build_link
from sparkmeter.misc.phoneutils import (
    country_code_to_display_name,
    parse_country_national,
    parse_phone_number,
)
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.fields import CountryCodeField, ReadOnlyStringField
from sparkmeter.web.forms import BaseForm
from sparkmeter.web.widgets import TagsSelect


class MeterTagsField(QuerySelectMultipleField):
    """
    Tags field.

    This field presents an input field where you can select tags with
    auto-complete enabled.
    """

    widget = TagsSelect()

    def __init__(self, *args, **kwargs):
        """Create a new tags field."""
        kwargs["query_factory"] = lambda: MeterTag.query.order_by(MeterTag.name)
        kwargs["get_label"] = "name"
        self.form_tags = []
        self.data = []
        super(MeterTagsField, self).__init__(*args, **kwargs)

    def process_formdata(self, valuelist):
        """
        Save a reference to the raw formdata, which we will need later.

        QuerySelectField overwrites the meaning of self.data so we have to save
        the raw value ourselves.
        """
        self.form_tags = valuelist
        super(MeterTagsField, self).process_formdata(valuelist)

    def populate_obj(self, obj, name):
        """Populate the obj with tags."""
        obj.tags = list(self.form_tags)

    def iter_choices(self):
        """Yield tuples of (value, label, selected) for rendering selected options

        :returns: A generator of tuples each contains (value: str, label: str, selected: bool)
        """
        for pk, obj in self._get_object_list():
            yield (pk, self.get_label(obj), self.get_label(obj) in self.data, {})


class TariffSelectField(QuerySelectField):
    """Tariff select that reports the modal's add-new sentinel itself.

    ``QuerySelectField.pre_validate`` reports every primary key it cannot
    resolve as "Not a valid choice", and WTForms carries on running the
    validation chain after a ``pre_validate`` ``ValidationError``, so the
    sentinel would collect that message on top of the accurate one. Raising
    ``StopValidation`` instead carries the accurate message and ends the chain,
    leaving the field with exactly one error.
    """

    def pre_validate(self, form):
        """Reject the add-new sentinel before the choice lookup can mislabel it."""
        if self.raw_data and self.raw_data[0] == form.ADD_NEW_TARIFF:
            raise StopValidation(_("No tariff was created. Please select a tariff or add a new one."))
        super(TariffSelectField, self).pre_validate(form)


class BaseMeterForm(BaseForm):
    """Base Meter Form."""

    #: add or edit, override in subclass
    mode = None
    template_filename = "meter-form.html"

    #: Value of the tariff select's "add a new tariff" option. The option is
    #: added by the browser and opens the tariff modal instead of selecting a
    #: tariff, so it is never a valid submitted value.
    ADD_NEW_TARIFF = "__add_new__"

    tariff = TariffSelectField(
        _("Tariff"),
        query_factory=lambda: Tariff.query.filter().order_by("name"),
        get_label="name",
        allow_blank=True,
        blank_text=_("Select a tariff"),
    )
    customer_name = StringField(_("Name"), default="new customer")
    customer_code = StringField(_("Code"))
    customer_country_code = CountryCodeField(_("Country code"), default=config["DEFAULT_PHONE_COUNTRY_CODE"])
    customer_national_number = TelField(_("Phone Number"), default="")
    active = BooleanField(_("Active"), default=True)
    tags = MeterTagsField(
        _("Tags"),
        description=(
            _("List of tags for this meter, could mean anything, for instance a geographical location")
        ),
    )
    state = SelectField(
        _("State"),
        choices=[
            (0, _("Off")),
            (1, _("On")),
            (2, _("Auto")),
        ],
        coerce=int,
    )
    subnet = SelectField(
        _("Subnet"),
        default=255,
        choices=[(i, i) for i in range(1, 256)],
        coerce=int,
    )
    address_street1 = StringField(_("Street1"))
    address_street2 = StringField(_("Street2"))
    address_city = StringField(_("City"))
    address_state = StringField(_("State"))
    address_postalcode = StringField(_("Postal code"))
    address_country = StringField(_("Country"))
    address_coords = StringField(_("Coordinates"))

    save_button = SubmitField(_("Save"))

    def __init__(self, formdata, obj=None, meter_type=None):
        """Create a new meter form."""
        super(BaseMeterForm, self).__init__(formdata=formdata, obj=obj)
        self.meter_type = meter_type
        self.customer = getattr(obj, "customer", None)
        self.view = obj

        if meter_type == Meter.TYPE_TOTALIZER:
            del self["customer_name"]
            del self["customer_code"]
            del self["customer_country_code"]
            del self["customer_national_number"]
            del self["state"]
            del self["tariff"]

    def validate_customer_national_number(self, field):
        """Validate the national number part of the form."""
        if not field.data:
            return
        try:
            parse_phone_number(field.data, self.customer_country_code.data)
        except ValueError:
            country = country_code_to_display_name(get_current_user().locale, self.customer_country_code.data)
            raise ValidationError(
                _(
                    "%(number)s is not a valid national phone number for %(country)s",
                    number=field.data,
                    country=country,
                )
            )

    def validate_tariff(self, field):
        """Require a tariff with a clear validation message.

        The field only exists on customer meters; ``__init__`` deletes it for
        totalizers. The add-new sentinel never reaches here: the field's own
        ``pre_validate`` reports it and stops the chain.
        """
        if field.data is None:
            raise ValidationError(_("Please select a tariff or add a new one."))

    def save(self, view):
        """Save content of meter form to database."""
        if self.meter_type == Meter.TYPE_CUSTOMER and self.customer_national_number.data:
            new_number = parse_country_national(
                self.customer_country_code.data, self.customer_national_number.data
            )
            if view.customer and view.customer_phone_number != new_number:
                view.customer_phone_number_verified = False
        super(BaseMeterForm, self).save(view)

    def redirect(self, view):
        """Redirect after form submission."""
        return redirect(url_for("meter.view", meter_serial=view.serial))


class MeterAddForm(BaseMeterForm):
    """Meter Add Form."""

    mode = "add"

    serial = StringField(_("Serial"), filters=[lambda s: s and s.upper()])

    def validate_serial(self, field):
        """Validate the serial field of this form."""
        ground = Ground.get_default()
        try:
            MeterView.validate_serial(serial=field.data, ground=ground)
        except MeterError as e:
            if e.code == MeterError.INVALID_SERIAL:
                raise ValidationError(_('Invalid meter serial, must look like "SMXXX-XX-XXXXXXXX".'))
            elif e.code == MeterError.DUPLICATE_SERIAL:
                raise ValidationError(_("Meter serial %(serial)s already exists.", serial=field.data))
            elif e.code == MeterError.UNKNOWN_MODEL:
                raise ValidationError(
                    _(
                        "The serial is not associated with a known model. Verify "
                        'the serial, in the form "SMXXX-XX-XXXXXXXX", is '
                        "accurate."
                    )
                )
            else:
                raise ValidationError(_("Application error: %(message)s", message=e.message))

    def notification_message(self, view):
        """Build a message to be displayed when a meter is added."""
        # FIXME: Figure out what the right link UI is here:
        # a) Meter [SM15R-01-0000007B] created. (CURRENT BEHAVIOR)
        # b) [Meter SM15R-01-0000007B] created.
        # c) [Meter SM15R-01-0000007B created.]
        link = build_link(url_for("meter.view", meter_serial=self.serial.data), self.serial.data)
        return Markup(_("Meter %(link)s created.", link=link))


class MeterEditForm(BaseMeterForm):
    """Meter Edit Form."""

    mode = "edit"

    #: Meter read-only serial
    serial = ReadOnlyStringField(_("serial"))

    def notification_message(self, view):
        """Build a message to be displayed when a meter is updated."""
        link = build_link(url_for("meter.view", meter_serial=self.serial.data), self.serial.data)
        return Markup(_("Meter %(link)s updated.", link=link))


class ChartForm(BaseForm):
    """Chart Form."""

    template_filename = "meter-chart.html"

    start = StringField(_("Start Date"))
    end = StringField(_("End Date"))

    group_by = SelectField(
        _("Group By"),
        default="none",
        choices=[
            ("none", _("none")),
            ("H", _("hours")),
            ("D", _("days")),
            ("W", _("weeks")),
            ("M", _("months")),
        ],
    )
    group_by_function = SelectField(
        _("Group By Function"),
        default="sum",
        choices=[
            ("sum", _("Sum")),
            ("min", _("Minimum")),
            ("avg", _("Average")),
            ("max", _("Maximum")),
        ],
    )

    fields = SelectMultipleField(
        _("Fields"),
        default=["true_power_avg"],
        choices=[],
    )
