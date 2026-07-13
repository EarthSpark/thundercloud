# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Config views unittest."""

import http.client

from sparkmeter.config import configviews, provider_settings
from sparkmeter.config.configviews import _live_metering_activation_flash
from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import MeterFactory


def _provider_record(provider_id="driver-1"):
    """A saved-provider dict shaped like get_saved_providers() output."""
    return {
        "id": provider_id,
        "name": "SparkNet-Http",
        "base_url": "http://127.0.0.1:18080",
        "openapi_url": "http://127.0.0.1:18080/openapi.json",
        "service_version": "1.2.3",
        "selected_interface": "http",
        "selected_interface_target": "",
        "enabled": True,
    }


def _interface_details():
    """A deterministic get_live_interface_details() payload with no driver fields."""
    return {
        "name": "SparkNet-Http",
        "base_url": "http://127.0.0.1:18080",
        "openapi_url": "http://127.0.0.1:18080/openapi.json",
        "service_version": "1.2.3",
        "driver_requirement_fields": [],
        "driver_requirement_field_map": {},
        "vendor_option_fields": [],
        "vendor_option_field_map": {},
        "interfaces": [
            {
                "type": "http",
                "label": "HTTP API",
                "base_url": "http://127.0.0.1:18080",
                "address": "http://127.0.0.1:18080",
            }
        ],
        "default_interface": "http",
        "selected_interface": "http",
        "selected_interface_details": {
            "type": "http",
            "label": "HTTP API",
            "address": "http://127.0.0.1:18080",
        },
    }


class LiveMeteringFlashTest(WebViewTestCaseBase):
    def test_no_loop_without_meters_defers_to_first_meter(self, session):
        message, category = _live_metering_activation_flash("main event loop is not available")
        assert category == "info"
        assert "add a meter" in str(message)

    def test_no_loop_with_meters_defers_to_next_start(self, session):
        MeterFactory()
        session.commit()
        message, category = _live_metering_activation_flash("main event loop is not available")
        assert category == "info"
        assert "next time" in str(message)

    def test_other_activation_error_is_generic(self, session):
        message, category = _live_metering_activation_flash("some unexpected error")
        assert category == "info"
        assert "not active yet" in str(message)


