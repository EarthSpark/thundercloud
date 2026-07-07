# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Views for the transaction web interface."""

import csv
import http.client
import logging
from builtins import str
from collections import OrderedDict, namedtuple
from io import StringIO

from flask.globals import request
from flask.helpers import flash, url_for
from flask.templating import render_template
from flask.wrappers import Response
from flask_babel import lazy_gettext as _
from flask_security import roles_accepted
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from sparkmeter.database.alchemy import sql
from sparkmeter.exceptions import TransactionError
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.meter.meterdomain import Meter
from sparkmeter.misc.jsonutils import jsonify
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.transaction.transactiondomain import (Transaction, TransactionSource,
                                                      TransactionView, Wallet)
from sparkmeter.transaction.transactionform import TransactionForm, TransactionTransferForm
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.blueprint import AuthBlueprint
from sparkmeter.web.redirects import safe_redirect_target

logger = logging.getLogger(__name__)

transaction = AuthBlueprint('transaction', __name__)
_TransactionDefaults = namedtuple('TransactionDefaults', 'markup')


@transaction.route("/meter/<string:meter_serial>/transaction",
                   methods=['GET', 'POST'])
def add(meter_serial):
    """Add transactions page."""
    meter = Meter.get_by_serial(meter_serial)
    if meter is None:
        abort(http.client.NOT_FOUND)

    user = get_current_user()
    accounts = SalesAccount.get_accounts_by_user_ground(
        user,
        meter.ground,
        active_only=True
    )
    if accounts.count() == 0:
        abort(http.client.FORBIDDEN)
    form = TransactionForm(request.form)
    form.account.query = accounts

    form.acct_type.choices = [(u'credit', _('Credit'))]
    # only show the debt option if they have debt
    if meter.debt_wallet.value > 0:
        form.acct_type.choices.append((u'debt', _('Debt')))

    if request.method == 'POST' and form.validate():
        amount = form.amount.data
        wallet_type = form.acct_type.data
        source = TransactionSource.get_by_id(form.source.data.id)
        account = form.account.data

        try:
            if wallet_type == Wallet.TYPE_CREDIT:
                # credit goes from a sales account to a meter
                from_object = account
                to_object = meter
                if not account.active:
                    raise Exception(
                        "Cannot process transaction - the account '{}' is disabled.".format(account.name))
            else:
                # debt goes from a meter to a sales account
                from_object = meter
                to_object = account

            Transaction.create_transactions(
                from_object=from_object,
                to_object=to_object,
                amount=amount,
                wallet_type=wallet_type,
                user=user,
                source=source,
                ground=meter.ground,
                session=sql.session,
            )
        except Exception as e:
            form.amount.errors.append(str(e))
        else:
            sql.session.commit()
            flash(_('Transaction Added'), 'success')
            return redirect(
                url_for(
                    'meter.view',
                    meter_serial=meter.serial,
                )
            )
    return form.render(meter=meter)


@transaction.route("/sales-account/transfer", methods=['GET', 'POST'])
def transfer():
    """Transaction transfer page."""
    from_account = SalesAccount.get_by_id(request.args.get('from_account_id'))
    if from_account is None:
        abort(http.client.NOT_FOUND)
    to_account = SalesAccount.get_by_id(request.args.get('to_account_id'))
    if to_account is None or to_account.system:
        abort(http.client.NOT_FOUND)

    user = get_current_user()
    try:
        from_account.check_can_sell_from(user)
        to_account.check_can_sell_to(user)
    except TransactionError:
        abort(http.client.FORBIDDEN)

    obj = _TransactionDefaults(markup=to_account.markup)
    form = TransactionTransferForm(request.form, obj=obj)

    if request.method == 'POST' and form.validate():
        amount = form.amount.data
        markup = form.markup.data
        wallet_type = form.acct_type.data
        source = TransactionSource.get_by_id(form.source.data.id)
        ground = to_account.ground

        # FIXME: This logic should probably be moved to the caller
        if wallet_type == Wallet.TYPE_DEBT:
            from_account, to_account = to_account, from_account

        try:
            transaction = Transaction.create_transactions(
                from_object=from_account,
                to_object=to_account,
                amount=amount,
                wallet_type=wallet_type,
                user=user,
                source=source,
                ground=ground,
                markup=markup,
                session=sql.session,
            )
        except Exception as e:
            form.amount.errors.append(str(e))
        else:
            sql.session.commit()
            flash(_('Transaction %(transaction)s Added',
                    transaction=transaction.id), 'success')
            return redirect(
                url_for('sales_account.view', sales_account_id=to_account.id))

    return form.render(from_account=from_account, to_account=to_account)


@transaction.route("/transaction/<uuid:transaction_id>/reverse")
@roles_accepted('operator')
def reverse(transaction_id):
    """Reverses an transaction."""
    transaction = Transaction.get_by_id(transaction_id)
    if transaction is None:
        abort(http.client.NOT_FOUND)

    user = get_current_user()
    try:
        rt = transaction.reverse(user)
    except TransactionError as e:
        error = _("Error processing transaction: {0.message}".format(e))
        if e.code == TransactionError.ERROR_NOT_PROCESSED:
            error = _('Unable to reverse transaction %(id)s. '
                      'Not yet processed.',
                      id=transaction.id)
        elif e.code == TransactionError.ERROR_ALREADY_REVERSED:
            error = _('Unable to reverse transaction %(id)s. '
                      'Already reversed in another transaction.',
                      id=transaction.id)
        flash(error, 'danger')
        return redirect(safe_redirect_target(
            request.referrer, url_for('transaction.transactions'), request.host))

    sql.session.add(rt)
    sql.session.commit()
    flash(_('Transaction %(transaction_id)s reversed',
            transaction_id=transaction_id), 'success')
    return redirect(safe_redirect_target(
        request.referrer, url_for('transaction.transactions'), request.host))


