# -*- coding: utf-8 -*-
"""Meter driver settings tests."""

import json

import httpx
import pytest

from sparkmeter.config import provider_settings
from sparkmeter.metering.provider_config import configured_provider_url


class FakeResponse(object):
    """Minimal HTTPX-like response test double."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        """Pretend the response was successful."""

    def json(self):
        """Return the configured JSON payload."""
        return self._payload


def _fake_openapi_get(url, timeout):
    """A minimal valid driver OpenAPI, for tests that only need a saved provider."""
    return FakeResponse(
        {
            "info": {"title": "SparkNet-Http", "version": "1.2.3"},
            "paths": {"/v1/commands": {}, "/v1/events": {}},
            "x-open-thunder": {"default_interface": "http", "interfaces": []},
        }
    )


def test_validate_contract_discovers_interfaces(monkeypatch):
    def fake_get(url, timeout):
        assert url == "http://127.0.0.1:18080/openapi.json"
        assert timeout == 10.0
        return FakeResponse(
            {
                "info": {
                    "title": "SparkNet-Http",
                    "version": "1.2.3",
                },
                "paths": {
                    "/v1/commands": {},
                    "/v1/events": {},
                },
                "x-open-thunder": {
                    "default_interface": "grpc",
                    "interfaces": [
                        {
                            "type": "grpc",
                            "label": "gRPC",
                            "target": "127.0.0.1:19090",
                        },
                    ],
                },
            }
        )

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert details["name"] == "SparkNet-Http"
    assert details["base_url"] == "http://127.0.0.1:18080"
    assert details["openapi_url"] == "http://127.0.0.1:18080/openapi.json"
    assert details["default_interface"] == "grpc"
    assert [interface["type"] for interface in details["interfaces"]] == ["http", "grpc"]


def test_validate_contract_discovers_vendor_option_requirements(monkeypatch):
    def fake_get(url, timeout):
        if url.endswith("/v1/requirements"):
            return FakeResponse(
                {
                    "required_fields": ["aes_key", "channel", "heartbeat_period_duration"],
                }
            )
        return FakeResponse(
            {
                "openapi": "3.1.0",
                "info": {
                    "title": "SparkNet-Http",
                    "version": "1.2.3",
                },
                "paths": {
                    "/v1/commands": {
                        "post": {
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "oneOf": [
                                                {"$ref": "#/components/schemas/ConfigureProviderCommand"},
                                            ],
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "/v1/events": {},
                },
                "components": {
                    "schemas": {
                        "ConfigureProviderCommand": {
                            "type": "object",
                            "properties": {
                                "command_type": {
                                    "type": "string",
                                    "enum": ["configure_provider"],
                                },
                                "vendor_options": {
                                    "type": "object",
                                    "required": ["aes_key", "channel"],
                                    "properties": {
                                        "aes_key": {
                                            "type": "string",
                                            "title": "AES key",
                                            "description": "32-character hex network key.",
                                            "pattern": "[0-9a-fA-F]{32}",
                                        },
                                        "channel": {
                                            "type": "integer",
                                            "title": "Channel",
                                            "description": "Radio channel to configure.",
                                            "minimum": 11,
                                            "maximum": 26,
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
                "x-open-thunder": {
                    "default_interface": "http",
                    "interfaces": [],
                },
            }
        )

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    fields = details["driver_requirement_field_map"]
    assert fields["aes_key"]["required"] is True
    assert fields["aes_key"]["pattern"] == "[0-9a-fA-F]{32}"
    assert fields["channel"]["required"] is True
    assert fields["channel"]["minimum"] == 11
    assert fields["channel"]["maximum"] == 26
    assert fields["heartbeat_period_duration"]["required"] is True
    assert fields["heartbeat_period_duration"]["type"] == "integer"


def test_validate_contract_falls_back_to_openapi_requirements(monkeypatch):
    def fake_get(url, timeout):
        if url.endswith("/v1/requirements"):
            raise httpx.HTTPStatusError(
                "missing",
                request=httpx.Request("GET", url),
                response=httpx.Response(404, request=httpx.Request("GET", url)),
            )
        return FakeResponse(
            {
                "openapi": "3.1.0",
                "info": {
                    "title": "SparkNet-Http",
                    "version": "1.2.3",
                },
                "paths": {
                    "/v1/commands": {
                        "post": {
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "oneOf": [
                                                {"$ref": "#/components/schemas/ConfigureProviderCommand"},
                                            ],
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "/v1/events": {},
                },
                "components": {
                    "schemas": {
                        "ConfigureProviderCommand": {
                            "type": "object",
                            "properties": {
                                "command_type": {
                                    "type": "string",
                                    "enum": ["configure_provider"],
                                },
                                "vendor_options": {
                                    "type": "object",
                                    "required": ["aes_key", "channel"],
                                    "properties": {
                                        "aes_key": {
                                            "type": "string",
                                            "pattern": "[0-9a-fA-F]{32}",
                                        },
                                        "channel": {
                                            "type": "integer",
                                            "minimum": 11,
                                            "maximum": 26,
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
                "x-open-thunder": {
                    "default_interface": "http",
                    "interfaces": [],
                },
            }
        )

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    fields = details["driver_requirement_field_map"]
    assert fields["aes_key"]["required"] is True
    assert fields["channel"]["required"] is True


def test_validate_contract_rejects_missing_paths(monkeypatch):
    def fake_get(url, timeout):
        return FakeResponse(
            {
                "info": {
                    "title": "SparkNet-Http",
                },
                "paths": {
                    "/v1/commands": {},
                },
            }
        )

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    try:
        provider_settings.validate_contract("http://127.0.0.1:18080")
    except provider_settings.ProviderRegistrationError as exc:
        assert "missing required paths" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ProviderRegistrationError")


def test_configured_provider_url_uses_saved_setting(session, monkeypatch):
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_openapi_get)
    provider_settings.save_provider_settings("http://127.0.0.1:18080", "http")
    session.commit()

    assert configured_provider_url(default="") == "http://127.0.0.1:18080"


def test_configured_provider_url_ignores_env_override(session, monkeypatch):
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_openapi_get)
    provider_settings.save_provider_settings("http://127.0.0.1:18080", "http")
    session.commit()
    monkeypatch.setenv("METERING_PROVIDER_URL", "http://127.0.0.1:28080")

    assert configured_provider_url(default="") == "http://127.0.0.1:18080"


def test_init_provider_from_payload_coerces_integer_fields(monkeypatch, tmp_path):
    import sparkmeter.metering.runtime_client as runtime_client

    captured = {}

    def fake_initialize_provider_sync(provider, field_values, provider_details=None):
        captured["field_values"] = field_values

    monkeypatch.setattr(runtime_client, "initialize_provider_sync", fake_initialize_provider_sync)
    monkeypatch.setattr(provider_settings, "get_live_interface_details", lambda *a, **k: {})
    monkeypatch.setattr(
        provider_settings, "get_provider_config_abspath", lambda provider: str(tmp_path / "driver.json")
    )

    provider_settings.init_provider_from_payload(
        {"base_url": "http://127.0.0.1:18080"},
        {
            "field_values": {
                "aes_key": "00112233445566778899aabbccddeeff",
                "channel": "26",
                "heartbeat_period_duration": "60",
            },
            "required_fields": [
                {"name": "aes_key", "type": "string", "required": True},
                {"name": "channel", "type": "integer", "required": True},
                {"name": "heartbeat_period_duration", "type": "integer", "required": True},
            ],
        },
        timeout=7.5,
    )

    # The integer fields are coerced before being handed to the init transport.
    assert captured["field_values"] == {
        "aes_key": "00112233445566778899aabbccddeeff",
        "channel": 26,
        "heartbeat_period_duration": 60,
    }


def _openapi_spec(**overrides):
    """A minimal contract that passes validate_contract's required checks."""
    spec = {
        "info": {"title": "SparkNet-Http", "version": "1.2.3"},
        "paths": {"/v1/commands": {}, "/v1/events": {}},
        "x-open-thunder": {"default_interface": "http", "interfaces": []},
    }
    spec.update(overrides)
    return spec


