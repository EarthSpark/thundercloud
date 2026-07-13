# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""SalesAccounts manage commands."""

import logging

import click
from flask.cli import with_appcontext
from zope.component import getUtility

from sparkmeter.cli_prompts import prompt_bool
from sparkmeter.interface import IApplication

logger = logging.getLogger(__name__)

salesaccount = click.Group("salesaccount", help="Sales account management commands.")


@salesaccount.command("list")
@with_appcontext
def list_accounts():
    """List all global sales accounts."""
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount

    app = getUtility(IApplication)
    app.setup_databases()

    fmt = "%36s | %20s | %20s"
    logger.info(fmt % ("ID", "NAME", "USERS"))
    logger.info("=" * 85)

    global_accounts = SalesAccount.query.filter_by(global_account=True, system=False)
    for account in global_accounts.order_by(SalesAccount.name, SalesAccount.id):
        usernames = sorted(u.username for u in account.users)
        logger.info(fmt % (account.id, account.name, ", ".join(usernames)))


@salesaccount.command("delete")
@click.option("-i", "--id", "sales_account_id", required=True, help="Sales account ID")
@click.option("-y", "--assume-yes", "force", is_flag=True, help="Skip confirmation")
@with_appcontext
def delete(sales_account_id, force=False):
    """Delete a sales account."""
    from sparkmeter.database.alchemy import sql
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount

    app = getUtility(IApplication)
    app.setup_databases()
    sales_account = SalesAccount.get_by_id(sales_account_id)
    if sales_account is None:
        logger.error("sales account %s does not exist", sales_account_id)
        raise SystemExit(1)

    msg = "Sales account %s will be deleted, are you sure" % (sales_account.name)
    if not force and not prompt_bool(msg, default=True):
        logger.info("sales account delete aborted")
        raise SystemExit(1)

    sql.session.delete(sales_account.credit_wallet)
    sql.session.delete(sales_account.debt_wallet)
    sql.session.delete(sales_account)
    sql.session.commit()

    logger.info("sales account %s was deleted", sales_account.name)
    return 0


@salesaccount.command("merge")
@click.option("-a", "--merge-salesaccount", "salesaccount_a_id", required=True, help="Sales account to keep")
@click.option(
    "-b", "--delete-salesaccount", "salesaccount_b_id", required=True, help="Sales account to delete"
)
@click.option("-y", "--assume-yes", "force", is_flag=True, help="Skip confirmation")
@with_appcontext
def merge(salesaccount_a_id, salesaccount_b_id, force=False):
    """Merge two sales accounts."""
    from sparkmeter.database.alchemy import sql
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
    from sparkmeter.transaction.transactiondomain import Transaction, Wallet
    from sparkmeter.user.userdomain import SalesAccountsUsers, User

    app = getUtility(IApplication)
    app.setup_databases()

    if salesaccount_a_id == salesaccount_b_id:
        logger.error("please enter two different sales accounts")
        raise SystemExit(1)

    salesaccount_a = SalesAccount.get_by_id(salesaccount_a_id)
    if salesaccount_a is None:
        logger.error("sales account %s does not exist", salesaccount_a_id)
        raise SystemExit(1)
    elif not salesaccount_a.global_account:
        logger.error(
            "sales account %s with id (%s) is a restricted sales account",
            salesaccount_a.name,
            salesaccount_a.id,
        )
        raise SystemExit(1)

    salesaccount_b = SalesAccount.get_by_id(salesaccount_b_id)
    if salesaccount_b is None:
        logger.error("sales account %s does not exist", salesaccount_b_id)
        raise SystemExit(1)
    elif not salesaccount_b.global_account:
        logger.error(
            "sales account %s with id (%s) is a restricted sales account",
            salesaccount_b.name,
            salesaccount_b.id,
        )
        raise SystemExit(1)

    # all wallets and users associated with sales account b
    wallets = Wallet.query.filter_by(sales_account_id=salesaccount_b.id)
    account_b_users = SalesAccountsUsers.query.filter_by(sales_account_id=salesaccount_b.id)
    api_users = User.query.filter_by(api_sales_account_id=salesaccount_b.id)

    b_from_transactions_credit = Transaction.query.filter_by(from_wallet_id=salesaccount_b.credit_wallet.id)
    b_to_transactions_credit = Transaction.query.filter_by(to_wallet_id=salesaccount_b.credit_wallet.id)
    b_from_transactions_debt = Transaction.query.filter_by(from_wallet_id=salesaccount_b.debt_wallet.id)
    b_to_transactions_debt = Transaction.query.filter_by(to_wallet_id=salesaccount_b.debt_wallet.id)

    logger.warning("%d wallets associated with sales account %s", wallets.count(), salesaccount_b.id)
    logger.warning("%d users associated with sales account %s", account_b_users.count(), salesaccount_b.id)
    logger.warning(
        "%d transactions associated with sales account %s",
        b_from_transactions_credit.count()
        + b_to_transactions_credit.count()
        + b_from_transactions_debt.count()
        + b_to_transactions_debt.count(),
        salesaccount_b.id,
    )

    msg = "Sales account %s will be deleted, are you sure" % (salesaccount_b.name)
    if not force and not prompt_bool(msg, default=True):
        logger.info("sales account merge aborted")
        raise SystemExit(1)

    # Merge Credit Wallet
    salesaccount_a.credit_wallet.value += salesaccount_b.credit_wallet.value
    sql.session.delete(salesaccount_b.credit_wallet)

    # Merge Debt Wallet
    salesaccount_a.debt_wallet.value += salesaccount_b.debt_wallet.value
    sql.session.delete(salesaccount_b.debt_wallet)

    # Merge Users
    salesaccount_a.users = list(set(salesaccount_a.users) | set(salesaccount_b.users))

    b_from_transactions_credit.update(dict(from_wallet_id=salesaccount_a.credit_wallet.id))
    b_to_transactions_credit.update(dict(to_wallet_id=salesaccount_a.credit_wallet.id))
    b_from_transactions_debt.update(dict(from_wallet_id=salesaccount_a.debt_wallet.id))
    b_to_transactions_debt.update(dict(to_wallet_id=salesaccount_a.debt_wallet.id))

    api_users.update(dict(api_sales_account_id=salesaccount_a.id))
    sql.session.delete(salesaccount_b)
    sql.session.commit()

    logger.info("sales account %s was deleted", salesaccount_b.name)

    return 0
