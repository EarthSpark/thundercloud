# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Forms module for the user web interface."""

from flask.helpers import url_for
from flask_babel import lazy_gettext as _
from flask_security.utils import hash_password
from markupsafe import Markup
from wtforms.fields import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, ValidationError
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.misc.htmlutils import build_link
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.user.userdomain import User
from sparkmeter.web.fields import ReadOnlyStringField
from sparkmeter.web.forms import BaseForm

_locales = sorted(config.get('LOCALES')) or ['en_US']


class VendorField(QuerySelectField):

    """Vendor field that doesn't validate the choice selected."""

    def pre_validate(self, form):
        """Noop pre-validate method."""


class BaseUserForm(BaseForm):

    """Base User Form."""

    template_filename = 'user-form.html'

    #: add or edit, override in subclass
    mode = None

    #: Url redirect to after saving the form
    redirect_url = 'user.list'

    #: Username
    username = StringField(_('Username'),
                           [DataRequired(_("You must enter a username."))])

    #: If user is active
    active = BooleanField(_('Active'), default=True)

    #: User locale
    locale = SelectField(
        _('Locale'),
        default=_locales[0],
        choices=[(loc, loc) for loc in _locales],
    )

    #: API Sales Account, only for API users
    api_sales_account = VendorField(
        _('API Sales Account'),
        query_factory=lambda: SalesAccount.query.filter_by(global_account=True).order_by(
            SalesAccount.system.desc(), SalesAccount.name),
        get_label='name',
        allow_blank=False)

    #: Transaction permission, only for API users
    transaction_permission = BooleanField(_('Permit selling of electricity'))

    #: If this user has access to all sales accounts, only for non-api users
    account_all_access = BooleanField(_('Associate with all Sales Accounts'))

    #: Sales accounts associated with this user, only for non-api users
    accounts = QuerySelectMultipleField(
        _('Sales Accounts'),
        query_factory=lambda: SalesAccount.query.order_by(SalesAccount.system.desc(), SalesAccount.name),
        get_label='name',
    )

    #: If this user has access to all grounds, only for non-api users
    ground_all_access = BooleanField(_('Associate with all Grounds'))

    #: Grounds associated with this user, only for non-api users
    grounds = QuerySelectMultipleField(
        _('Grounds'),
        query_factory=lambda: Ground.query.order_by(Ground.name),
        get_label='name',
    )

    save_button = SubmitField(_('Save'))

    def __init__(self, role, *args, **kwargs):
        """Create a new user form."""
        super(BaseUserForm, self).__init__(*args, **kwargs)
        self.user = kwargs.get('obj')
        self.role = role

        # Vendor and transaction_permission are only used for api users
        if self.role != "api":
            del self['api_sales_account']
            del self['transaction_permission']

        # Accounts and Email is not used for API users, passwords are generated.
        if self.role == 'api':
            del self['account_all_access']
            del self['accounts']
            del self['email']
            if 'password' in self:
                del self['password']
                del self['confirm']

    def validate_username(self, field):
        """Validate the username field of this form."""
        if self.user and self.user.username == field.data:
            return
        if not User.is_username_unique(field.data):
            raise ValidationError(
                _('This username is already used, please enter another.'))

    def save(self, user):
        """Save content of user form to database."""
        if self.role == 'api':
            if not user.password:
                # A password is needed to base the authentication token on
                user.generate_password()

            if not self.transaction_permission.data:
                self.api_sales_account.data = None
        elif hasattr(self, 'password'):
            self.password.data = hash_password(self.password.data)
        super(BaseUserForm, self).save(user)
        if user.account_all_access or user.ground_all_access:
            if user.account_all_access:
                user.accounts = SalesAccount.get_all()
            if user.ground_all_access:
                user.grounds = Ground.get_all()
            sql.session.add(user)
            sql.session.commit()


class UserAddForm(BaseUserForm):

    """User Add Form."""

    mode = 'add'

    #: User email
    email = StringField(_('Email'),
                        [DataRequired(_("You must enter an email."))])

    #: Password, only for non-api users
    password = PasswordField(_('Password'),
                             [DataRequired(_("Password(s) cannot be empty.")),
                              EqualTo('confirm',
                                      message=_('Passwords must match.'))])
    #: Confirm password, only for non-api users
    confirm = PasswordField(_('Repeat password'),
                            [DataRequired(_("Password(s) cannot be empty."))])

    def validate_email(self, field):
        """Validate the email field of this form."""
        if not User.is_email_unique(field.data):
            raise ValidationError(
                _('This email is already used, please enter another.'))

    def notification_message(self, user):
        """Build a message to be displayed when a user is added."""
        link = build_link(url_for('user.view', username=user.username),
                          user.username)
        return Markup(_('User %(link)s created.', link=link))


class UserEditForm(BaseUserForm):

    """User Edit Form."""

    mode = 'edit'

    #: User read-only email, only for non-api users
    email = ReadOnlyStringField(_('Email'))

    def notification_message(self, user):
        """Build a message to be displayed when a user is updated."""
        link = build_link(url_for('user.view', username=user.username),
                          user.username)
        return Markup(_('User %(link)s updated.', link=link))
