# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Forms module for the sales account web interface."""

from flask.helpers import url_for
from flask_babel import lazy_gettext as _
from markupsafe import Markup
from wtforms.fields import BooleanField, FloatField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectField

from sparkmeter.ground.grounddomain import Ground
from sparkmeter.misc.htmlutils import build_link
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.web.forms import BaseForm


class BaseSalesAccountForm(BaseForm):
    """Base Sales Account Form."""

    template_filename = "sales-account-form.html"

    #: add or edit, override in subclass
    mode = None

    #: Url redirect to after saving the form
    redirect_url = "sales_account.index"

    #: Sales account name
    name = StringField(_("Name"), [DataRequired(_("You must enter a name."))])

    #: If sales account is visible in UI
    active = BooleanField(_("Active"), default=True)

    #: Markup for this sales account, only for restricted accounts
    markup = FloatField(
        _("Markup"),
        default=0.05,
        validators=[
            NumberRange(min=0.0, message=_("This field cannot be negative, it must be 0.0 or higher."))
        ],
    )

    #: The ground this sales account belongs to, only for restricted accounts
    ground = QuerySelectField(
        _("Ground"),
        query_factory=lambda: Ground.query.order_by(Ground.name),
        get_label="name",
    )

    #: Save button
    save_button = SubmitField(_("Save"))

    def __init__(self, account_type, *args, **kwargs):
        """Create a new user form."""
        super(BaseSalesAccountForm, self).__init__(*args, **kwargs)
        self.account = kwargs.get("obj")
        self.account_type = account_type

        if account_type == "global":
            del self["markup"]
            del self["ground"]

    def validate_name(self, field):
        """Validate the name field of this form."""
        if not SalesAccount.is_name_unique(field.data, skip=self.account):
            raise ValidationError(_("This name is already used, please enter another."))


class SalesAccountAddForm(BaseSalesAccountForm):
    """SalesAccount Add Form."""

    mode = "add"

    def notification_message(self, sales_account):
        """Build a message to be displayed when a sales_account is added."""
        link = build_link(
            url_for("sales_account.view", sales_account_id=sales_account.id), sales_account.name
        )
        if self.account_type == "global":
            return Markup(_("Global sales account %(link)s created.", link=link))
        else:
            return Markup(_("Restricted sales account %(link)s created.", link=link))


class SalesAccountEditForm(BaseSalesAccountForm):
    """SalesAccount Edit Form."""

    mode = "edit"

    def notification_message(self, sales_account):
        """Build a message to be displayed when a sales_account is updated."""
        link = build_link(
            url_for("sales_account.view", sales_account_id=sales_account.id), sales_account.name
        )
        if self.account_type == "global":
            return Markup(_("Global sales account %(link)s updated.", link=link))
        else:
            return Markup(_("Restricted sales account %(link)s updated.", link=link))
