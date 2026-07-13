# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Config views."""

from flask import request
from flask.templating import render_template
from flask_security import roles_accepted

from sparkmeter.event.eventviews import format_event_type
from sparkmeter.web.blueprint import AuthBlueprint

config = AuthBlueprint("config", __name__)


@config.route("/config/billing")
@roles_accepted("operator")
def billing():
    """Billing configuration."""
    return render_template("config-billing.html")


@config.route("/config/sms")
@roles_accepted("operator")
def sms():
    """SMS configuration."""
    return render_template("config-sms.html")


@config.route("/config/sms-template-help")
@roles_accepted("operator")
def sms_template_help():
    """SMS template help."""
    event_type = request.args["event_type"]
    spec = format_event_type(event_type)
    return render_template("sms-template-help.html", event_spec=spec)


@config.route("/config/meters")
@roles_accepted("operator")
def meters():
    """Meter configuration page."""
    return render_template("config-meters.html")
