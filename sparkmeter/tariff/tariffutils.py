"""Utility methods for tariffs and tariff accessories."""

from flask_babel import lazy_gettext as _
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from wtforms.validators import ValidationError

from sparkmeter.config.configdict import config
from sparkmeter.constants import MAX_SIGNED_INT
from sparkmeter.database.alchemy import sql
from sparkmeter.event.eventdomain import Event
from sparkmeter.tariff.tariffdomain import Tariff, parse_plan_duration_and_start_day_string


def add_tariff_from_form(form, tariff=None, session=None):
    """Add a tariff corresponding to the given form object.

    Validation errors are stored on the form object.

    :param form: The form from which the tariff should be created.
    :param tariff: An optional tariff object to validate. If not specified, a new one will be created.
    :param session: An optional session with which the resultant tariff should be associated.
    :returns: The created tariff, or None if there was a validation error.
    """
    session = session or sql.session
    if tariff is None:
        tariff = Tariff()
    try:
        tariff = validate_tariff(form, tariff)
        session.add(tariff)
        session.commit()
        return tariff
    except ValidationError:
        return None


def update_tariff_from_form(tariff, form, session=None):
    """Edit an existing tariff based on the data from a form object.

    Validation errors are stored on the form object.

    :param tariff: The tariff being updated.
    :param form: The form from which the tariff should be updated. This must have been
        initialized with the `obj` arg referencing the tariff object.
    :param session: An optional session with which the tariff update, and subsequent
        events, should be associated.
    :returns: The updated tariff.
    """
    session = session or sql.session
    old_power_limit = tariff.get_current_load_limit()
    tariff = add_tariff_from_form(form, tariff=tariff, session=session)
    if tariff is None:
        return None
    events = []
    # update the meters with this new power limit if we are not in heroku
    if old_power_limit != tariff.get_current_load_limit():
        event = Event.create(Event.TYPE_TARIFF_POWER_LIMIT_CHANGED, obj=tariff)
        session.add(event)
        events.append(event)

    if not config["HEROKU"]:
        for event in events:
            event.process()
    session.commit()
    return tariff


def validate_tariff(form, tariff):
    """Validate a tariff form.

    :param form: The form being validated
    :param tariff: The tariff object corresponding to the form
    :returns: The created tariff
    """
    # Unrelated, but simplifies call sites :-)
    # FIXME: Do not overwrite the id
    del form.id
    form.populate_obj(tariff)
    _validate_name(form, tariff)
    _validate_plan_duration_and_start_day(form)
    _validate_load_limits(form, tariff)
    _validate_plan(form)
    _validate_tariff_type(form, tariff)
    _validate_flat_price(form, tariff)
    _validate_tous(form, tariff)
    _validate_balance_threshold(form, tariff)
    _validate_daily_energy_limit(form, tariff)
    if form.errors:
        raise ValidationError(form.errors)
    return tariff


def _validate_name(form, tariff):
    """Validate the tariff's name field.

    :param form: The form being validated
    :param tariff: The tariff object corresponding to the form
    """
    form.name.errors = []
    if not tariff.name:
        form.name.errors.append(_("Please set a name for this tariff"))

    # Test for name uniqueness
    try:
        existing = Tariff.get_by_name(tariff.name, fail_on_multiple=True)
        if existing.id != tariff.id:  # If there's a tariff with this name that isn't this one...
            form.name.errors.append(_('A tariff with the name "{}" already exists'.format(tariff.name)))
    except MultipleResultsFound:
        form.name.errors.append(_('A tariff with the name "{}" already exists'.format(tariff.name)))
    except NoResultFound:
        pass


def _validate_plan_duration_and_start_day(form):
    """Validate the form's cycle start day of month field.

    :param form: The form being validated.
    """
    form.plan_duration_and_start_day.validate(form)
    try:
        parse_plan_duration_and_start_day_string(form.plan_duration_and_start_day.data)
    except ValueError:
        if not form.plan_duration_and_start_day.errors:  # pragma: nocover
            # Only append the generic error message if there isn't another validation error
            form.plan_duration_and_start_day.errors.append("Not a valid choice.")


