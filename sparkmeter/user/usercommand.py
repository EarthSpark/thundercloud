# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""User manage commands."""

import logging

import click
from flask.cli import with_appcontext
from zope.component import getUtility

from sparkmeter.cli_prompts import prompt, prompt_bool, prompt_choices
from sparkmeter.interface import IApplication

logger = logging.getLogger(__name__)

user = click.Group("user", help="User management commands.")


@user.command("create")
@click.option("-e", "--email", default=None, help="User email address")
@click.option("-p", "--password", default=None, help="User password")
@click.option("-u", "--username", default=None, help="Username")
@click.option("-r", "--role", default=None, help="User role (operator, vendor, api)")
@click.option("-a", "--account", default=None, help="Account of an api user")
@with_appcontext
def create(email=None, password=None, username=None, role=None, account=None):
    """Create a user.

    For api users,
      - Add account access for the account specified
    For vendors,
      - Add access to all current grounds.
    For operators:
      - Add access to all current & future grounds.
      - Add access to all current & future sales accounts.
    """
    from flask_security.utils import hash_password

    from sparkmeter.database.alchemy import sql
    from sparkmeter.ground.grounddomain import Ground
    from sparkmeter.misc.uuidutils import as_uuid
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
    from sparkmeter.user.userdomain import Role, User

    app = getUtility(IApplication)
    app.setup_databases()

    roles = Role.query.all()
    role_choices = [(r.name, r) for r in roles]
    data = dict(
        email=email,
        password=password,
        role=role,
        username=username,
    )
    if role == "api":
        data["account"] = account

    user = None
    first_run = True
    while user is None:
        try:
            if role == "api":
                data["password"] = data["email"] = "not-used"
            for field in data:
                if first_run and data[field]:
                    continue
                if field == "role":
                    value = prompt_choices(field, role_choices, data[field])
                else:
                    value = prompt(field, data[field])
                if value:
                    data[field] = value

            first_run = False
            created, user = User.get_one_or_create(
                session=sql.session, id=as_uuid(data["username"]), username=data["username"]
            )
            user.roles = [Role.query.filter_by(name=data["role"]).one()]
            if user.is_api():
                user.generate_password()
                if data["account"]:
                    user.accounts = [SalesAccount.query.filter_by(name=data["account"]).one()]
            else:
                user.password = hash_password(data["password"])
                user.email = data["email"]
                user.grounds = Ground.get_all()
                if role == "operator":
                    user.accounts = SalesAccount.get_all()
                    user.account_all_access = True
                    user.ground_all_access = True
            sql.session.commit()
        except Exception as e:
            logger.error("an error occurred: %r, try again" % (e,))
            raise SystemExit(1)

    logger.info("user created")
    return 0


@user.command("list")
@with_appcontext
def list_users():
    """List all users with id and username."""
    from sparkmeter.user.userdomain import User

    app = getUtility(IApplication)
    app.setup_databases()

    fmt = "%36s | %20s | %30s"
    logger.info(fmt % ("ID", "USERNAME", "EMAIL"))
    logger.info("=" * 92)

    for user in User.query.order_by(User.username, User.id):
        logger.info(fmt % (user.id, user.username, user.email))


@user.command("merge")
@click.option("-a", "--merge-user", "usera_id", required=True, help="User to keep")
@click.option("-b", "--delete-user", "userb_id", required=True, help="User to delete")
@click.option("-y", "--assume-yes", "force", is_flag=True, help="Skip confirmation")
@with_appcontext
def merge(usera_id, userb_id, force=False):
    """Merge two users."""
    from sparkmeter.database.alchemy import sql
    from sparkmeter.ground.grounddomain import Ground
    from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
    from sparkmeter.transaction.transactiondomain import Transaction
    from sparkmeter.user.userdomain import User

    app = getUtility(IApplication)
    app.setup_databases()

    if usera_id == userb_id:  # pragma: nocoverage
        logger.error("users must be different")
        raise SystemExit(1)

    usera = User.get_by_id(usera_id)
    if usera is None:
        logger.error("user %s does not exist", usera_id)
        raise SystemExit(1)

    userb = User.get_by_id(userb_id)
    if userb is None:
        logger.error("user %s does not exist", userb_id)
        raise SystemExit(1)

    # print out the number of transactions and all grounds
    transactions = Transaction.query.filter_by(user_id=userb.id)
    logger.warning("%d transactions are associated with user %s", transactions.count(), userb.username)
    for ground in userb.grounds:
        logger.warning("Ground: %s" % (ground.name,))
    for account in userb.accounts:
        logger.warning("Sales account: %s" % (account.name,))

    # ask if password should be from user-a or user-b
    if not force and not prompt_bool("Use password from user %s" % (usera.username,), default=True):
        usera.password = userb.password
        logger.info("user b password used")

    # confirm before committing to database
    msg = "User %s will be deleted, are you sure" % (userb.username,)
    if not force and not prompt_bool(msg, default=True):
        logger.info("user merge aborted")
        raise SystemExit(1)

    # transactions from user-b will be changed to be from user-a
    transactions.update(dict(user_id=usera.id))

    # all grounds in user-b will be added to user-a
    if usera.ground_all_access or userb.ground_all_access:  # pragma: nocoverage
        usera.ground_all_access = True
        grounds = list(Ground.get_all())
    else:
        grounds = list(set(usera.grounds) | set(userb.grounds))
    usera.grounds = grounds

    # all sales account in user-b will be added to user-a
    if usera.account_all_access or userb.account_all_access:  # pragma: nocoverage
        usera.account_all_access = True
        accounts = list(SalesAccount.get_all())
    else:
        accounts = list(set(usera.accounts) | set(userb.accounts))
    usera.accounts = accounts
    sql.session.add(usera)

    sql.session.delete(userb)
    sql.session.commit()
    logger.info("user %s was deleted", userb.username)

    return 0
