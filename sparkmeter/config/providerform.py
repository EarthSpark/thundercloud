# -*- coding: utf-8 -*-
"""Forms for meter driver configuration."""

from flask.helpers import url_for
from flask_babel import lazy_gettext as _
from werkzeug.utils import redirect
from wtforms.fields import BooleanField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError

from sparkmeter.config import provider_settings
from sparkmeter.database.alchemy import sql
from sparkmeter.web.forms import BaseForm


class MeterDriverSettingsForm(BaseForm):
    """Configure the standalone meter driver URL and interface."""

    template_filename = "config-meter-driver-form.html"
    mode = "add"

    service_url = StringField(_("Driver service URL"))
    aes_key = StringField(_("AES key"))
    channel = StringField(_("Channel"))
    selected_interface = SelectField(_("Selected interface"), choices=[], validate_choice=False)
    enabled = BooleanField(_("Enabled"), default=True)
    save_button = SubmitField(_("Save"))

    def __init__(self, *args, **kwargs):
        self.provider_details = kwargs.pop("provider_details", None)
        self.provider = kwargs.pop("provider", None)
        super(MeterDriverSettingsForm, self).__init__(*args, **kwargs)
        self.mode = "edit" if self.provider is not None else "add"

        if self.provider is not None and not self.service_url.data:
            self.service_url.data = self.provider["base_url"]
            self.aes_key.data = self.provider.get("aes_key", "")
            self.channel.data = self.provider.get("channel", "")
            self.enabled.data = bool(self.provider.get("enabled", True))

        if self.provider_details is None and self.service_url.data:
            self.provider_details = provider_settings.get_live_interface_details(
                self.service_url.data,
                selected_interface=(
                    self.provider["selected_interface"] if self.provider is not None else None
                ),
            )

        if self.provider_details is not None:
            self._set_interface_choices(self.provider_details)
            self._apply_vendor_option_labels()

        if not self.selected_interface.data:
            self.selected_interface.data = (
                self.provider["selected_interface"] if self.provider is not None else None
            ) or self._default_selected_interface()

    def vendor_option_spec(self, name):
        """Return the normalized driver-requirement spec for a known field."""
        provider_data = self.provider_details or {}
        return (provider_data.get("driver_requirement_field_map") or {}).get(name)

    def supports_vendor_option(self, name):
        """Whether the validated provider advertises the given vendor option."""
        return self.vendor_option_spec(name) is not None

    def vendor_option_description(self, name):
        """Return help text for a vendor option field."""
        spec = self.vendor_option_spec(name) or {}
        return spec.get("description") or ""

    def vendor_option_required(self, name):
        """Whether the vendor option is required by the contract."""
        spec = self.vendor_option_spec(name) or {}
        return bool(spec.get("required"))

    def vendor_option_fields(self):
        """Return the contract-advertised driver requirement field list."""
        provider_data = self.provider_details or {}
        return provider_data.get("driver_requirement_fields") or []

    def config_directory(self):
        """Return the absolute directory where driver JSON files are created."""
        path = provider_settings.get_provider_config_abspath({"id": "example"})
        return path.rsplit("/", 1)[0] if path else ""

    def config_file_path(self):
        """Return the absolute JSON config path for an existing provider."""
        if self.provider is None:
            return ""
        return provider_settings.get_provider_config_abspath(self.provider)

    def _interface_choice_label(self, interface):
        """Format a display label for an advertised interface."""
        address = interface.get("base_url") or interface.get("target") or interface.get("address") or ""
        if address:
            return "{} ({})".format(interface.get("label") or interface["type"], address)
        return interface.get("label") or interface["type"]

    def _set_interface_choices(self, provider_data):
        """Populate the interface selector from live provider metadata."""
        interfaces = (provider_data or {}).get("interfaces") or []
        self.selected_interface.choices = [
            (interface["type"], self._interface_choice_label(interface)) for interface in interfaces
        ]

    def _default_selected_interface(self):
        """Return the preferred interface from the current provider metadata."""
        provider_data = self.provider_details or {}
        if provider_data.get("selected_interface"):
            return provider_data["selected_interface"]
        if provider_data.get("default_interface"):
            return provider_data["default_interface"]
        if self.selected_interface.choices:
            return self.selected_interface.choices[0][0]
        return "http"

    def _apply_vendor_option_labels(self):
        """Update known vendor-option labels from the validated contract."""
        aes_key_spec = self.vendor_option_spec("aes_key")
        if aes_key_spec and aes_key_spec.get("label"):
            self.aes_key.label.text = aes_key_spec["label"]

        channel_spec = self.vendor_option_spec("channel")
        if channel_spec and channel_spec.get("label"):
            self.channel.label.text = channel_spec["label"]

    def validate_service_url(self, field):
        if not (field.data or "").strip():
            self.provider_details = None
            self.selected_interface.choices = [("http", "HTTP API")]
            return

        try:
            self.provider_details = provider_settings.validate_contract(field.data)
            self._set_interface_choices(self.provider_details)
            self._apply_vendor_option_labels()
        except provider_settings.ProviderRegistrationError as exc:
            raise ValidationError(str(exc))

    def validate_selected_interface(self, field):
        if not (self.service_url.data or "").strip():
            return

        provider_data = getattr(self, "provider_details", None)
        if not provider_data or not field.data:
            return

        valid_interfaces = {interface["type"] for interface in provider_data.get("interfaces") or []}
        if field.data not in valid_interfaces:
            raise ValidationError(_("Selected interface is not available from this driver."))

    def validate_aes_key(self, field):
        field.data = ""

    def validate_channel(self, field):
        field.data = ""

    def save(self):
        """Persist the current meter driver settings."""
        if not (self.service_url.data or "").strip():
            raise RuntimeError("service_url is required for meter drivers")

        selected_interface = self.selected_interface.data or self._default_selected_interface()
        provider_id = provider_settings.save_provider_settings(
            self.service_url.data,
            selected_interface,
            enabled=self.enabled.data,
            provider_id=self.provider["id"] if self.provider is not None else None,
        )
        self.saved_provider_id = provider_id
        sql.session.commit()
        return provider_id

    def notification_message(self):
        """Return the success message after saving."""
        config_path = provider_settings.get_provider_config_abspath(
            {
                "id": getattr(self, "saved_provider_id", None),
            }
        )
        if self.mode == "edit":
            return _(
                "Meter driver updated. Edit %(path)s to fill the required driver fields.", path=config_path
            )
        return _(
            "Meter driver registered. Edit %(path)s to fill the required driver fields.", path=config_path
        )

    def redirect(self):
        """Return to the meter drivers list page."""
        return redirect(url_for("config.meter_driver"))