@transaction.route("/transaction/transactions")
@roles_accepted('operator')
def transactions():
    """Transactions table."""
    return render_template(
        'transaction-list.html',
        ground=Ground.get_current(),
    )


DATATABLE_COLUMN_MAP = {
    '3': 'from_data',
    '4': 'to_data',
    'username': 'user_username',
}


def parse_datatables_args():
    """Parse the relevant datatables parameters."""
    params = {
        'draw': int(request.args.get('draw', '1')),
        'start': int(request.args.get('start', '0')),
        'length': int(request.args.get('length', '100')),
        'order': {
            'column_idx': int(request.args.get('order[0][column]', '-1')),
            'column_name': None,
            'dir': request.args.get('order[0][dir]', 'desc'),
        },
        'search': {
            'value': request.args.get('search[value]', ''),
            'regex': request.args.get('search[regex]', 'false') == 'true',
        },
    }
    column_name = request.args.get('columns[{}][data]'.format(params['order']['column_idx']), 'created')
    params['order']['column_name'] = DATATABLE_COLUMN_MAP.get(column_name, column_name)
    return params


@transaction.route("/transaction/transactions.json")
@roles_accepted('operator')
def transaction_data():
    """Transaction data REST API."""
    ground = Ground.get_current()
    user = get_current_user()
    filter_args = parse_datatables_args()
    transaction_views = TransactionView.get_transaction_view(ground=ground,
                                                             user=user,
                                                             order=filter_args['order']['column_name'],
                                                             ascending=filter_args['order']['dir'] == 'asc',
                                                             offset=filter_args['start'],
                                                             limit=filter_args['length'],
                                                             query_string=filter_args['search']['value'])
    return jsonify(**format_transaction_views(transaction_views, filter_args['draw']))


def iter_csv(data):
    """A generator that converts a transaction object to CSV."""
    mapping = OrderedDict([
        ('ID', 'id'),
        ('Amount', 'amount'),
        ('Type', 'acct_type'),
        ('From', ''),
        ('To', ''),
        ('User', 'user_username'),
        ('Reference', 'reference_id'),
        ('Created', 'created'),
        ('Ground', 'ground_name'),
        ('Source', 'source_name'),
        ('State', 'state'),
        ('Origin', 'origin'),
        ('External', 'external_id'),
        ('Memo', 'memo'),
        ('Error', 'error'),
        ('Meter Serial', ''),
        ('Sales Account', ''),
    ])
    line = StringIO()
    writer = csv.DictWriter(line, fieldnames=mapping.keys(), extrasaction='ignore',
                            lineterminator='\n')
    writer.writeheader()
    line.seek(0)
    yield line.read()
    for row in data:
        record = row.TransactionView
        line.truncate(0)
        line.seek(0)
        tx = {
            'From': record.from_data.get('meter_serial') or record.from_data.get('sales_account_name'),
            'To': record.to_data.get('customer_name') or record.to_data.get('sales_account_name'),
            'Meter Serial': record.from_data.get('meter_serial') or record.to_data.get('meter_serial', ''),
            'Sales Account': record.from_data.get('sales_account_name')
            or record.to_data.get('sales_account_name', ''),
        }
        for key, fieldname in mapping.items():
            if fieldname:
                tx[key] = getattr(record, fieldname)
        writer.writerow(tx)
        line.seek(0)
        yield line.read()


@transaction.route("/transaction/transactions.csv")
@roles_accepted('operator')
def transaction_export():
    """Transaction data REST API."""
    ground = Ground.get_current()
    user = get_current_user()
    filter_args = parse_datatables_args()
    transaction_views = TransactionView.get_transaction_view(ground=ground,
                                                             user=user,
                                                             order=filter_args['order']['column_name'],
                                                             ascending=filter_args['order']['dir'] == 'asc',
                                                             offset=None,
                                                             limit=None,
                                                             query_string=filter_args['search']['value'])
    response = Response(iter_csv(transaction_views), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=transactions.csv'
    return response


def format_transaction_views(transaction_views, draw):
    """Format a transaction query result.

    Format a query result from Transaction.get_transaction_view() and make it
    suitable for displaying in a JSON api.
    :param transaction_views: the query results
    :param draw: the datatables "draw" scalar
    :returns: an iterator of dictionaries
    """
    total = 0
    formatted = []
    for tv, total in transaction_views.all():
        formatted.append(dict(
            acct_type=tv.acct_type,
            amount=tv.amount,
            created=tv.created,
            error=tv.error,
            external_id=tv.external_id,
            from_data=tv.from_data,
            has_reversal=tv.has_reversal,
            id=tv.id,
            memo=tv.memo,
            ground_name=tv.ground_name,
            ground_serial=tv.ground_serial,
            monetary=tv.source_monetary,
            origin=tv.origin,
            reference_id=tv.reference_id,
            source_name=tv.source_name,
            state=tv.state,
            to_data=tv.to_data,
            username=tv.user_username,
        ))
    return {'total': total, 'draw': draw, 'transactions': formatted}