def _validate_load_limits(form, tariff):
    """Validate the tariff's load limit fields

    :param form: The form being validated
    :param tariff: The tariff object corresponding to the form
    """
    if tariff.load_limit_type == Tariff.LOAD_LIMIT_TYPE_FLAT:
        if not tariff.flat_load_limit:
            form.flat_load_limit.errors = [_("Please enter a Load Limit for this tariff")]

        if tariff.flat_load_limit < 0:
            form.flat_load_limit.errors = [_("Load Limits cannot be negative")]

        if tariff.flat_load_limit > MAX_SIGNED_INT:
            form.flat_load_limit.errors = [
                _("Load Limit must be less than or equal to %(max_int)s", max_int=MAX_SIGNED_INT)
            ]
        # Be paraniod and reset scheduled load limits if we're using flat
        tariff.load_limits = []
    elif tariff.load_limit_type == Tariff.LOAD_LIMIT_TYPE_SCHEDULED:
        try:
            tariff.validate_load_limits()
        except ValueError as e:
            form.load_limits.errors = [e]

        if tariff.load_limits is not None:
            for i, load_limit in enumerate(tariff.load_limits[:]):
                if load_limit["end"] == "24:00":
                    tariff.load_limits[i]["end"] = "00:00"
                    break
    elif tariff.load_limit_type:
        form.load_limit_type.errors = [_("Must be one of: {}".format(", ".join(Tariff.LOAD_LIMIT_TYPES)))]


def _validate_plan(form):
    """Validate the form's plan fields.

    :param form: The form being validated
    :param tariff: The tariff object corresponding to the form
    """
    form.plan_price.validate(form)
    form.plan_fixed_fee.validate(form)


def _validate_tariff_type(form, tariff):
    """Validate the form's tariff type field.

    :param form: The form being validated
    :param tariff: The tariff object corresponding to the form
    """
    if tariff.tariff_type not in Tariff.TYPES:
        form.tariff_type.errors = [_("Must be one of: {}".format(", ".join(Tariff.TYPES)))]
        return
    if tariff.tariff_type == Tariff.TYPE_FLAT and not (tariff.flat_price):
        form.flat_price.errors = [_("Please set a Flat Rate")]

    if tariff.tariff_type == Tariff.TYPE_BLOCKRATE:
        try:
            tariff.validate_blockrates()
        except ValueError as e:
            form.blockrates.errors = [e]


def _validate_flat_price(form, tariff):
    """Validate the form's flat price field.

    :param form: The form being validated
    :param tariff: The tariff object corresponding to the form
    """
    if tariff.flat_price < 0:
        form.flat_price.errors = [_("Flat Rate cannot be negative")]


def _validate_tous(form, tariff):
    """Validate the tariff's TOU fields.

    :param form: The form being validated
    :param tariff: The tariff object corresponding to the form
    """
    if tariff.tous is not None:
        for i, tou in enumerate(tariff.tous[:]):
            if tou["end"] == "24:00":
                tariff.tous[i]["end"] = "00:00"
                break
    if tariff.tou_enabled:
        try:
            tariff.validate_tous()
        except ValueError as e:
            form.tous.errors = [e]


def _validate_balance_threshold(form, tariff):
    """Validate the tariffs balance threshold field.

    :param form: The form being validated
    :param tariff: The tariff object corresponding to the form
    """
    if form.low_balance_threshold.data is None:
        form.low_balance_threshold.errors = [_("Low Balance cannot be empty.")]
    elif tariff.low_balance_threshold < 0.0:
        form.low_balance_threshold.errors = [_("Low Balance must be higher or equals to 0.")]


def _validate_daily_energy_limit(form, tariff):
    """Validate the tariff's daily energy limit fields.

    :param form: The form being validated
    :param tariff: The tariff object corresponding to the form
    """
    if tariff.daily_energy_limit_enabled:
        if tariff.daily_energy_limit_value < 0:
            form.daily_energy_limit_value.errors = [
                _("Daily Energy Limit Value must be greater than or equal to 0")
            ]
        if int(tariff.daily_energy_limit_reset_hour) not in range(24):
            form.daily_energy_limit_reset_hour.errors = [
                _("Daily Energy Limit Reset Hour must be between 0 and 23 hours")
            ]
