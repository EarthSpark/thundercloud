# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""Tests for the meter web-interface forms."""

import pytest
from wtforms.validators import ValidationError

from sparkmeter.config.provider_settings import DriverConfigError
from sparkmeter.meter.meterdomain import Meter


@pytest.fixture
def meterform(app):
    """Import meterform after the app has populated config.

    meterform's class body reads config['DEFAULT_PHONE_COUNTRY_CODE'] at import
    time, which is only available once the app is bootstrapped — so the import
    is deferred into this app-dependent fixture rather than done at module top.
    """
    from sparkmeter.meter import meterform as module

    return module


def _payload(has_successful_init, invalid=False):
    """Build a runtime-settings payload shaped like the form inspects."""
    payload = {"init_status": {"has_successful_init": has_successful_init}}
    if invalid:
        payload["invalid"] = True
    return payload


class TestProviderChoices:
    def test_provider_choices_filters_ineligible_providers(self, meterform, app, session, monkeypatch):
        # One provider for each way _provider_choices() rejects a provider,
        # plus one that survives every filter.
        providers = [
            {"id": "disabled", "name": "Disabled", "enabled": False},
            {"id": "nopayload", "name": "NoPayload", "enabled": True},
            {"id": "invalid", "name": "Invalid", "enabled": True},
            {"id": "noinit", "name": "NoInit", "enabled": True},
            {"id": "good", "name": "Good Driver", "enabled": True},
        ]

        runtime = {
            "nopayload": {},
            "invalid": _payload(has_successful_init=True, invalid=True),
            "noinit": _payload(has_successful_init=False),
            "good": _payload(has_successful_init=True),
        }

        def fake_runtime_settings(provider):
            return runtime.get(provider["id"], {})

        def fake_validate(payload):
            if isinstance(payload, dict) and payload.get("invalid"):
                raise DriverConfigError("required fields are missing values: aes_key")
            return payload

        monkeypatch.setattr(meterform, "get_saved_providers", lambda: providers)
        monkeypatch.setattr(meterform, "load_provider_runtime_settings", fake_runtime_settings)
        monkeypatch.setattr(meterform, "validate_provider_config_payload", fake_validate)

        with app.test_request_context():
            form = meterform.MeterAddForm(formdata=None, meter_type=Meter.TYPE_CUSTOMER)

        # Only the fully eligible provider survives; the blank sentinel leads.
        assert form.provider_id.choices == [
            ("", "Select a meter driver"),
            ("good", "Good Driver"),
        ]

    def test_provider_choices_sorted_by_name_with_label_fallback(self, meterform, app, session, monkeypatch):
        providers = [
            {"id": "z", "name": "Zeta", "enabled": True},
            {"id": "a", "name": "alpha", "enabled": True},
            # No name: label falls back to base_url.
            {"id": "m", "base_url": "http://mid:9000", "enabled": True},
        ]

        monkeypatch.setattr(meterform, "get_saved_providers", lambda: providers)
        monkeypatch.setattr(
            meterform,
            "load_provider_runtime_settings",
            lambda provider: _payload(has_successful_init=True),
        )
        monkeypatch.setattr(meterform, "validate_provider_config_payload", lambda payload: payload)

        with app.test_request_context():
            form = meterform.MeterAddForm(formdata=None, meter_type=Meter.TYPE_CUSTOMER)

        # Sort key is the (lowercased) name only, so the nameless provider's
        # empty key sorts it first; its label still falls back to base_url.
        assert form.provider_id.choices == [
            ("", "Select a meter driver"),
            ("m", "http://mid:9000"),
            ("a", "alpha"),
            ("z", "Zeta"),
        ]


class TestValidateProviderId:
    def _make_form(self, meterform, app, monkeypatch):
        """Build a meter form with no auto-discovered drivers."""
        monkeypatch.setattr(meterform, "get_saved_providers", lambda: [])
        with app.test_request_context():
            return meterform.MeterAddForm(formdata=None, meter_type=Meter.TYPE_CUSTOMER)

    def test_requires_selection_when_drivers_available(self, meterform, app, session, monkeypatch):
        form = self._make_form(meterform, app, monkeypatch)
        form.provider_id.choices = [("", "Select a meter driver"), ("p1", "Driver One")]
        form.provider_id.data = ""

        with pytest.raises(ValidationError) as exc:
            form.validate_provider_id(form.provider_id)
        assert "Please select a meter driver." in str(exc.value)

    def test_rejects_selection_not_in_choices(self, meterform, app, session, monkeypatch):
        form = self._make_form(meterform, app, monkeypatch)
        form.provider_id.choices = [("", "Select a meter driver"), ("p1", "Driver One")]
        form.provider_id.data = "bogus"

        with pytest.raises(ValidationError) as exc:
            form.validate_provider_id(form.provider_id)
        assert "Please select a valid meter driver." in str(exc.value)

    def test_accepts_eligible_selection(self, meterform, app, session, monkeypatch):
        form = self._make_form(meterform, app, monkeypatch)
        form.provider_id.choices = [("", "Select a meter driver"), ("p1", "Driver One")]
        form.provider_id.data = "p1"

        # A selection that is among the choices passes without raising.
        assert form.validate_provider_id(form.provider_id) is None

    def test_no_drivers_allows_empty_selection(self, meterform, app, session, monkeypatch):
        form = self._make_form(meterform, app, monkeypatch)
        # Only the blank sentinel: an empty selection is "no driver", allowed.
        form.provider_id.choices = [("", "Select a meter driver")]
        form.provider_id.data = ""

        assert form.validate_provider_id(form.provider_id) is None
