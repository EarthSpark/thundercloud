# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 transaction views."""

import http.client
import uuid

from flask import url_for
from flask_security import roles_accepted
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from sparkmeter.api.apiviews0 import api, check_param, get_params, success
from sparkmeter.database.alchemy import sql
from sparkmeter.exceptions import APIError, TransactionError
from sparkmeter.meter.meterdomain import Customer
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource, Wallet
from sparkmeter.user.userutils import get_current_user


@api.route("/transaction/", methods=["POST"])
@roles_accepted("api")
def transaction_add():
    """Create transaction."""
    user = get_current_user()
    if user.api_sales_account is None or not user.api_sales_account.active:
        raise APIError("permission denied", status_code=http.client.FORBIDDEN)

    params = get_params()
    customer_id = check_param(params, "customer_id", uuid.UUID, name="uuid")
    amount = check_param(params, "amount", float, name="number")
    source_name = check_param(params, "source", default="cash")
    external_id = check_param(params, "external_id", default=None)
    memo = check_param(params, "memo", str, default=None)

    customer = Customer.get_by_id(customer_id)
    if customer is None:
        raise APIError("no such customer", status_code=http.client.NOT_FOUND)

    source = TransactionSource.get_by_name(source_name)
    if source is None:
        raise APIError("no such source", status_code=http.client.NOT_FOUND)

    try:
        transaction = Transaction.create_transactions(
            from_object=user.api_sales_account,
            to_object=customer.meter,
            amount=amount,
            user=user,
            wallet_type=Wallet.TYPE_CREDIT,
            ground=customer.meter.ground,
            source=source,
            external_id=external_id,
            memo=memo,
        )
    except TransactionError as e:
        if e.code == TransactionError.ERROR_NOT_ENOUGH_FUNDS:
            raise APIError("not enough funds", status_code=http.client.UNPROCESSABLE_ENTITY)
        elif e.code == TransactionError.ERROR_DUPLICATED:
            # FIXME: Change this status code httplib.CONFLICT when API can be broken
            raise APIError("transaction already exists", status_code=http.client.LOCKED)
        else:
            raise APIError(e.code + "-" + e.message)
    except ValueError as ve:
        raise APIError(str(ve))

    sql.session.commit()

    r = success(transaction_id=transaction.id)
    r.status_code = http.client.CREATED
    r.headers["Location"] = url_for(".transaction_view", transaction_id=str(transaction.id))
    return r


def _get_transaction(transaction_id):
    """Get a transaction by its ID."""
    try:
        return Transaction.get_by_id_or_external_id(transaction_id)
    except MultipleResultsFound:
        raise APIError("Multiple transactions with the external ID found. Please query with the internal ID.")
    except NoResultFound:
        raise APIError("no such transaction", status_code=http.client.NOT_FOUND)


@api.route("/transaction/<string:transaction_id>")
@roles_accepted("api")
def transaction_view(transaction_id):
    """Get transaction."""
    transaction = _get_transaction(transaction_id)
    if transaction.state == Transaction.STATE_PROCESSED:
        status = "processed"
    elif transaction.state == Transaction.STATE_ERROR:
        status = "error"
    elif transaction.state == Transaction.STATE_REVERSED:
        status = "reversed"
    else:
        status = "not-processed"

    def wallet_to_dict(wallet):
        sales_account = wallet.sales_account
        if sales_account is not None:
            if sales_account.system:
                sales_account_type = "system"
            elif sales_account.global_account:
                sales_account_type = "global"
            else:
                sales_account_type = "restricted"
            return dict(
                type="sales-account",
                id=sales_account.id,
                sales_account=dict(
                    type=sales_account_type,
                    name=sales_account.name,
                ),
            )
        meter = wallet.meter
        if meter:
            customer = meter.customer
            return dict(
                type="customer",
                id=customer.id,
                customer=dict(
                    name=customer.name,
                    code=customer.code,
                ),
            )
        else:  # pragma: nocoverage
            raise APIError("server error", status_code=http.client.INTERNAL_SERVER_ERROR)

    info = dict(
        id=transaction.id,
        created=transaction.created,
        source=transaction.source.name,
        amount=transaction.amount,
        status=status,
        error=transaction.error,
        external_id=transaction.external_id,
        type=transaction.acct_type,
        origin=transaction.origin,
        memo=transaction.memo,
    )
    info["from"] = wallet_to_dict(transaction.from_wallet)
    info["to"] = wallet_to_dict(transaction.to_wallet)
    return success(transaction=info)


@api.route("/transaction/<string:transaction_id>/reverse", methods=["POST"])
@roles_accepted("api")
def transaction_reverse(transaction_id):
    transaction = _get_transaction(transaction_id)
    if transaction.state == Transaction.STATE_PENDING:
        raise APIError("transaction is pending", status_code=http.client.UNPROCESSABLE_ENTITY)
    elif transaction.has_been_reversed():
        raise APIError("transaction has already been reversed", status_code=http.client.UNPROCESSABLE_ENTITY)
    elif transaction.state == Transaction.STATE_REVERSED:
        raise APIError("transaction is reversed", status_code=http.client.UNPROCESSABLE_ENTITY)
    elif transaction.origin == Transaction.ORIGIN_REVERSAL:
        raise APIError("transaction is a reversal", status_code=http.client.UNPROCESSABLE_ENTITY)

    user = get_current_user()
    try:
        rt = transaction.reverse(user)
    except TransactionError as e:
        raise APIError("error: " + e.message)

    sql.session.add(rt)
    sql.session.commit()

    r = success(transaction_id=rt.id)
    r.headers["Location"] = url_for(".transaction_view", transaction_id=str(rt.id))
    r.status_code = http.client.CREATED
    return r
