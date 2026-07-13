# -*- coding: utf-8 -*-
# Copyright © 2019 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 sales account views."""

import http.client

from flask import request
from flask_security import roles_accepted

from sparkmeter.api.apiviews0 import api, check_param, get_params, success
from sparkmeter.database.alchemy import sql
from sparkmeter.exceptions import APIError
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.salesaccount.salesaccountviews import sales_accounts_as_dict
from sparkmeter.transaction.transactiondomain import Transaction, TransactionSource, Wallet
from sparkmeter.user.userutils import get_current_user


def _format_sales_account(acct):
    """Format a sales account dict for API presentation.

    :param acct: The sales account dict to format
    :returns: A formatted sales account dict
    """
    formatted = {
        "id": acct["id"],
        "name": acct["name"],
        "markup": acct["markup"],
        "active": acct["active"],
        "credit": acct["credit"],
    }
    if "ground_serial" in acct:  # restricted
        formatted["account_type"] = "restricted"
    else:  # global
        formatted["account_type"] = "global"
        formatted["credit"] = None
        formatted["markup"] = None
    return formatted


@api.route("/sales-accounts")
@roles_accepted("api")
def list_sales_accounts():
    """Get the sales accounts for the site."""
    account_type = check_param(request.args, "type", required=False)
    if account_type and account_type not in ("global", "restricted"):
        raise APIError("bad parameter: 'type', must be one of: 'global', 'restricted'")
    elif not account_type:
        account_type = "all"
    accounts = []
    if account_type in ("all", "restricted"):
        accounts.extend(sales_accounts_as_dict(False))
    if account_type in ("all", "global"):
        accounts.extend(sales_accounts_as_dict(True))
    return success(accounts=[_format_sales_account(account) for account in accounts])


@api.route("/sales-accounts/<uuid:account_id>")
@roles_accepted("api")
def get_sales_account(account_id):
    """Get a sales account by its ID."""
    acct = SalesAccount.get_by_id(account_id)
    if acct is None:
        raise APIError("no such sales account", status_code=http.client.NOT_FOUND)
    acct_dict = {
        "id": acct.id,
        "active": acct.active,
        "credit": acct.credit_wallet.value,
        "markup": acct.markup,
        "name": acct.name,
    }
    if not acct.global_account:
        acct_dict["ground_serial"] = None  # the formatter tests for the presence of the ground serial key
    return success(account=_format_sales_account(acct_dict))


@api.route("/sales-accounts/<uuid:account_id>/payment", methods=["POST"])
@roles_accepted("api")
def pay_sales_account(account_id):
    """Get a sales account by its ID."""
    user = get_current_user()
    if user.api_sales_account is None or not user.api_sales_account.active:
        raise APIError("permission denied", status_code=http.client.FORBIDDEN)
    to_account = SalesAccount.get_by_id(account_id)
    if to_account is None:
        raise APIError("no such sales account", status_code=http.client.NOT_FOUND)
    if to_account.global_account:
        raise APIError("only restricted sales accounts may receive payments")
    params = get_params()
    amount = check_param(params, "amount", param_type=float)
    source_name = check_param(params, "source", param_type=str, strict=True)
    markup = check_param(params, "markup", param_type=float, default=to_account.markup, required=False)
    external_id = check_param(params, "external_id", required=False)
    memo = check_param(params, "memo", required=False)
    source = TransactionSource.get_by_name(source_name)
    if not source:
        raise APIError(
            "bad parameter: 'source', must be one of: '{}', '{}'".format(
                TransactionSource.CASH, TransactionSource.BONUS
            )
        )
    try:
        transaction, bonus_transaction = Transaction.create_transactions(
            from_object=user.api_sales_account,
            to_object=to_account,
            amount=amount,
            wallet_type=Wallet.TYPE_CREDIT,
            memo=memo,
            user=user,
            source=source,
            markup=markup,
            external_id=external_id,
            ground=to_account.ground,
            return_bonus_tuple=True,
        )
    except Exception as err:
        raise APIError(str(err))
    sql.session.commit()
    result = success(
        transaction_id=transaction.id,
        bonus_transaction_id=bonus_transaction.id if bonus_transaction else None,
    )
    result.status_code = http.client.CREATED
    return result
