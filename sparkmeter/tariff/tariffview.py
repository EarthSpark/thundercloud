# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Tariff views."""

import http.client
import logging

from flask.globals import request
from flask.helpers import flash, url_for
from flask.templating import render_template
from flask_babel import lazy_gettext as _
from markupsafe import Markup
from werkzeug.exceptions import abort
from werkzeug.utils import redirect

from sparkmeter.misc.htmlutils import build_link
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tariff.tariffform import TariffForm
from sparkmeter.tariff.tariffutils import add_tariff_from_form, update_tariff_from_form
from sparkmeter.web.blueprint import AuthBlueprint
from sparkmeter.web.permission import verify_permission

logger = logging.getLogger(__name__)
tariff = AuthBlueprint("tariff", __name__)


@tariff.route("/tariff/")
@verify_permission("tariff", "view")
def index():
    """Listing of the tariffs."""
    tariffs = Tariff.query.order_by(Tariff.name).all()
    return render_template("tariff-index.html", tariffs=tariffs)


@tariff.route("/tariff/<uuid:tariff_id>/", methods=["GET"])
@verify_permission("tariff", "view")
def view(tariff_id):
    """Edit tariff page."""
    tariff = Tariff.get_by_id(tariff_id)
    if tariff is None:
        abort(http.client.NOT_FOUND)

    return render_template("tariff-view.html")


@tariff.route("/tariff/add", methods=["GET", "POST"])
@verify_permission("tariff", "add")
def add():
    """Add tariff page."""
    form = TariffForm(request.form)
    if request.method == "POST":
        tariff = add_tariff_from_form(form)
        if tariff:
            link = build_link(url_for("tariff.edit", tariff_id=tariff.id), tariff.name)
            flash(Markup(_("Tariff %(link)s created.", link=link)), "success")
            return redirect(url_for("tariff.index"))
    else:
        form.validate()  # prepopulate the empty form with validation errors
    return form.render(mode="add")


@tariff.route("/tariff/<uuid:tariff_id>/edit", methods=["GET", "POST"])
@verify_permission("tariff", "edit")
def edit(tariff_id):
    """Edit tariff page."""
    tariff = Tariff.get_by_id(tariff_id)
    form = TariffForm(request.form, obj=tariff)
    if request.method == "POST":
        tariff = update_tariff_from_form(tariff, form)
        if tariff:
            flash(_("Tariff updated."), "success")
            return redirect(url_for("tariff.view", tariff_id=tariff.id))
    else:
        form.validate()
    return form.render(mode="edit")
