# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Config views."""

import http.client

from flask import abort, flash, request
from flask.helpers import redirect, url_for
from flask.templating import render_template
from flask_babel import lazy_gettext as _
from flask_security import roles_accepted

from sparkmeter.config.provider_settings import (
    DriverConfigError,
    DriverInitializationError,
    get_live_interface_details,
    get_provider,
    get_provider_config_abspath,
    get_provider_init_status,
    get_runtime_status,
    get_saved_providers,
)
from sparkmeter.config.providerform import MeterDriverConfigEditorForm, MeterDriverSettingsForm
from sparkmeter.event.eventviews import format_event_type
from sparkmeter.meter.meterdomain import Meter
from sparkmeter.metering.lifespan import activate_metering_runtime_in_process
from sparkmeter.web.blueprint import AuthBlueprint

config = AuthBlueprint("config", __name__)


def _live_metering_activation_flash(activation_error):
    """Translate low-level runtime activation errors into operator-friendly UI text."""
    if activation_error == "main event loop is not available":
        if Meter.query.count() == 0:
            return (
                _(
                    "Driver config saved and init succeeded. No meters are registered yet, "
                    "so live metering will start after you add a meter."
                ),
                "info",
            )
        return (
            _(
                "Driver config saved and init succeeded. Live metering is not active in this "
                "screen yet, but it will start the next time TC2.0 starts."
            ),
            "info",
        )

    return (
        _("Driver config saved and init succeeded. Live metering is not active yet."),
        "info",
    )


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


@config.route("/config/meter-driver", methods=["GET", "POST"])
@roles_accepted("operator")
def meter_driver():
    """Meter driver list page."""
    providers = get_saved_providers()
    provider_statuses = {}
    provider_contracts = {}
    provider_config_paths = {}
    provider_init_statuses = {}

    for provider in providers:
        provider_init_statuses[provider["id"]] = get_provider_init_status(provider)
        provider_contracts[provider["id"]] = get_live_interface_details(
            provider["base_url"],
            selected_interface=provider["selected_interface"],
        )
        provider_statuses[provider["id"]] = get_runtime_status(
            provider["base_url"],
            include_gateway_status=bool(provider_init_statuses[provider["id"]].get("has_successful_init")),
        )
        provider_config_paths[provider["id"]] = get_provider_config_abspath(provider)

    return render_template(
        "config-meter-driver-list.html",
        providers=providers,
        provider_statuses=provider_statuses,
        provider_contracts=provider_contracts,
        provider_config_paths=provider_config_paths,
        provider_init_statuses=provider_init_statuses,
    )


@config.route("/config/meter-driver/add", methods=["GET", "POST"])
@roles_accepted("operator")
def meter_driver_add():
    """Register a meter driver."""
    form = MeterDriverSettingsForm(
        formdata=request.form if request.method == "POST" else None,
    )

    if request.method == "POST" and form.validate():
        form.save()
        flash(form.notification_message(), "success")
        return redirect(url_for("config.meter_driver"))

    return form.render()


@config.route("/config/meter-driver/<string:provider_id>/edit", methods=["GET", "POST"])
@roles_accepted("operator")
def meter_driver_edit(provider_id):
    """Edit the configured meter driver."""
    provider = get_provider(provider_id)
    if provider is None:
        abort(http.client.NOT_FOUND)

    provider_details = get_live_interface_details(
        provider["base_url"],
        selected_interface=provider["selected_interface"],
    )

    form = MeterDriverSettingsForm(
        formdata=request.form if request.method == "POST" else None,
        provider_details=provider_details,
        provider=provider,
    )

    if request.method == "POST" and form.validate():
        form.save()
        flash(form.notification_message(), "success")
        return redirect(url_for("config.meter_driver"))

    return form.render(provider=provider)


@config.route("/config/meter-driver/<string:provider_id>/config", methods=["GET", "POST"])
@roles_accepted("operator")
def meter_driver_config(provider_id):
    """Edit the generated JSON config for a meter driver and attempt init."""
    provider = get_provider(provider_id)
    if provider is None:
        abort(http.client.NOT_FOUND)

    provider_details = get_live_interface_details(
        provider["base_url"],
        selected_interface=provider["selected_interface"],
    )
    form = MeterDriverConfigEditorForm(
        formdata=request.form if request.method == "POST" else None,
        provider=provider,
        provider_details=provider_details,
    )

    if request.method == "POST":
        if form.cancel_button.data:
            return redirect(url_for("config.meter_driver"))
        if form.save_button.data and form.validate():
            try:
                form.save_and_init()
            except DriverConfigError as exc:
                flash(str(exc), "danger")
                return form.render(provider=provider, provider_details=provider_details)
            except DriverInitializationError as exc:
                flash(str(exc), "danger")
                return form.render(provider=provider, provider_details=provider_details)
            activated, activation_error = activate_metering_runtime_in_process(
                skip_provider_init=True,
            )
            if not activated and activation_error:
                message, category = _live_metering_activation_flash(activation_error)
                flash(message, category)
            flash(_("Driver config saved and init succeeded."), "success")
            return redirect(url_for("config.meter_driver"))

    return form.render(provider=provider, provider_details=provider_details)