class MeterDriverConfigEditorForm(BaseForm):
    """Edit the generated JSON config for a meter driver."""

    template_filename = "config-meter-driver-config-editor.html"

    config_text = TextAreaField(_("Driver config JSON"))
    save_button = SubmitField(_("Save"))
    cancel_button = SubmitField(_("Cancel"))

    def __init__(self, *args, **kwargs):
        self.provider = kwargs.pop("provider")
        self.provider_details = kwargs.pop("provider_details")
        super(MeterDriverConfigEditorForm, self).__init__(*args, **kwargs)

        if not self.config_text.data:
            self.config_text.data = provider_settings.load_provider_config_text(self.provider)

    def required_fields(self):
        """Return the driver-required field list."""
        return (self.provider_details or {}).get("driver_requirement_fields") or []

    def config_file_path(self):
        """Return the absolute config path for the current provider."""
        return provider_settings.get_provider_config_abspath(self.provider)

    def save_and_init(self):
        """Persist the JSON file and initialize the driver."""
        payload, _validated = provider_settings.save_provider_config_text(
            self.provider,
            self.config_text.data or "{}",
        )
        provider_settings.init_provider_from_payload(self.provider, payload)

    def redirect(self):
        """Return to the meter driver list page."""
        return redirect(url_for("config.meter_driver"))