def _use_temp_config_root(monkeypatch, tmp_path):
    """Redirect the module's config directory globals at a temp location."""
    monkeypatch.setattr(provider_settings, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(provider_settings, "_METER_DRIVER_CONFIG_DIR", tmp_path / "meter_driver_configs")


# ---------------------------------------------------------------------------
# JSON-pointer / schema resolution helpers
# ---------------------------------------------------------------------------


def test_resolve_local_ref_rejects_non_local_refs():
    assert provider_settings._resolve_local_ref({}, "") is None
    assert provider_settings._resolve_local_ref({}, "https://x/y") is None


def test_resolve_local_ref_walks_and_unescapes_tokens():
    spec = {"components": {"sch~emas": {"a/b": {"leaf": 1}}}}
    # ~0 -> "~" and ~1 -> "/" per RFC 6901.
    assert provider_settings._resolve_local_ref(spec, "#/components/sch~0emas/a~1b") == {"leaf": 1}


def test_resolve_local_ref_returns_none_for_missing_node():
    assert provider_settings._resolve_local_ref({"a": {}}, "#/a/missing") is None


def test_resolve_schema_handles_non_dict_ref_and_plain():
    assert provider_settings._resolve_schema({}, "not-a-dict") == {}
    spec = {"components": {"schemas": {"Foo": {"type": "object"}}}}
    assert provider_settings._resolve_schema(spec, {"$ref": "#/components/schemas/Foo"}) == {"type": "object"}
    assert provider_settings._resolve_schema({}, {"$ref": "#/nope"}) == {}
    assert provider_settings._resolve_schema({}, {"type": "string"}) == {"type": "string"}


def test_command_type_values_reads_const_and_enum():
    assert provider_settings._command_type_values({}, {"properties": {"command_type": {"const": "Foo"}}}) == {
        "foo"
    }
    values = provider_settings._command_type_values(
        {}, {"properties": {"command_type": {"enum": ["A", " b ", ""]}}}
    )
    assert values == {"a", "b"}


def test_find_configure_provider_schema_falls_back_to_components():
    spec = {
        "paths": {},
        "components": {
            "schemas": {
                "Other": {"properties": {"command_type": {"const": "noop"}}},
                "Cfg": {
                    "properties": {
                        "command_type": {"const": "configure_provider"},
                        "vendor_options": {"type": "object"},
                    }
                },
            }
        },
    }
    schema = provider_settings._find_configure_provider_schema(spec)
    assert "vendor_options" in schema.get("properties", {})


def test_find_configure_provider_schema_returns_empty_when_absent():
    assert provider_settings._find_configure_provider_schema({"paths": {}, "components": {}}) == {}


# ---------------------------------------------------------------------------
# Requirement discovery helpers
# ---------------------------------------------------------------------------


def test_fetch_requirements_payload_rejects_non_object(monkeypatch):
    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: FakeResponse(["nope"]))
    with pytest.raises(provider_settings.ProviderRegistrationError):
        provider_settings._fetch_requirements_payload("http://127.0.0.1:18080")


