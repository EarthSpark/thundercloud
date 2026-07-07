# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Views for the ground web interface."""

import datetime
import http.client
import logging
import os

from flask.globals import current_app, request
from flask.helpers import flash, make_response, send_from_directory, url_for
from flask.templating import render_template
from flask_babel import format_timedelta
from flask_babel import gettext as _
from flask_security import login_user, roles_accepted
from werkzeug.exceptions import abort
from werkzeug.utils import redirect
from zope.component import getUtility

from sparkmeter.config.configdict import config
from sparkmeter.database.databasecommand import reset_demo
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.interface import IApplication
from sparkmeter.user.userdomain import User
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.blueprint import AuthBlueprint
from sparkmeter.web.redirects import safe_redirect_target

app = getUtility(IApplication)
logger = logging.getLogger(__name__)
web = AuthBlueprint('web', __name__)


@web.route('/favicon.ico')
def favicon():
    """Default favicon for this app."""
    r = send_from_directory(
        os.path.join(app.static_folder, 'logo'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon')
    return r


@web.local_only
@web.route("/reset-demo", methods=['GET', 'POST'])
@roles_accepted('operator')
def reset_demo_data():
    """Reset the demo."""
    if not config.get('ENABLE_DEMO_RESET', False):
        return abort(http.client.NOT_FOUND)

    if request.method == 'POST':
        logger.info(request.form.get('confirm'))
        if request.form.get('confirm') == 'YES':
            reset_demo()
            return make_response('System reset')
        else:
            flash('You must type "YES" into the box to reset')

    return render_template('reset_demo.html')


@web.route("/demo-login/<uuid:user_id>")
def demo_login(user_id):
    """Login as demo users."""
    if not current_app._demo_login_enabled():
        return abort(http.client.NOT_FOUND)

    user = User.get_by_id(user_id)
    if not user:
        abort(http.client.NOT_FOUND)

    if login_user(user):
        flash(_('Successfully logged in as %(username)s', username=user.username))

    return redirect(safe_redirect_target(
        request.args.get("next"), url_for("homepage.index")))


@app.context_processor
def set_config():
    """Inject the current app configs into templates."""
    ctx = dict(config=config)
    user = get_current_user()
    if user is not None:
        override_modifieds = []
        ground_name = None
        # FIXME: Do more on the PostgreSQL side, but this probably scales fine for a few hundred
        # grounds
        for serial, name, override_state, override_modified in Ground.get_override_view():
            if serial == config['SERIAL'] and not config['HEROKU']:
                ground_name = name
            if override_state:
                override_modifieds.append(override_modified)
        ctx['ground_name'] = ground_name
        if override_modifieds:
            ctx['override_banner'] = create_override_banner(override_modifieds)
    return ctx


def create_override_banner(override_modifieds):
    """Create the override banner."""
    current_time = datetime.datetime.utcnow().replace(tzinfo=None)
    delta = current_time - min(override_modifieds)
    delta_friendly = format_timedelta(delta, granularity='minutes')
    return _('System has been in override mode for %(delta_friendly)s',
             delta_friendly=delta_friendly)


@app.route('/assets/<path:filename>')
def custom_static(filename):    # pragma: nocoverage
    """Serve static assets, only for development."""
    if not app.debug:
        abort(http.client.NOT_FOUND)
    assets_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'assets')
    return send_from_directory(assets_dir, filename)
