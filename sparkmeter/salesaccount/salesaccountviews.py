# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Views for the sales account web interface."""

import http.client
import logging
from builtins import str

from flask.globals import request
from flask.templating import render_template
from flask.wrappers import Response
from flask_security import roles_accepted
from werkzeug.exceptions import abort

from sparkmeter.database.alchemy import sql
from sparkmeter.exceptions import TransactionError
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.misc.jsonutils import jsonify
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.salesaccount.salesaccountform import SalesAccountAddForm, SalesAccountEditForm
from sparkmeter.transaction.transactiondomain import TransactionView
from sparkmeter.transaction.transactionview import (format_transaction_views, iter_csv,
                                                    parse_datatables_args)
from sparkmeter.user.userdomain import User
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.blueprint import AuthBlueprint
from sparkmeter.web.permission import verify_permission

sales_account = AuthBlueprint('sales_account', __name__)
logger = logging.getLogger(__name__)


@sales_account.route("/sales-account/")
def index():
    """Sales Account listing page."""
    return render_template('sales-accounts.html')


@sales_account.route("/sales-account/add/<account_type>", methods=['GET', 'POST'])
@verify_permission('sales-account', 'add', status=http.client.FORBIDDEN)
def add(account_type):
    """Sales Account add page."""
    if account_type not in ['global', 'restricted']:
        abort(http.client.BAD_REQUEST)
    global_account = account_type == 'global'
    form = SalesAccountAddForm(account_type, request.form)

    if request.method == 'POST' and form.validate():
        if global_account:
            ground = None
        else:
            ground = form.ground.data
        sales_account = SalesAccount.create_empty(
            ground,
            global_account=global_account)
        form.save(sales_account)
        all_accounts = SalesAccount.get_all()
        for user in User.get_with_all_account_access():
            user.accounts = all_accounts
        sql.session.commit()
        return form.notify_and_redirect(sales_account)

    return form.render(account_type=account_type)


@sales_account.route("/sales-account/<uuid:sales_account_id>/edit",
                     methods=['GET', 'POST'])
@verify_permission('sales-account', 'edit', status=http.client.FORBIDDEN)
def edit(sales_account_id):
    """SalesAccount edit page."""
    sales_account = SalesAccount.get_by_id(sales_account_id)
    if sales_account is None:
        abort(http.client.NOT_FOUND)

    if sales_account.system:
        abort(http.client.FORBIDDEN)

    if sales_account.global_account:
        account_type = 'global'
    else:
        account_type = 'restricted'
    form = SalesAccountEditForm(account_type, request.form, obj=sales_account)

    if request.method == 'POST' and form.validate():
        form.save(sales_account)
        return form.notify_and_redirect(sales_account)

    return form.render(account_type=account_type, sales_account=sales_account)


@sales_account.route("/sales-account/<uuid:sales_account_id>/",
                     methods=['GET', 'POST'])
@verify_permission('sales-account', 'view', status=http.client.FORBIDDEN)
def view(sales_account_id):
    """SalesAccount edit page."""
    sales_account = SalesAccount.get_by_id(sales_account_id)
    if sales_account is None:
        abort(http.client.NOT_FOUND)
    system_sales_account = SalesAccount.get_system()
    user = get_current_user()
    try:
        system_sales_account.check_can_sell_from(user)
        sales_account.check_can_sell_to(user)
        user_can_sell = True
    except TransactionError as e:
        user_can_sell = False
        logger.warning(u"Cannot place transactions: " + str(e))

    can_edit = user.is_operator() and not sales_account.system
    return render_template(
        'sales-account-view.html',
        sales_account=sales_account,
        system_sales_account=system_sales_account,
        user_can_sell=user_can_sell,
        can_edit=can_edit,
    )


@sales_account.route("/sales-account/<uuid:sales_account_id>/transactions.json")
def transactions(sales_account_id):
    """Sales account transactions data."""
    sales_account = SalesAccount.get_by_id(sales_account_id)
    if sales_account is None:
        abort(http.client.NOT_FOUND)
    user = get_current_user()
    ground = Ground.get_current()
    filter_args = parse_datatables_args()
    transaction_views = TransactionView.get_transaction_view(ground=ground,
                                                             user=user,
                                                             sales_account=sales_account,
                                                             order=filter_args['order']['column_name'],
                                                             ascending=filter_args['order']['dir'] == 'asc',
                                                             offset=filter_args['start'],
                                                             limit=filter_args['length'],
                                                             query_string=filter_args['search']['value'])
    return jsonify(**format_transaction_views(transaction_views, filter_args['draw']))


@sales_account.route("/sales-account/<uuid:sales_account_id>/transactions.csv")
def transactions_export(sales_account_id):
    """Sales account transactions export."""
    sales_account = SalesAccount.get_by_id(sales_account_id)
    if sales_account is None:
        abort(http.client.NOT_FOUND)
    user = get_current_user()
    ground = Ground.get_current()
    filter_args = parse_datatables_args()
    transaction_views = TransactionView.get_transaction_view(ground=ground,
                                                             user=user,
                                                             sales_account=sales_account,
                                                             order=filter_args['order']['column_name'],
                                                             ascending=filter_args['order']['dir'] == 'asc',
                                                             offset=None,
                                                             limit=None,
                                                             query_string=filter_args['search']['value'])
    response = Response(iter_csv(transaction_views), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=transactions.csv'
    return response


@sales_account.route("/sales-account/<account_type>.json")
@roles_accepted('operator')
def sales_accounts(account_type):
    """Sales accounts data."""
    if account_type not in ['global', 'restricted']:
        abort(http.client.BAD_REQUEST)
    ground = Ground.get_current()
    return sales_accounts_as_json(
        global_account=account_type == 'global',
        ground=ground,
    )


def sales_accounts_as_dict(global_account, ground=None, user=None):
    """
    Query & Serialize sales accounts as a collection of dicts

    :param global_account: True for global_accounts, False for restricted
    :type global_account: bool
    :param ground: ground to filter, None for everything
    :type ground: Ground | None
    :param user: user to filter for, None for everything
    :type user: User | None
    :return: a collection of sales account dicts
    """

    if global_account:
        ground = None
    query = SalesAccount.get_sales_account_view(
        ground=ground,
        user=user,
        global_account=global_account,
        include_system=True,
    )
    sas = []
    for result in sql.session.execute(query):
        row = dict(
            active=result.active,
            credit=result.credit,
            debt=result.debt,
            id=result.id,
            markup=result.markup,
            name=result.name,
            negative_permitted=result.negative_permitted,
        )
        if global_account:
            row['transaction_count'] = result.transaction_count
            row['transaction_total'] = result.transaction_total
        else:
            row['ground_serial'] = result.ground_serial
            row['ground_name'] = result.ground_name
        sas.append(row)
    return sas


def sales_accounts_as_json(global_account, ground=None, user=None):
    """
    Query & Serialize sales accounts as a JSON response

    :param global_account: True for global_accounts, False for restricted
    :type global_account: bool
    :param ground: ground to filter, None for everything
    :type ground: Ground | None
    :param user: user to filter for, None for everything
    :type user: User | None
    :return: a response.
    """
    return jsonify(sales_accounts=sales_accounts_as_dict(global_account, ground, user))