def test_iter_candidate_requirement_schemas_skips_non_dicts_and_bounds_depth():
    # Nest object schemas deeper than the depth-6 walk bound: the marker
    # property sits at nesting depth 7 and must NOT be yielded, while the
    # wrapper one level shallower (depth 6) still is.
    nested = {"properties": {"deep_marker": {"type": "string"}}}
    for level in range(7):
        nested = {"properties": {"wrap_{}".format(level): nested}}

    spec = {
        "components": {"schemas": {"Root": nested}},
        "paths": {
            "/v1/commands": "not-a-dict",  # non-dict path item is skipped
            "/v1/events": {"post": "not-a-dict"},  # non-dict operation is skipped
        },
    }

    property_sets = [
        set(s.get("properties") or {}) for s in provider_settings._iter_candidate_requirement_schemas(spec)
    ]

    # The innermost wrapper (holding "wrap_0") is yielded at depth 6.
    assert {"wrap_0"} in property_sets
    # The schema one level deeper (holding "deep_marker") is beyond the bound.
    assert not any("deep_marker" in properties for properties in property_sets)


def test_iter_candidate_requirement_schemas_skips_ref_to_non_dict():
    # A component schema whose $ref resolves to a non-dict (a list here) must
    # be skipped by the walk rather than treated as a properties-bearing schema.
    spec = {
        "components": {"schemas": {"Bad": {"$ref": "#/x/list"}}},
        "x": {"list": [1, 2, 3]},
        "paths": {},
    }
    assert list(provider_settings._iter_candidate_requirement_schemas(spec)) == []


def test_extract_fields_from_requirements_uses_standard_type_hints():
    # No component schema describes these, so the standard hints supply types.
    fields = provider_settings._extract_fields_from_requirements(
        {"components": {}, "paths": {}}, ["channel", "aes_key"]
    )
    by_name = {field["name"]: field for field in fields}
    assert by_name["channel"]["type"] == "integer"
    assert by_name["aes_key"]["type"] == "string"
    assert by_name["channel"]["required"] is True


def test_extract_driver_requirement_fields_returns_empty_without_vendor_options(monkeypatch):
    # A contract with no configure-provider schema advertises no requirements.
    assert provider_settings._extract_driver_requirement_fields("http://x", {"paths": {}}) == []


