# -*- coding: utf-8 -*-
"""Tests for the meter-driver configuration forms."""

import pytest
from wtforms.validators import ValidationError

from sparkmeter.config import provider_settings, providerform

# A live-interface details payload shaped like get_live_interface_details()
# returns, so the forms never need to reach out over httpx.
_DETAILS = {
    "interfaces": [
        {
            "type": "http",
            "label": "HTTP API",
            "base_url": "http://driver:18080",
            "address": "http://driver:18080",
        },
        {"type": "grpc", "label": "gRPC", "target": "driver:50051", "address": "driver:50051"},
    ],
    "default_interface": "http",
    "selected_interface": "http",
    "driver_requirement_fields": [
        {"name": "aes_key", "label": "AES Key", "description": "hex key", "required": True},
        {"name": "channel", "label": "Radio Channel", "description": "", "required": False},
    ],
    "driver_requirement_field_map": {
        "aes_key": {"name": "aes_key", "label": "AES Key", "description": "hex key", "required": True},
        "channel": {"name": "channel", "label": "Radio Channel", "description": "", "required": False},
    },
}


class TestMeterDriverSettingsForm:
    def test_add_mode_populates_interface_choices_and_labels(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            assert form.mode == "add"
            assert form.selected_interface.choices == [
                ("http", "HTTP API (http://driver:18080)"),
                ("grpc", "gRPC (driver:50051)"),
            ]
            # Advertised vendor-option labels are applied to the fields.
            assert form.aes_key.label.text == "AES Key"
            assert form.channel.label.text == "Radio Channel"
            assert form.selected_interface.data == "http"

    def test_edit_mode_seeds_from_provider_and_fetches_details(self, app, monkeypatch):
        monkeypatch.setattr(provider_settings, "get_live_interface_details", lambda *a, **k: _DETAILS)
        provider = {
            "id": "abc",
            "base_url": "http://driver:18080",
            "selected_interface": "grpc",
            "enabled": True,
        }
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider=provider)
            assert form.mode == "edit"
            assert form.service_url.data == "http://driver:18080"
            assert form.selected_interface.data == "grpc"

    def test_vendor_option_helpers(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            assert form.supports_vendor_option("aes_key") is True
            assert form.supports_vendor_option("nonexistent") is False
            assert form.vendor_option_required("aes_key") is True
            assert form.vendor_option_required("channel") is False
            assert form.vendor_option_description("aes_key") == "hex key"
            assert [f["name"] for f in form.vendor_option_fields()] == ["aes_key", "channel"]

    def test_config_paths(self, app, monkeypatch):
        monkeypatch.setattr(
            provider_settings,
            "get_provider_config_abspath",
            lambda provider: "/app/meter_driver_configs/{}.json".format(provider["id"]),
        )
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            assert form.config_directory() == "/app/meter_driver_configs"
            assert form.config_file_path() == ""  # add mode has no provider yet

            provider = {"id": "abc", "base_url": "http://x", "selected_interface": "http"}
            edit_form = providerform.MeterDriverSettingsForm(
                formdata=None, provider=provider, provider_details=_DETAILS
            )
            assert edit_form.config_file_path() == "/app/meter_driver_configs/abc.json"

    def test_default_selected_interface_falls_back_to_http(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(
                formdata=None, provider_details={"interfaces": [], "default_interface": ""}
            )
            assert form._default_selected_interface() == "http"

    def test_default_selected_interface_prefers_default_then_first_choice(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)

            form.provider_details = {"default_interface": "grpc"}
            assert form._default_selected_interface() == "grpc"

            form.provider_details = {}
            form.selected_interface.choices = [("mqtt", "MQTT")]
            assert form._default_selected_interface() == "mqtt"

    def test_interface_choice_label_without_address(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            assert form._interface_choice_label({"type": "http", "label": "HTTP API"}) == "HTTP API"

    def test_validate_selected_interface_noop_without_details(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            form.service_url.data = "http://driver:18080"
            form.provider_details = None
            # Service URL present but no discovered details → nothing to check.
            assert form.validate_selected_interface(form.selected_interface) is None

    def test_redirect_returns_to_driver_list(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            response = form.redirect()
            assert response.status_code == 302
            assert response.headers["Location"].endswith("/config/meter-driver")

    def test_validate_service_url_blank_resets_to_http_only(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            form.service_url.data = "  "
            form.validate_service_url(form.service_url)
            assert form.provider_details is None
            assert form.selected_interface.choices == [("http", "HTTP API")]

    def test_validate_service_url_valid_refreshes_details(self, app, monkeypatch):
        monkeypatch.setattr(provider_settings, "validate_contract", lambda url: _DETAILS)
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=None)
            form.service_url.data = "http://driver:18080"
            form.validate_service_url(form.service_url)
            assert form.provider_details == _DETAILS

    def test_validate_service_url_invalid_raises(self, app, monkeypatch):
        def boom(url):
            raise provider_settings.ProviderRegistrationError("bad url")

        monkeypatch.setattr(provider_settings, "validate_contract", boom)
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=None)
            form.service_url.data = "http://driver:18080"
            with pytest.raises(ValidationError):
                form.validate_service_url(form.service_url)

    def test_validate_selected_interface_rejects_unavailable(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            form.service_url.data = "http://driver:18080"
            form.selected_interface.data = "carrier-pigeon"
            with pytest.raises(ValidationError):
                form.validate_selected_interface(form.selected_interface)

    def test_validate_selected_interface_noop_without_service_url(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            form.service_url.data = ""
            # No service URL → nothing to validate against; returns without raising.
            assert form.validate_selected_interface(form.selected_interface) is None

    def test_validate_aes_key_and_channel_are_cleared(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            form.aes_key.data = "secret"
            form.channel.data = "26"
            form.validate_aes_key(form.aes_key)
            form.validate_channel(form.channel)
            assert form.aes_key.data == ""
            assert form.channel.data == ""

    def test_save_persists_and_returns_id(self, app, session, monkeypatch):
        captured = {}

        def fake_save(service_url, selected_interface, enabled=True, provider_id=None):
            captured.update(
                service_url=service_url,
                selected_interface=selected_interface,
                enabled=enabled,
                provider_id=provider_id,
            )
            return "new-id"

        monkeypatch.setattr(provider_settings, "save_provider_settings", fake_save)
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            form.service_url.data = "http://driver:18080"
            form.selected_interface.data = "http"
            form.enabled.data = True

            provider_id = form.save()

            assert provider_id == "new-id"
            assert form.saved_provider_id == "new-id"
            assert captured["service_url"] == "http://driver:18080"
            assert captured["provider_id"] is None  # add mode

    def test_save_requires_service_url(self, app):
        with app.test_request_context():
            form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            form.service_url.data = ""
            with pytest.raises(RuntimeError):
                form.save()

    def test_notification_message_varies_by_mode(self, app, monkeypatch):
        monkeypatch.setattr(provider_settings, "get_provider_config_abspath", lambda provider: "/cfg/x.json")
        with app.test_request_context():
            add_form = providerform.MeterDriverSettingsForm(formdata=None, provider_details=_DETAILS)
            assert "registered" in str(add_form.notification_message())

            provider = {"id": "abc", "base_url": "http://x", "selected_interface": "http"}
            edit_form = providerform.MeterDriverSettingsForm(
                formdata=None, provider=provider, provider_details=_DETAILS
            )
            assert "updated" in str(edit_form.notification_message())


class TestMeterDriverConfigEditorForm:
    def test_init_loads_config_text_when_absent(self, app, monkeypatch):
        monkeypatch.setattr(
            provider_settings, "load_provider_config_text", lambda provider: '{"driver": {}}\n'
        )
        provider = {"id": "abc"}
        with app.test_request_context():
            form = providerform.MeterDriverConfigEditorForm(
                formdata=None, provider=provider, provider_details=_DETAILS
            )
            assert form.config_text.data == '{"driver": {}}\n'
            assert [f["name"] for f in form.required_fields()] == ["aes_key", "channel"]

    def test_config_file_path(self, app, monkeypatch):
        monkeypatch.setattr(provider_settings, "load_provider_config_text", lambda provider: "{}\n")
        monkeypatch.setattr(
            provider_settings, "get_provider_config_abspath", lambda provider: "/cfg/abc.json"
        )
        with app.test_request_context():
            form = providerform.MeterDriverConfigEditorForm(
                formdata=None, provider={"id": "abc"}, provider_details=_DETAILS
            )
            assert form.config_file_path() == "/cfg/abc.json"

    def test_save_and_init_persists_then_initializes(self, app, monkeypatch):
        calls = []
        monkeypatch.setattr(provider_settings, "load_provider_config_text", lambda provider: "{}\n")
        monkeypatch.setattr(
            provider_settings,
            "save_provider_config_text",
            lambda provider, text: calls.append(("save", text)) or ({"init_status": {}}, {}),
        )
        monkeypatch.setattr(
            provider_settings,
            "init_provider_from_payload",
            lambda provider, payload: calls.append(("init", payload)),
        )
        with app.test_request_context():
            form = providerform.MeterDriverConfigEditorForm(
                formdata=None, provider={"id": "abc"}, provider_details=_DETAILS
            )
            form.config_text.data = '{"field_values": {}}'
            form.save_and_init()

        # save receives the editor's JSON text; the payload save RETURNS (its
        # first tuple element) is exactly what flows into init — not the raw
        # text and not the validated dict.
        assert calls == [
            ("save", '{"field_values": {}}'),
            ("init", {"init_status": {}}),
        ]

    def test_redirect_returns_to_driver_list(self, app, monkeypatch):
        monkeypatch.setattr(provider_settings, "load_provider_config_text", lambda provider: "{}\n")
        with app.test_request_context():
            form = providerform.MeterDriverConfigEditorForm(
                formdata=None, provider={"id": "abc"}, provider_details=_DETAILS
            )
            response = form.redirect()
            assert response.status_code == 302
            assert response.headers["Location"].endswith("/config/meter-driver")
