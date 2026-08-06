# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""Forms module for the ground web interface."""

import collections.abc
import logging
from builtins import map, str

from flask.helpers import flash, url_for
from flask.templating import render_template
from flask.wrappers import Response
from flask_wtf import FlaskForm
from werkzeug.utils import redirect
from wtforms import Form
from wtforms.fields import BooleanField, FieldList, FormField

from sparkmeter.database.alchemy import sql
from sparkmeter.exceptions import InvalidData
from sparkmeter.misc.jsonutils import json_dumps

logger = logging.getLogger("forms")
BooleanField.false_values = BooleanField.false_values + (False,)  # needed for JSON deserialization


# MultiDict and from_json code adapted from wtforms-json: https://github.com/kvesteri/wtforms-json/
class MultiDict(dict):  # pragma: nocoverage
    """A WTForms dict object."""

    def getlist(self, key):
        """Get the values of a key as a list."""
        val = self[key]
        if not isinstance(val, list):
            val = [val]
        return val

    def getall(self, key):
        """Get all values associated with a key as a list."""
        return [self[key]]


def set_form_errors_header(response, form):
    """Attach a form's validation errors to a response as ``X-Form-Errors``.

    This is for development, and especially so that unittests can show a nicer
    error when there is a form error.

    Every error is coerced to ``str``: validators are free to store exception
    instances rather than messages, and those are not JSON serializable.

    :param response: the response to annotate.
    :param form: the form whose errors should be reported.
    :return: the same response, for convenience.
    :rtype: Response
    """
    if not form.errors:
        return response

    error_dict = {}
    for name, errors in list(form.errors.items()):
        error_dict[name] = list(map(str, errors))
    response.headers["X-Form-Errors"] = json_dumps(error_dict)
    logger.warning("{} errors: {} {}".format(type(form).__name__, error_dict, form.data))
    return response


class BaseForm(FlaskForm):
    """Base form, used by all other forms in the application."""

    #: URL redirect to after saving the form
    redirect_url = "index"

    #: Filename to use as template to render this form
    template_filename = None

    @classmethod
    def from_json(
        cls, formdata=None, obj=None, prefix="", data=None, meta=None, skip_unknown_keys=True, **kwargs
    ):  # pragma: nocoverage
        """Build the form object from a JSON dict."""
        if formdata:
            formdata = MultiDict(flatten_json(cls, formdata, skip_unknown_keys=skip_unknown_keys))
        return cls(formdata=formdata, obj=obj, prefix=prefix, data=data, meta=meta, **kwargs)

    def save(self, obj):
        """Save content of the form to a database.

        :param obj: the object to populate and commit.

        Popoulate the object from the form, save it to the database
        optionally flash a message and redirect to a page.
        """
        self.populate_obj(obj)
        sql.session.add(obj)
        sql.session.commit()

    def notify_message(self, obj, style="success"):
        """Notify the user with a message."""
        message = self.notification_message(obj)
        if message:
            flash(message, style)

    def redirect(self, obj):
        """Redirect to the url specified in the form."""
        return redirect(url_for(self.redirect_url))

    def notify_and_redirect(self, obj):
        """Display a message and redirect."""
        self.notify_message(obj)
        return self.redirect(obj)

    def notification_message(self, obj):
        """Save message hook.

        :param obj: the object that was just saved.
        :returns: a message to be displayed or ``None`` to skip displaying a message
        """

    def render(self, **context):
        """Render this form.

        This is similar to flask render_template(), but it has the additional
        feature of including form errors as a header, for development, especially
        so that unittests can show a nicer error when there is a form error.
        :param context: template context
        :return: the rendered form
        :rtype: Response
        """
        body = render_template(self.template_filename, form=self, **context)
        return set_form_errors_header(Response(body), self)


def flatten_json(form, json, parent_key="", separator="-", skip_unknown_keys=True):  # pragma: nocoverage
    """Flatten given JSON dict to cope with WTForms dict structure.

    :form form: WTForms Form object
    :param json: json to be converted into flat WTForms style dict
    :param parent_key: this argument is used internally be recursive calls
    :param separator: default separator
    :param skip_unknown_keys:
        if True unknown keys will be skipped, if False throws InvalidData
        exception whenever unknown key is encountered
    Examples::
        >>> flatten_json(MyForm, {'a': {'b': 'c'}})
        {'a-b': 'c'}
    """
    if not isinstance(json, collections.abc.Mapping):
        raise InvalidData("This function only accepts dict-like data structures.")

    items = []
    for key, value in json.items():
        try:
            unbound_field = getattr(form, key)
        except AttributeError:
            if skip_unknown_keys:
                continue
            else:
                raise InvalidData("Unknown field name '{}'.".format(key))

        try:
            field_class = unbound_field.field_class
        except AttributeError:
            if skip_unknown_keys:
                continue
            else:
                raise InvalidData("Key '{}' is not valid field class.".format(key))

        new_key = "{}{}{}".format(parent_key, separator, key) if parent_key else key
        if isinstance(value, collections.abc.MutableMapping):
            if issubclass(field_class, FormField):
                nested_form_class = unbound_field.bind(Form(), "").form_class
                items.extend(flatten_json(nested_form_class, value, new_key).items())
            else:
                items.append((new_key, value))
        elif isinstance(value, list):
            if issubclass(field_class, FieldList):
                nested_unbound_field = unbound_field.bind(Form(), "").unbound_field
                items.extend(flatten_json_list(nested_unbound_field, value, new_key, separator))
            else:
                items.append((new_key, value))
        else:
            items.append((new_key, value))
    return dict(items)


def flatten_json_list(field, json, parent_key="", separator="-"):  # pragma: nocoverage
    """Flatten given JSON list to a structure that WTForms expects."""
    items = []
    for i, item in enumerate(json):
        new_key = "{}{}{}".format(parent_key, separator, str(i))
        if isinstance(item, dict) and issubclass(getattr(field, "field_class"), FormField):
            nested_class = field.field_class(*field.args, **field.kwargs).bind(Form(), "").form_class
            items.extend(flatten_json(nested_class, item, new_key).items())
        else:
            items.append((new_key, item))
    return items