def test_extract_driver_requirement_fields_falls_back_on_requirements_error(monkeypatch):
    spec = {
        "paths": {
            "/v1/commands": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"oneOf": [{"$ref": "#/components/schemas/Cfg"}]}}
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Cfg": {
                    "properties": {
                        "command_type": {"const": "configure_provider"},
                        "vendor_options": {
                            "required": ["aes_key"],
                            "properties": {"aes_key": {"type": "string"}},
                        },
                    }
                }
            }
        },
    }

    def boom(url, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(provider_settings.httpx, "get", boom)
    fields = provider_settings._extract_driver_requirement_fields("http://x", spec)
    assert [field["name"] for field in fields] == ["aes_key"]


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------


def test_normalize_base_url_strips_openapi_and_trailing_slash():
    assert provider_settings.normalize_base_url("http://h:1/openapi.json") == "http://h:1"
    assert provider_settings.normalize_base_url("http://h:1/") == "http://h:1"


def test_normalize_base_url_requires_url_and_scheme():
    with pytest.raises(provider_settings.ProviderRegistrationError):
        provider_settings.normalize_base_url("   ")
    with pytest.raises(provider_settings.ProviderRegistrationError):
        provider_settings.normalize_base_url("127.0.0.1:8080")


def test_get_openapi_url_appends_suffix():
    assert provider_settings.get_openapi_url("http://h:1/") == "http://h:1/openapi.json"


# ---------------------------------------------------------------------------
# Interface metadata
# ---------------------------------------------------------------------------


def test_normalize_interface_metadata_injects_http_and_dedups():
    spec = {
        "x-open-thunder": {
            "default_interface": "grpc",
            "interfaces": [
                "not-a-dict",
                {"type": ""},
                {"type": "grpc", "target": "10.0.0.1:9090"},
                {"type": "grpc", "target": "dup"},
                {"type": "mqtt", "base_url": "mqtt://host"},
            ],
        }
    }
    details = provider_settings._normalize_interface_metadata("http://base", spec)
    by_type = {interface["type"]: interface for interface in details["interfaces"]}
    # http is always synthesized and placed first.
    assert details["interfaces"][0]["type"] == "http"
    assert by_type["grpc"]["address"] == "10.0.0.1:9090"
    assert by_type["mqtt"]["address"] == "mqtt://host"
    assert details["default_interface"] == "grpc"


def test_normalize_interface_metadata_blank_address_without_target_or_base_url():
    # An advertised interface that declares neither base_url nor target still
    # appears, but with an empty address.
    spec = {
        "x-open-thunder": {
            "default_interface": "http",
            "interfaces": [{"type": "mqtt", "label": "MQTT"}],
        }
    }
    details = provider_settings._normalize_interface_metadata("http://base", spec)
    by_type = {interface["type"]: interface for interface in details["interfaces"]}
    assert by_type["mqtt"]["address"] == ""
    assert "base_url" not in by_type["mqtt"]
    assert "target" not in by_type["mqtt"]


def test_normalize_interface_metadata_defaults_to_http_when_unknown():
    spec = {"x-open-thunder": {"default_interface": "carrier-pigeon", "interfaces": []}}
    details = provider_settings._normalize_interface_metadata("http://base", spec)
    assert details["default_interface"] == "http"


def test_apply_selected_interface_falls_back_to_default_when_invalid():
    details = {
        "interfaces": [{"type": "http"}, {"type": "grpc"}],
        "default_interface": "grpc",
    }
    applied = provider_settings._apply_selected_interface(dict(details), selected_interface="carrier")
    assert applied["selected_interface"] == "grpc"
    assert applied["selected_interface_details"]["type"] == "grpc"


def test_apply_selected_interface_uses_explicit_selection():
    details = {"interfaces": [{"type": "http"}, {"type": "grpc"}], "default_interface": "http"}
    applied = provider_settings._apply_selected_interface(dict(details), selected_interface="grpc")
    assert applied["selected_interface"] == "grpc"


def test_fallback_interface_metadata_includes_non_http_selection():
    details = provider_settings._fallback_interface_metadata("http://base", selected_interface="grpc")
    types = [interface["type"] for interface in details["interfaces"]]
    assert types == ["http", "grpc"]
    assert details["selected_interface"] == "grpc"
    assert details["openapi_url"] == "http://base/openapi.json"


# ---------------------------------------------------------------------------
# validate_contract error paths
# ---------------------------------------------------------------------------


def test_validate_contract_wraps_http_errors(monkeypatch):
    def boom(url, timeout):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(provider_settings.httpx, "get", boom)
    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")
    assert "could not fetch" in str(exc.value)


def test_validate_contract_rejects_invalid_json(monkeypatch):
    class BadJSON(FakeResponse):
        def json(self):
            raise ValueError("bad")

    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: BadJSON({}))
    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")
    assert "invalid JSON" in str(exc.value)


def test_validate_contract_requires_info_title(monkeypatch):
    spec = _openapi_spec(info={})
    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: FakeResponse(spec))
    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")
    assert "info.title" in str(exc.value)


# ---------------------------------------------------------------------------
# Live interface details / runtime status
# ---------------------------------------------------------------------------


def test_get_live_interface_details_falls_back_on_registration_error(monkeypatch):
    def boom(url, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(provider_settings.httpx, "get", boom)
    details = provider_settings.get_live_interface_details(
        "http://127.0.0.1:18080", selected_interface="grpc"
    )
    assert details["error"]
    assert details["selected_interface"] == "grpc"


def test_get_live_interface_details_applies_selection_on_success(monkeypatch):
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_openapi_get)
    details = provider_settings.get_live_interface_details("http://127.0.0.1:18080")
    assert details["selected_interface"] == "http"


