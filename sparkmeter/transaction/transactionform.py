# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Forms module for the transaction web interface."""

from flask_babel import lazy_gettext as _
from sqlalchemy import desc
from wtforms.fields import FloatField, SelectField
from wtforms.validators import DataRequired, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField

from sparkmeter.transaction.transactiondomain import TransactionSource
from sparkmeter.web.forms import BaseForm


def transaction_sources():
    """
    sqlalchemy TransactionSource query for the QuerySelectField.

    this returns a name ordered list of user transactions sources, followed by the system bonus source.
    """
    return TransactionSource.query.order_by(
        desc(TransactionSource.name != TransactionSource.BONUS),
        TransactionSource.name,
    ).all()


class TransactionForm(BaseForm):

    """Transaction Form."""
    template_filename = 'transaction-form.html'

    amount = FloatField(
        _('Amount'),
        default=100,
        validators=[DataRequired(), NumberRange(min=0)],
    )

    account = QuerySelectField(
        _('From Sales Account'),
        get_label='name')

    acct_type = SelectField(
        _('Type'),
        choices=[
            (u'credit', _('Credit')),
            (u'debt', _('Debt')),
        ]
    )

    source = QuerySelectField(
        _('Source'),
        query_factory=transaction_sources,
        get_label='name',
        allow_blank=True,
        blank_text="select payment source",
    )


class TransactionTransferForm(BaseForm):

    """Transfer Form."""
    template_filename = 'transaction-transfer-form.html'

    amount = FloatField(
        _('Amount'),
        default=100,
        validators=[DataRequired(), NumberRange(min=0)],
    )

    markup = FloatField(
        _('Bonus rate'),
        validators=[NumberRange(min=0, max=1)],
        default=0.0,
    )

    acct_type = SelectField(
        _('Type'),
        choices=[
            (u'credit', _('Credit')),
            (u'debt', _('Debt')),
        ]
    )

    source = QuerySelectField(
        _('Source'),
        query_factory=transaction_sources,
        get_label='name',
        allow_blank=True,
        blank_text="select payment source",
    )
