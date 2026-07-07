# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""User views for the web interface."""
import http.client
import logging

from flask.globals import request
from flask.helpers import flash, url_for
from flask.templating import render_template
from flask_babel import gettext as _
from flask_babel import refresh
from flask_security import roles_accepted
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.misc.jsonutils import jsonify
from sparkmeter.salesaccount.salesaccountviews import sales_accounts_as_json
from sparkmeter.user.userdomain import User
from sparkmeter.user.userform import UserAddForm, UserEditForm
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.blueprint import AuthBlueprint
from sparkmeter.web.permission import verify_permission
from sparkmeter.web.redirects import safe_redirect_target

logger = logging.getLogger(__name__)
user = AuthBlueprint('user', __name__)


@user.route("/user/")
@roles_accepted('operator')
def list():
    """User list page."""
    user = get_current_user()
    if user.is_vendor():
        return redirect(
            url_for('user.view', username=user.username)
        )
    return render_template('user-list.html')


@user.route("/user/<username>/")
def view(username):
    """User base page."""
    user = User.get_by_name(username)
    if user is None:
        abort(http.client.NOT_FOUND)
    current_user = get_current_user()
    if current_user.is_vendor() and current_user.username != username:
        abort(http.client.UNAUTHORIZED)

    return render_template('user-view.html', user=User.get_by_name(username))


@user.route("/users.json")
@roles_accepted('operator')
def users():
    """User listing json data."""
    role = request.args.get('role')
    if role not in ['operator', 'vendor', 'api']:
        abort(http.client.BAD_REQUEST)
    query = User.get_user_view(role)
    result = sql.session.execute(query)
    return jsonify(users=format_users(result))


@user.route("/user/add/<role>", methods=['GET', 'POST'])
@verify_permission('user', 'add', status=http.client.FORBIDDEN)
def add(role='operator'):
    """User add page."""
    if role not in ['operator', 'vendor', 'api']:
        abort(http.client.NOT_FOUND)

    form = UserAddForm(role, request.form)

    if request.method == 'POST' and form.validate():
        user = User.create_empty(role)
        form.save(user)
        return form.notify_and_redirect(user)

    return form.render(role=role)


@user.route("/user/<username>/edit", methods=['GET', 'POST'])
@verify_permission('user', 'edit', status=http.client.FORBIDDEN)
def edit(username):
    """User edit page."""
    user = User.get_by_name(username)
    if user is None:
        abort(http.client.NOT_FOUND)
    form = UserEditForm(user.roles[0].name, request.form, obj=user)

    if request.method == 'POST' and form.validate():
        form.save(user)
        return form.notify_and_redirect(user)

    return form.render(role=user.roles[0].name, user=user)


@user.route("/user/<username>/<locale>", methods=['GET', 'POST'])
def update_locale(username, locale):
    """Update the users locale."""
    current_user = get_current_user()
    if current_user.username != username:
        abort(http.client.UNAUTHORIZED)

    if locale not in config['LOCALES']:
        abort(http.client.NOT_FOUND)

    current_user.locale = locale
    current_user.save()
    refresh()
    flash(_('User updated'), 'success')
    next = safe_redirect_target(
        request.referrer, url_for('user.view', username=current_user.username),
        request.host)
    return redirect(next)


@user.route("/user/<username>/reset-credentials.json", methods=['POST'])
@verify_permission('user', 'edit', status=http.client.FORBIDDEN)
def reset_credentials(username):
    """Reset User credentials."""
    user = User.get_by_name(username)
    if user is None:
        abort(http.client.NOT_FOUND)
    user.generate_password()
    sql.session.add(user)
    sql.session.commit()
    return jsonify()


def format_users(results):
    """Format a users query result.

    Format a query result from User.get_user_view() and make it
    suitable for displaying in a JSON api.
    :param results: the query results
    :returns: an iterator of dictionaries
    """
    rv = []
    for r in results:
        rv.append(dict(
            active=r.active,
            email=r.email,
            id=r.id,
            accounts=r.accounts,
            username=r.username,
        ))
    return rv


@user.route("/user/grounds.json")
def current_grounds():
    """Fetch the list of grounds for the currently logged in user."""
    user = get_current_user()
    grounds = [dict(id=m.id,
                    name=m.name,
                    serial=m.serial) for m in user.grounds]
    return jsonify(grounds=grounds)


@user.route("/user/token.json")
def current_token():
    """Get the current auth token."""
    user = get_current_user()
    return jsonify(token=user.get_auth_token())


@user.route("/user/sales-account/<account_type>.json")
def current_sales_accounts(account_type):
    """Fetch the list of sales accounts for the currently logged in user."""
    if account_type not in ['global', 'restricted']:
        abort(http.client.BAD_REQUEST)
    user = get_current_user()
    return sales_accounts_as_json(
        ground=Ground.get_current(),
        global_account=account_type == 'global',
        user=user,
    )


@user.route("/user/<username>/sales-account/<account_type>.json")
def sales_accounts(username, account_type):
    """Fetch the list of sales accounts for a user."""
    if account_type not in ['global', 'restricted']:
        abort(http.client.BAD_REQUEST)
    user = User.get_by_name(username)
    if user is None:
        abort(http.client.NOT_FOUND)
    current_user = get_current_user()
    if current_user.is_vendor() and current_user.username != username:
        abort(http.client.UNAUTHORIZED)

    return sales_accounts_as_json(
        ground=Ground.get_current(),
        global_account=account_type == 'global',
        user=user,
    )