def test_get_runtime_status_reports_gateway_when_connected(monkeypatch):
    def fake_get(url, timeout):
        if url.endswith("/v1/status"):
            return FakeResponse({"connected": True, "gateway_type": "sparknet"})
        return FakeResponse({})

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is True
    assert status["gateway_active"] is True
    assert status["gateway_type"] == "sparknet"
    assert status["checked_url"].endswith("/v1/healthz")


def test_get_runtime_status_can_skip_gateway_probe(monkeypatch):
    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: FakeResponse({}))
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080", include_gateway_status=False)
    assert status["online"] is True
    assert status["gateway_active"] is False
    assert status["gateway_checked"] is False


def test_get_runtime_status_tolerates_gateway_probe_failure(monkeypatch):
    def fake_get(url, timeout):
        if url.endswith("/v1/status"):
            raise httpx.ConnectError("no status")
        return FakeResponse({})

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is True
    assert status["gateway_active"] is False
    assert status["gateway_checked"] is True


def test_get_runtime_status_falls_back_to_legacy_health(monkeypatch):
    def fake_get(url, timeout):
        if url.endswith("/v1/healthz"):
            raise httpx.ConnectError("no healthz")
        if url.endswith("/health"):
            return FakeResponse({})
        if url.endswith("/v1/status"):
            return FakeResponse({"connected": False})
        return FakeResponse({})

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is True
    assert status["checked_url"].endswith("/health")


def test_get_runtime_status_reports_offline_when_unreachable(monkeypatch):
    def fake_get(url, timeout):
        raise httpx.ConnectError("nothing here")

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is False
    assert status["gateway_active"] is False
    assert "nothing here" in status["message"]


# ---------------------------------------------------------------------------
# Driver config file helpers
# ---------------------------------------------------------------------------


