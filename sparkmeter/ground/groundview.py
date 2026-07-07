# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Views for the ground web interface."""

import http.client

from flask import flash, url_for
from flask.globals import request
from flask.templating import render_template
from flask_babel import lazy_gettext as _
from flask_security import roles_accepted
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.ground.groundform import GroundForm
from sparkmeter.user.userutils import get_current_user
from sparkmeter.web.blueprint import AuthBlueprint
from sparkmeter.web.permission import verify_permission

ground = AuthBlueprint('ground', __name__)


# Redirect for for backwards compatibility added in 1.4
@ground.route("/microgrid/<path:path>")
@ground.route("/microgrid/")
def microgrid_redirect(path=""):
    """
    Permanent redirect for urls using the old microgrid urls.

    This is only for backwards compatability with grids that had the old urls.
    """
    return redirect("/ground/%s" % (path, ), http.client.MOVED_PERMANENTLY)


@ground.route("/ground/")
@roles_accepted('operator')
def index():
    """Listing of the grounds."""
    if config['HEROKU']:
        grounds = get_current_user().grounds
    else:
        grounds = [Ground.get_current()]
    return render_template('ground-index.html',
                           grounds=grounds)


@ground.route("/ground/<ground_serial>/edit", methods=['GET', 'POST'])
@verify_permission('ground', 'edit', status=http.client.FORBIDDEN)
def edit(ground_serial):
    """Edit the ground."""
    ground = Ground.get_by_serial(ground_serial)
    if ground is None:
        abort(http.client.NOT_FOUND)
    form = GroundForm(request.form, obj=ground)
    if request.method == 'POST' and form.validate():
        form.populate_obj(ground)
        form.save(ground)
        return form.notify_and_redirect(ground)

    return form.render(ground=ground)


@ground.route("/ground/override")
@ground.route("/ground/<ground_serial>/override")
@roles_accepted('operator')
def override(ground_serial=None):
    """The manual override page."""
    if config['HEROKU']:
        abort(http.client.NOT_FOUND)
    if ground_serial is None:
        ground = Ground.get_current()
    else:
        ground = Ground.get_by_serial(ground_serial)
    if ground is None:
        abort(http.client.NOT_FOUND)
    return render_template('ground-override.html', ground=ground)


@ground.route("/ground/<ground_serial>/manual-override")
@verify_permission('ground', 'view', status=http.client.FORBIDDEN)
def manual_override(ground_serial):
    """Turn off override status."""
    ground = Ground.get_by_serial(ground_serial)
    if ground is None:
        abort(http.client.NOT_FOUND)
    ground.private.set_override_meter_state(False)
    sql.session.commit()
    flash(_('Override disabled, meters can now consume energy again'))
    return redirect(url_for('homepage.index'))