class ConfigTest(WebViewTestCaseBase):
    def test_billing(self, client, config):
        client.login_as(self.user)
        path = "/config/billing"
        config["HEROKU"] = True
        response = client.get(path)
        self.verify_response(response)

    def test_sms(self, client, config):
        path = "/config/sms"
        config["HEROKU"] = True
        response = client.get(path)
        self.verify_response(response)

    def test_sms_template_help(self, client):
        path = "/config/sms-template-help"
        response = client.get(path + "?event_type=customer-low-balance")
        self.verify_response(response)

    def test_meters(self, client, config):
        client.login_as(self.user)
        config["HEROKU"] = True
        path = "/config/meters"
        response = client.get(path)
        self.verify_response(response)

    def test_meter_driver(self, client, config):
        client.login_as(self.user)
        config["HEROKU"] = True
        path = "/config/meter-driver"
        response = client.get(path)
        self.verify_response(response)

    def test_meter_driver_with_saved_provider(self, client, config, monkeypatch):
        # Exercises the per-provider status loop (configviews lines 99-108).
        config["HEROKU"] = True
        provider = _provider_record()
        monkeypatch.setattr(configviews, "get_saved_providers", lambda: [provider])
        monkeypatch.setattr(
            configviews,
            "get_provider_init_status",
            lambda p: {
                "has_successful_init": True,
                "last_init_succeeded": True,
                "last_init_error": "",
            },
        )
        monkeypatch.setattr(
            configviews,
            "get_live_interface_details",
            lambda base_url, selected_interface=None: _interface_details(),
        )
        seen = {}

        def fake_runtime_status(base_url, include_gateway_status=True):
            seen["include_gateway_status"] = include_gateway_status
            return {
                "online": True,
                "message": "online",
                "gateway_checked": True,
                "gateway_active": True,
                "gateway_type": "sparknet",
            }

        monkeypatch.setattr(configviews, "get_runtime_status", fake_runtime_status)
        monkeypatch.setattr(
            configviews,
            "get_provider_config_abspath",
            lambda p: "/srv/meter_driver_configs/driver-1.json",
        )

        response = client.get("/config/meter-driver")

        # has_successful_init is True, so gateway status must be requested.
        assert seen["include_gateway_status"] is True
        self.verify_response(response)

    def test_meter_driver_add_get(self, client, config):
        # Renders the empty registration form (configviews lines 124-126, 133).
        config["HEROKU"] = True
        response = client.get("/config/meter-driver/add")
        self.verify_response(response)

    def test_meter_driver_add_post_saves(self, client, config, monkeypatch):
        # POST with a valid contract saves and redirects (configviews lines 128-131).
        config["HEROKU"] = True
        details = _interface_details()
        monkeypatch.setattr(
            provider_settings,
            "get_live_interface_details",
            lambda service_url, selected_interface=None, timeout=2.0: details,
        )
        monkeypatch.setattr(
            provider_settings,
            "validate_contract",
            lambda service_url, timeout=10.0: details,
        )
        saved = {}

        def fake_save(
            service_url, selected_interface, enabled=True, provider_id=None, aes_key="", channel=""
        ):
            saved["service_url"] = service_url
            saved["selected_interface"] = selected_interface
            saved["enabled"] = enabled
            saved["provider_id"] = provider_id
            return "new-driver-id"

        monkeypatch.setattr(provider_settings, "save_provider_settings", fake_save)

        response = client.post(
            "/config/meter-driver/add",
            data={
                "service_url": "http://127.0.0.1:18080",
                "selected_interface": "http",
                "enabled": "y",
                "save_button": "Save",
            },
        )

        assert response.status_code == http.client.FOUND
        assert response.headers["Location"].endswith("/config/meter-driver")
        assert saved["service_url"] == "http://127.0.0.1:18080"
        assert saved["selected_interface"] == "http"
        assert saved["enabled"] is True
        assert saved["provider_id"] is None

    def test_meter_driver_edit_get(self, client, config, monkeypatch):
        # Renders the edit form for a saved provider (configviews lines 140-160).
        config["HEROKU"] = True
        provider = _provider_record()
        monkeypatch.setattr(
            configviews,
            "get_provider",
            lambda provider_id: provider if provider_id == provider["id"] else None,
        )
        monkeypatch.setattr(
            configviews,
            "get_live_interface_details",
            lambda base_url, selected_interface=None: _interface_details(),
        )

        response = client.get("/config/meter-driver/driver-1/edit")
        self.verify_response(response)

    def test_meter_driver_edit_not_found(self, client, config):
        # Unknown provider ids abort with 404 (configviews lines 141-142).
        config["HEROKU"] = True
        response = client.get("/config/meter-driver/does-not-exist/edit")
        assert response.status_code == http.client.NOT_FOUND

    def test_meter_driver_config_get(self, client, config, monkeypatch):
        # Renders the JSON config editor (configviews lines 167-179, 202).
        config["HEROKU"] = True
        provider = _provider_record("config-driver")
        monkeypatch.setattr(
            configviews,
            "get_provider",
            lambda provider_id: provider if provider_id == provider["id"] else None,
        )
        monkeypatch.setattr(
            configviews,
            "get_live_interface_details",
            lambda base_url, selected_interface=None: _interface_details(),
        )
        monkeypatch.setattr(
            provider_settings,
            "get_provider_config_abspath",
            lambda p: "/srv/meter_driver_configs/config-driver.json",
        )
        monkeypatch.setattr(
            provider_settings,
            "load_provider_config_text",
            lambda p: '{\n  "field_values": {}\n}\n',
        )

        response = client.get("/config/meter-driver/config-driver/config")
        self.verify_response(response)

    def test_meter_driver_config_not_found(self, client, config):
        # Unknown provider ids abort with 404 (configviews lines 168-169).
        config["HEROKU"] = True
        response = client.get("/config/meter-driver/nope/config")
        assert response.status_code == http.client.NOT_FOUND

    def _patch_config_editor(self, monkeypatch, provider):
        monkeypatch.setattr(
            configviews,
            "get_provider",
            lambda provider_id: provider if provider_id == provider["id"] else None,
        )
        monkeypatch.setattr(
            configviews,
            "get_live_interface_details",
            lambda base_url, selected_interface=None: _interface_details(),
        )
        monkeypatch.setattr(
            provider_settings,
            "get_provider_config_abspath",
            lambda p: "/srv/meter_driver_configs/config-driver.json",
        )
        monkeypatch.setattr(
            provider_settings,
            "load_provider_config_text",
            lambda p: '{\n  "field_values": {}\n}\n',
        )

    def test_meter_driver_config_post_cancel(self, client, config, monkeypatch):
        # Cancel button redirects to the list without persisting (configviews 181-183).
        config["HEROKU"] = True
        provider = _provider_record("config-driver")
        self._patch_config_editor(monkeypatch, provider)
        save_calls = []
        monkeypatch.setattr(
            provider_settings,
            "save_provider_config_text",
            lambda p, text: save_calls.append((p, text)) or ({}, {}),
        )

        response = client.post(
            "/config/meter-driver/config-driver/config",
            data={"cancel_button": "Cancel"},
        )
        assert response.status_code == http.client.FOUND
        assert response.headers["Location"].endswith("/config/meter-driver")
        # Cancel must not write anything.
        assert save_calls == []

    def test_meter_driver_config_post_save_and_init(self, client, config, monkeypatch):
        # Successful save + init redirects to the list (configviews 184-186, 193-195, 199-200).
        config["HEROKU"] = True
        provider = _provider_record("config-driver")
        self._patch_config_editor(monkeypatch, provider)
        save_calls, init_calls, activate_calls = [], [], []

        def fake_save(p, text):
            save_calls.append((p, text))
            return ({"driver": {"id": p["id"]}}, {})

        def fake_init(p, payload):
            init_calls.append((p, payload))

        def fake_activate(skip_provider_init=True):
            activate_calls.append(skip_provider_init)
            return (True, None)

        monkeypatch.setattr(provider_settings, "save_provider_config_text", fake_save)
        monkeypatch.setattr(provider_settings, "init_provider_from_payload", fake_init)
        monkeypatch.setattr(configviews, "activate_metering_runtime_in_process", fake_activate)

        response = client.post(
            "/config/meter-driver/config-driver/config",
            data={"save_button": "Save", "config_text": '{"field_values": {}}'},
            follow_redirects=True,
        )

        # The edited JSON is persisted, and the payload save returns is exactly
        # what flows into init (not the raw text or the validated dict).
        assert save_calls == [(provider, '{"field_values": {}}')]
        assert init_calls == [(provider, {"driver": {"id": "config-driver"}})]
        assert activate_calls == [True]
        # Activation succeeded → only the success flash, no deferral notice.
        assert b"Driver config saved and init succeeded." in response.data
        assert b"add a meter" not in response.data

    def test_meter_driver_config_post_activation_deferred(self, client, config, monkeypatch):
        # Save succeeds but live activation is deferred (configviews 196-198).
        config["HEROKU"] = True
        provider = _provider_record("config-driver")
        self._patch_config_editor(monkeypatch, provider)
        monkeypatch.setattr(provider_settings, "save_provider_config_text", lambda p, text: ({}, {}))
        monkeypatch.setattr(provider_settings, "init_provider_from_payload", lambda p, payload: None)
        activate_calls = []

        def fake_activate(skip_provider_init=True):
            activate_calls.append(skip_provider_init)
            return (False, "main event loop is not available")

        monkeypatch.setattr(configviews, "activate_metering_runtime_in_process", fake_activate)

        response = client.post(
            "/config/meter-driver/config-driver/config",
            data={"save_button": "Save", "config_text": '{"field_values": {}}'},
            follow_redirects=True,
        )

        assert activate_calls == [True]
        # The deferred-activation branch flashes the extra "add a meter" notice
        # in addition to the success message.
        assert b"add a meter" in response.data
        assert b"Driver config saved and init succeeded." in response.data

    def test_meter_driver_config_post_config_error(self, client, config, monkeypatch):
        # A DriverConfigError re-renders the editor with a danger flash (configviews lines 187-189).
        config["HEROKU"] = True
        provider = _provider_record("config-driver")
        self._patch_config_editor(monkeypatch, provider)

        def boom(p, text):
            raise provider_settings.DriverConfigError("config JSON is invalid")

        monkeypatch.setattr(provider_settings, "save_provider_config_text", boom)

        response = client.post(
            "/config/meter-driver/config-driver/config",
            data={"save_button": "Save", "config_text": "not json"},
        )
        # The whole editor page is re-rendered with the danger flash; snapshot it.
        self.verify_response(response)

    def test_meter_driver_config_post_init_error(self, client, config, monkeypatch):
        # A DriverInitializationError re-renders the editor with a danger flash (configviews lines 190-192).
        config["HEROKU"] = True
        provider = _provider_record("config-driver")
        self._patch_config_editor(monkeypatch, provider)
        monkeypatch.setattr(provider_settings, "save_provider_config_text", lambda p, text: ({}, {}))

        def boom(p, payload):
            raise provider_settings.DriverInitializationError("driver init failed: nope")

        monkeypatch.setattr(provider_settings, "init_provider_from_payload", boom)

        response = client.post(
            "/config/meter-driver/config-driver/config",
            data={"save_button": "Save", "config_text": '{"field_values": {}}'},
        )
        # The whole editor page is re-rendered with the danger flash; snapshot it.
        self.verify_response(response)