def test_cleanup_orphaned_driver_config_files_removes_unknown(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    config_dir = tmp_path / "meter_driver_configs"
    config_dir.mkdir()
    (config_dir / "keep.json").write_text("{}")
    (config_dir / "orphan.json").write_text("{}")

    provider_settings._cleanup_orphaned_driver_config_files([{"id": "keep"}])

    assert (config_dir / "keep.json").exists()
    assert not (config_dir / "orphan.json").exists()


def test_cleanup_orphaned_driver_config_files_swallows_unlink_errors(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    config_dir = tmp_path / "meter_driver_configs"
    config_dir.mkdir()
    (config_dir / "orphan.json").write_text("{}")

    def boom(self, *args, **kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(provider_settings.Path, "unlink", boom)
    # A failure to remove a stale file is swallowed; the call returns cleanly.
    provider_settings._cleanup_orphaned_driver_config_files([])
    assert (config_dir / "orphan.json").exists()


def test_cleanup_orphaned_driver_config_files_noop_without_directory(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    # Directory does not exist; the call must simply return.
    provider_settings._cleanup_orphaned_driver_config_files([{"id": "x"}])


def test_load_existing_driver_config_variants(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    assert provider_settings._load_existing_driver_config("") == {}
    assert provider_settings._load_existing_driver_config("meter_driver_configs/missing.json") == {}

    config_dir = tmp_path / "meter_driver_configs"
    config_dir.mkdir()
    (config_dir / "bad.json").write_text("{not json")
    assert provider_settings._load_existing_driver_config("meter_driver_configs/bad.json") == {}
    (config_dir / "list.json").write_text("[1, 2]")
    assert provider_settings._load_existing_driver_config("meter_driver_configs/list.json") == {}
    (config_dir / "ok.json").write_text('{"a": 1}')
    assert provider_settings._load_existing_driver_config("meter_driver_configs/ok.json") == {"a": 1}


def test_get_provider_config_abspath_handles_blank_id(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    assert provider_settings.get_provider_config_abspath({"id": ""}) == ""
    path = provider_settings.get_provider_config_abspath({"id": "abc"})
    assert path.endswith("meter_driver_configs/abc.json")


def test_load_provider_runtime_settings_reads_file(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    assert provider_settings.load_provider_runtime_settings({"id": ""}) == {}
    config_dir = tmp_path / "meter_driver_configs"
    config_dir.mkdir()
    (config_dir / "abc.json").write_text('{"field_values": {"channel": 11}}')
    assert provider_settings.load_provider_runtime_settings({"id": "abc"}) == {
        "field_values": {"channel": 11}
    }


def test_load_provider_config_text_synthesizes_when_missing(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    assert provider_settings.load_provider_config_text({"id": ""}) == "{}\n"

    text = provider_settings.load_provider_config_text(
        {"id": "abc", "name": "Driver", "base_url": "http://x", "selected_interface": "http"}
    )
    payload = json.loads(text)
    assert payload["driver"]["id"] == "abc"
    assert payload["init_status"]["has_successful_init"] is False


def test_load_provider_config_text_returns_existing_file(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    config_dir = tmp_path / "meter_driver_configs"
    config_dir.mkdir()
    (config_dir / "abc.json").write_text('{"custom": true}\n')
    assert provider_settings.load_provider_config_text({"id": "abc"}) == '{"custom": true}\n'


def test_write_driver_config_file_merges_previous_field_values(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    config_dir = tmp_path / "meter_driver_configs"
    config_dir.mkdir()
    (config_dir / "abc.json").write_text(
        json.dumps({"field_values": {"channel": 20}, "init_status": {"has_successful_init": True}})
    )

    provider_record = {
        "id": "abc",
        "selected_interface": "http",
        "selected_interface_target": "",
        "enabled": True,
    }
    details = {
        "name": "Driver",
        "base_url": "http://x",
        "openapi_url": "http://x/openapi.json",
        "service_version": "1.0",
        "driver_requirement_fields": [
            {"name": "channel", "default": 11},
            {"name": "aes_key", "default": None},
        ],
    }
    provider_settings._write_driver_config_file(provider_record, details)

    written = json.loads((config_dir / "abc.json").read_text())
    # Previous channel value is preserved; aes_key falls back to "" (no default).
    assert written["field_values"] == {"channel": 20, "aes_key": ""}
    # A previously-successful init status carries through.
    assert written["init_status"]["has_successful_init"] is True


# ---------------------------------------------------------------------------
# Config text parsing / validation / coercion
# ---------------------------------------------------------------------------


def test_parse_provider_config_text_errors():
    with pytest.raises(provider_settings.DriverConfigError):
        provider_settings.parse_provider_config_text("{not json")
    with pytest.raises(provider_settings.DriverConfigError):
        provider_settings.parse_provider_config_text("[1, 2]")
    assert provider_settings.parse_provider_config_text('{"a": 1}') == {"a": 1}


def test_required_field_helpers_reject_wrong_types():
    with pytest.raises(provider_settings.DriverConfigError):
        provider_settings._required_field_names({"required_fields": "nope"})
    with pytest.raises(provider_settings.DriverConfigError):
        provider_settings._field_values({"field_values": "nope"})
    with pytest.raises(provider_settings.DriverConfigError):
        provider_settings._required_field_specs({"required_fields": "nope"})


def test_required_field_names_accepts_dicts_and_strings():
    names = provider_settings._required_field_names(
        {"required_fields": [{"name": "aes_key"}, "channel", {"name": ""}, "  "]}
    )
    assert names == ["aes_key", "channel"]


def test_coerce_field_value_by_type():
    assert provider_settings._coerce_field_value("c", "26", {"type": "integer"}) == 26
    assert provider_settings._coerce_field_value("r", "1.5", {"type": "number"}) == 1.5
    assert provider_settings._coerce_field_value("b", "yes", {"type": "boolean"}) is True
    assert provider_settings._coerce_field_value("b", "off", {"type": "boolean"}) is False
    assert provider_settings._coerce_field_value("b", True, {"type": "boolean"}) is True
    assert provider_settings._coerce_field_value("s", "kept", {"type": "string"}) == "kept"


def test_coerce_field_value_raises_on_bad_input():
    with pytest.raises(provider_settings.DriverConfigError):
        provider_settings._coerce_field_value("c", "nope", {"type": "integer"})
    with pytest.raises(provider_settings.DriverConfigError):
        provider_settings._coerce_field_value("r", "nope", {"type": "number"})
    with pytest.raises(provider_settings.DriverConfigError):
        provider_settings._coerce_field_value("b", "maybe", {"type": "boolean"})


def test_validate_provider_config_payload_reports_missing_and_coerces():
    with pytest.raises(provider_settings.DriverConfigError) as exc:
        provider_settings.validate_provider_config_payload(
            {"required_fields": ["channel"], "field_values": {"channel": ""}}
        )
    assert "missing values" in str(exc.value)

    validated = provider_settings.validate_provider_config_payload(
        {
            "required_fields": [{"name": "channel", "type": "integer"}],
            "field_values": {"channel": "26"},
        }
    )
    assert validated["field_values"]["channel"] == 26


def test_normalize_init_status_defaults_for_bad_input():
    assert provider_settings._normalize_init_status({"init_status": "nope"}) == {
        "has_successful_init": False,
        "last_init_succeeded": False,
        "last_init_error": "",
    }
    assert provider_settings._normalize_init_status(
        {"init_status": {"has_successful_init": True, "last_init_error": "x"}}
    ) == {"has_successful_init": True, "last_init_succeeded": False, "last_init_error": "x"}


def test_save_provider_config_text_writes_normalized_file(monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    (tmp_path / "meter_driver_configs").mkdir()
    provider = {"id": "abc"}
    config_text = json.dumps(
        {
            "required_fields": [{"name": "channel", "type": "integer"}],
            "field_values": {"channel": "26"},
        }
    )
    payload, validated = provider_settings.save_provider_config_text(provider, config_text)
    assert validated["field_values"]["channel"] == 26
    assert payload["init_status"]["has_successful_init"] is False
    on_disk = json.loads((tmp_path / "meter_driver_configs" / "abc.json").read_text())
    assert on_disk["field_values"]["channel"] == "26"


# ---------------------------------------------------------------------------
# Driver initialization
# ---------------------------------------------------------------------------


def _init_payload():
    return {
        "field_values": {"aes_key": "00112233445566778899aabbccddeeff", "channel": "26"},
        "required_fields": [
            {"name": "aes_key", "type": "string", "required": True},
            {"name": "channel", "type": "integer", "required": True},
        ],
    }


def test_init_provider_from_payload_records_success(monkeypatch, tmp_path):
    import sparkmeter.metering.runtime_client as runtime_client

    config_file = tmp_path / "driver.json"
    monkeypatch.setattr(runtime_client, "initialize_provider_sync", lambda *a, **k: None)
    monkeypatch.setattr(provider_settings, "get_live_interface_details", lambda *a, **k: {})
    monkeypatch.setattr(provider_settings, "get_provider_config_abspath", lambda provider: str(config_file))

    provider_settings.init_provider_from_payload({"base_url": "http://x", "name": "Driver"}, _init_payload())

    status = json.loads(config_file.read_text())["init_status"]
    assert status["has_successful_init"] is True
    assert status["last_init_succeeded"] is True
    assert status["last_init_error"] == ""


def test_init_provider_from_payload_records_failure(monkeypatch, tmp_path):
    import sparkmeter.metering.runtime_client as runtime_client

    config_file = tmp_path / "driver.json"

    def boom(*a, **k):
        raise RuntimeError("transport exploded")

    monkeypatch.setattr(runtime_client, "initialize_provider_sync", boom)
    monkeypatch.setattr(provider_settings, "get_live_interface_details", lambda *a, **k: {})
    monkeypatch.setattr(provider_settings, "get_provider_config_abspath", lambda provider: str(config_file))

    with pytest.raises(provider_settings.DriverInitializationError) as exc:
        provider_settings.init_provider_from_payload({"base_url": "http://x"}, _init_payload())
    assert "transport exploded" in str(exc.value)

    status = json.loads(config_file.read_text())["init_status"]
    assert status["last_init_succeeded"] is False
    assert status["last_init_error"] == "transport exploded"


def test_init_provider_from_payload_handles_detailless_failure(monkeypatch, tmp_path):
    import sparkmeter.metering.runtime_client as runtime_client

    config_file = tmp_path / "driver.json"

    def boom(*a, **k):
        raise RuntimeError("")

    monkeypatch.setattr(runtime_client, "initialize_provider_sync", boom)
    monkeypatch.setattr(provider_settings, "get_live_interface_details", lambda *a, **k: {})
    monkeypatch.setattr(provider_settings, "get_provider_config_abspath", lambda provider: str(config_file))

    with pytest.raises(provider_settings.DriverInitializationError) as exc:
        provider_settings.init_provider_from_payload({"base_url": "http://x"}, _init_payload())
    assert str(exc.value) == "driver init failed"


def test_get_provider_init_status_reads_persisted_state(monkeypatch):
    monkeypatch.setattr(
        provider_settings,
        "load_provider_runtime_settings",
        lambda provider: {"init_status": {"has_successful_init": True}},
    )
    assert provider_settings.get_provider_init_status({"id": "abc"})["has_successful_init"] is True


def test_initialize_configured_providers_on_startup_covers_each_outcome(monkeypatch):
    providers = [
        {"id": "missing"},
        {"id": "invalid"},
        {"id": "initfail"},
        {"id": "ok"},
    ]
    payloads = {
        "missing": {},
        "invalid": {"bad": True},
        "initfail": {"ok": True},
        "ok": {"ok": True},
    }
    monkeypatch.setattr(provider_settings, "get_saved_providers", lambda: providers)
    monkeypatch.setattr(
        provider_settings, "load_provider_runtime_settings", lambda provider: payloads[provider["id"]]
    )

    def fake_validate(payload):
        if payload == {"bad": True}:
            raise provider_settings.DriverConfigError("bad config")

    def fake_init(provider, payload, timeout=10.0):
        if provider["id"] == "initfail":
            raise provider_settings.DriverInitializationError("init boom")

    monkeypatch.setattr(provider_settings, "validate_provider_config_payload", fake_validate)
    monkeypatch.setattr(provider_settings, "init_provider_from_payload", fake_init)

    results = {r["provider"]["id"]: r for r in provider_settings.initialize_configured_providers_on_startup()}
    assert results["missing"] == {
        "provider": {"id": "missing"},
        "attempted": False,
        "success": False,
        "reason": "missing config payload",
    }
    assert results["invalid"]["attempted"] is False
    assert results["invalid"]["reason"] == "bad config"
    assert results["initfail"]["attempted"] is True
    assert results["initfail"]["success"] is False
    assert results["ok"]["success"] is True


# ---------------------------------------------------------------------------
# Persistence (DB-backed)
# ---------------------------------------------------------------------------


def test_create_parameter_if_missing_is_idempotent_and_guards_unknown(session):
    first = provider_settings._create_parameter_if_missing("metering-providers")
    second = provider_settings._create_parameter_if_missing("metering-providers")
    assert first.name == "metering-providers"
    assert second.id == first.id
    with pytest.raises(RuntimeError):
        provider_settings._create_parameter_if_missing("no-such-parameter-xyz")


def test_create_parameter_if_missing_creates_known_absent_parameter(session):
    from sparkmeter.config.configdomain import ConfigParameter

    # Ensure a known parameter is absent, then confirm it is created on demand.
    existing = ConfigParameter.get_by_name("send-broadcast-signal")
    if existing is not None:
        session.delete(existing)
        session.flush()
    assert ConfigParameter.get_by_name("send-broadcast-signal") is None

    created = provider_settings._create_parameter_if_missing("send-broadcast-signal")
    assert created.name == "send-broadcast-signal"
    assert ConfigParameter.get_by_name("send-broadcast-signal") is not None


def test_get_saved_providers_handles_blank_invalid_and_non_dict(session):
    parameter = provider_settings._providers_parameter()

    parameter.value = "   "
    session.flush()
    assert provider_settings.get_saved_providers() == []

    parameter.value = "{not json"
    session.flush()
    assert provider_settings.get_saved_providers() == []

    parameter.value = json.dumps([42, {"id": "abc", "base_url": "http://x"}])
    session.flush()
    saved = provider_settings.get_saved_providers()
    assert len(saved) == 1
    assert saved[0]["id"] == "abc"
    assert saved[0]["selected_interface"] == "http"
    assert saved[0]["enabled"] is True


def test_save_and_lookup_providers_roundtrip(session, monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_openapi_get)

    provider_id = provider_settings.save_provider_settings("http://127.0.0.1:18080", "http")
    session.flush()

    assert provider_settings.get_provider(provider_id)["base_url"] == "http://127.0.0.1:18080"
    assert provider_settings.get_provider("nonexistent") is None
    assert provider_settings.get_enabled_provider()["id"] == provider_id


def test_save_provider_settings_replaces_existing_by_id(session, monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_openapi_get)

    provider_id = provider_settings.save_provider_settings("http://127.0.0.1:18080", "http")
    session.flush()
    # Saving again with the same id replaces rather than appends.
    provider_settings.save_provider_settings("http://127.0.0.1:28080", "http", provider_id=provider_id)
    session.flush()

    providers = provider_settings.get_saved_providers()
    assert len(providers) == 1
    assert providers[0]["base_url"] == "http://127.0.0.1:28080"


def test_save_provider_settings_preserves_other_providers(session, monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_openapi_get)

    first_id = provider_settings.save_provider_settings("http://127.0.0.1:18080", "http")
    session.flush()
    second_id = provider_settings.save_provider_settings("http://127.0.0.1:28080", "http")
    session.flush()

    # Re-saving the first provider must carry the unrelated second one through.
    provider_settings.save_provider_settings("http://127.0.0.1:19090", "http", provider_id=first_id)
    session.flush()

    providers = {p["id"]: p for p in provider_settings.get_saved_providers()}
    assert set(providers) == {first_id, second_id}
    assert providers[first_id]["base_url"] == "http://127.0.0.1:19090"
    assert providers[second_id]["base_url"] == "http://127.0.0.1:28080"


def test_save_provider_settings_falls_back_for_invalid_interface(session, monkeypatch, tmp_path):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_openapi_get)

    # "grpc" is not advertised by _fake_openapi_get, so it falls back to http.
    provider_id = provider_settings.save_provider_settings("http://127.0.0.1:18080", "grpc")
    session.flush()
    assert provider_settings.get_provider(provider_id)["selected_interface"] == "http"
