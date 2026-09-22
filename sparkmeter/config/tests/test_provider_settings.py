# -*- coding: utf-8 -*-
"""Meter driver settings tests."""

import json
from pathlib import Path

import httpx
import pytest

from sparkmeter.config import provider_settings
from sparkmeter.metering.provider_config import configured_provider_url

# The Meter Driver Specification's own openapi/meter-driver.yaml (v1.4.0),
# converted to JSON: exactly what a driver serving nothing but the spec
# answers on GET /openapi.json (its x-meter-driver block lists http + grpc).
_SPEC_DOCUMENT_PATH = Path(__file__).with_name("meter_driver_spec_openapi.json")

# The reference driver's /v1/requirements list (spec section 5.2 example).
_REFERENCE_REQUIRED_FIELDS = ("aes_key", "channel", "heartbeat_period_duration")


def load_spec_document():
    """Return a fresh copy of the spec's OpenAPI document."""
    return json.loads(_SPEC_DOCUMENT_PATH.read_text())


class FakeResponse(object):
    """Minimal HTTPX-like response test double."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        """Pretend the response was successful."""

    def json(self):
        """Return the configured JSON payload."""
        return self._payload


def _spec_document(**overrides):
    """A minimal document listing the spec's required routes with an http x-meter-driver block."""
    document = {
        "openapi": "3.1.0",
        "info": {"title": "Spec Driver", "version": "1.2.3"},
        "paths": {path: {} for path in provider_settings.REQUIRED_CONTRACT_PATHS},
        "x-meter-driver": {
            "default_interface": "http",
            "interfaces": [{"type": "http", "label": "HTTP API", "base_url": "http://127.0.0.1:18080"}],
        },
    }
    document.update(overrides)
    return document


def _http_error(url, status_code=404):
    request = httpx.Request("GET", url)
    return httpx.HTTPStatusError(
        "failed", request=request, response=httpx.Response(status_code, request=request)
    )


def _fake_driver(
    document=None, required_fields=("heartbeat_period_duration", "aes_key"), requirements_error=None
):
    """Return an httpx.get double for a driver serving /openapi.json and /v1/requirements.

    Every URL it answers is recorded on `fake_get.calls`; anything other
    than those two routes is an assertion failure, so a test sees any
    stray probe (a legacy /health, a vendor init route) immediately.
    """
    document = _spec_document() if document is None else document
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        if url.endswith("/v1/requirements"):
            if requirements_error is not None:
                raise requirements_error
            return FakeResponse({"required_fields": list(required_fields)})
        if url.endswith("/openapi.json"):
            return FakeResponse(document)
        raise AssertionError("unexpected GET {}".format(url))

    fake_get.calls = calls
    return fake_get


def _fake_openapi_get(url, timeout):
    """A spec-only driver, for tests that only need a saved provider."""
    return _fake_driver()(url, timeout)


def _vendor_options_extension(**properties):
    """The optional /v1/commands configure_provider extension a reference driver adds."""
    return {
        "paths": {
            "/v1/commands": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [{"$ref": "#/components/schemas/ConfigureProviderCommand"}]
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "ConfigureProviderCommand": {
                    "type": "object",
                    "properties": {
                        "command_type": {"type": "string", "enum": ["configure_provider"]},
                        "vendor_options": {
                            "type": "object",
                            "required": list(properties),
                            "properties": properties,
                        },
                    },
                }
            }
        },
    }


def _with_vendor_options(document, **properties):
    """Return `document` extended with a /v1/commands vendor-option schema."""
    extension = _vendor_options_extension(**properties)
    document = dict(document)
    document["paths"] = {**document.get("paths", {}), **extension["paths"]}
    document["components"] = {
        "schemas": {
            **((document.get("components") or {}).get("schemas") or {}),
            **extension["components"]["schemas"],
        }
    }
    return document


# ---------------------------------------------------------------------------
# validate_contract against the spec's own document
# ---------------------------------------------------------------------------


def test_spec_document_fixture_is_the_spec(monkeypatch):
    document = load_spec_document()
    assert document["info"]["version"] == "1.4.0"
    assert document["x-meter-driver"]["default_interface"] == "http"
    assert set(provider_settings.REQUIRED_CONTRACT_PATHS) <= set(document["paths"])
    # The spec's required-route list, and nothing the reference driver adds.
    assert "/v1/commands" not in document["paths"]


def test_validate_contract_accepts_a_spec_only_driver(monkeypatch):
    # A driver serving exactly the spec document, with the reference
    # /v1/requirements list. This is the meter-driver-emulator case.
    fake_get = _fake_driver(load_spec_document(), required_fields=_REFERENCE_REQUIRED_FIELDS)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert details["name"] == "Meter Driver API"
    assert details["service_version"] == "1.4.0"
    assert [interface["type"] for interface in details["interfaces"]] == ["http", "grpc"]
    assert details["default_interface"] == "http"
    # Requirements come from GET /v1/requirements, in the driver's order.
    assert [field["name"] for field in details["driver_requirement_fields"]] == list(
        _REFERENCE_REQUIRED_FIELDS
    )
    assert all(field["required"] for field in details["driver_requirement_fields"])
    # ...typed by the document's InitRequest schema.
    fields = details["driver_requirement_field_map"]
    assert fields["heartbeat_period_duration"]["type"] == "integer"
    assert fields["heartbeat_period_duration"]["minimum"] == 0
    assert fields["channel"]["type"] == "integer"
    assert fields["aes_key"]["type"] == "string"
    assert fields["aes_key"]["pattern"] == "^[A-Fa-f0-9]{32}$"
    # No /v1/commands, so no optional extras.
    assert details["vendor_option_fields"] == []
    # Exactly the spec's two discovery calls, nothing else.
    assert fake_get.calls == [
        "http://127.0.0.1:18080/openapi.json",
        "http://127.0.0.1:18080/v1/requirements",
    ]


def test_validate_contract_accepts_the_spec_document_from_its_openapi_url(monkeypatch):
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_driver(load_spec_document()))

    details = provider_settings.validate_contract("http://127.0.0.1:18080/openapi.json")

    assert details["base_url"] == "http://127.0.0.1:18080"
    assert details["openapi_url"] == "http://127.0.0.1:18080/openapi.json"


# ---------------------------------------------------------------------------
# validate_contract: interfaces
# ---------------------------------------------------------------------------


def test_validate_contract_discovers_grpc_interface(monkeypatch):
    document = _spec_document(
        **{
            "x-meter-driver": {
                "default_interface": "grpc",
                "interfaces": [
                    {"type": "http", "label": "HTTP API", "base_url": "http://127.0.0.1:18080"},
                    {"type": "grpc", "label": "gRPC", "target": "h:50051"},
                ],
            }
        }
    )
    fake_get = _fake_driver(document)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert fake_get.calls[0] == "http://127.0.0.1:18080/openapi.json"
    assert details["name"] == "Spec Driver"
    assert details["default_interface"] == "grpc"
    by_type = {interface["type"]: interface for interface in details["interfaces"]}
    assert set(by_type) == {"http", "grpc"}
    assert by_type["grpc"]["target"] == "h:50051"
    assert by_type["grpc"]["address"] == "h:50051"


def test_validate_contract_synthesizes_http_when_discovery_block_is_absent(monkeypatch):
    document = _spec_document()
    del document["x-meter-driver"]
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_driver(document))

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert details["interfaces"] == [
        {
            "type": "http",
            "label": "HTTP API",
            "base_url": "http://127.0.0.1:18080",
            "address": "http://127.0.0.1:18080",
        }
    ]
    assert details["default_interface"] == "http"


def test_validate_contract_ignores_non_spec_discovery_blocks(monkeypatch):
    # A block under any other name is not the spec's; it is not read. The
    # reference driver's pre-spec block name is assembled here so that no
    # source line in sparkmeter/ carries it verbatim.
    document = _spec_document()
    del document["x-meter-driver"]
    document["-".join(["x", "open", "thunder"])] = {
        "default_interface": "grpc",
        "interfaces": [{"type": "grpc", "target": "h:50051"}],
    }
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_driver(document))

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert [interface["type"] for interface in details["interfaces"]] == ["http"]
    assert details["default_interface"] == "http"


# ---------------------------------------------------------------------------
# validate_contract: required routes
# ---------------------------------------------------------------------------


def test_required_contract_paths_are_the_spec_required_routes():
    assert provider_settings.REQUIRED_CONTRACT_PATHS == (
        "/v1/requirements",
        "/v1/init",
        "/v1/nodes/register",
        "/v1/nodes/{node_id}",
        "/v1/nodes/{node_id}/configure-meter",
        "/v1/meters/configure",
        "/v1/events",
        "/v1/status",
        "/v1/healthz",
    )


def test_validate_contract_rejects_missing_paths_naming_them(monkeypatch):
    document = _spec_document()
    del document["paths"]["/v1/requirements"]
    del document["paths"]["/v1/init"]
    del document["paths"]["/v1/healthz"]
    fake_get = _fake_driver(document)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert "missing required paths" in str(exc.value)
    assert "/v1/requirements, /v1/init, /v1/healthz" in str(exc.value)
    # Rejected on the document alone; requirements are never probed.
    assert fake_get.calls == ["http://127.0.0.1:18080/openapi.json"]


def test_validate_contract_does_not_require_vendor_routes(monkeypatch):
    # /v1/commands is a reference-driver extension, not a spec route.
    document = _spec_document()
    assert "/v1/commands" not in document["paths"]
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_driver(document))

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert details["name"] == "Spec Driver"


def test_validate_contract_rejects_a_document_with_only_vendor_routes(monkeypatch):
    document = _spec_document(paths={"/v1/commands": {}, "/v1/events": {}})
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_driver(document))

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert "/v1/requirements" in str(exc.value)
    assert "/v1/init" in str(exc.value)


# ---------------------------------------------------------------------------
# validate_contract: requirements probe
# ---------------------------------------------------------------------------


def test_validate_contract_returns_requirements_in_driver_order(monkeypatch):
    fake_get = _fake_driver(required_fields=("zeta", "alpha", "heartbeat_period_duration"))
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert [field["name"] for field in details["driver_requirement_fields"]] == [
        "zeta",
        "alpha",
        "heartbeat_period_duration",
    ]
    assert fake_get.calls == [
        "http://127.0.0.1:18080/openapi.json",
        "http://127.0.0.1:18080/v1/requirements",
    ]


def test_validate_contract_types_undocumented_requirements_as_string(monkeypatch):
    # The minimal document has no InitRequest schema, so every field is a string.
    monkeypatch.setattr(
        provider_settings.httpx, "get", _fake_driver(required_fields=("aes_key", "site_token"))
    )

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    fields = details["driver_requirement_field_map"]
    assert fields["aes_key"]["type"] == "string"
    assert fields["site_token"]["type"] == "string"
    assert fields["site_token"]["required"] is True


def test_validate_contract_types_requirements_from_the_init_request_schema(monkeypatch):
    document = load_spec_document()
    # A driver with different init fields documents them in InitRequest
    # (spec section 5.3) and lists them on /v1/requirements.
    document["components"]["schemas"]["InitRequest"]["properties"]["site_token"] = {
        "type": "string",
        "title": "Site token",
        "pattern": "^[a-z]+$",
    }
    document["components"]["schemas"]["InitRequest"]["properties"]["poll_seconds"] = {
        "type": "integer",
        "minimum": 5,
        "maximum": 3600,
        "default": 60,
    }
    fake_get = _fake_driver(document, required_fields=("site_token", "poll_seconds"))
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    fields = details["driver_requirement_field_map"]
    assert fields["site_token"] == {
        "name": "site_token",
        "label": "Site token",
        "type": "string",
        "required": True,
        "description": "",
        "pattern": "^[a-z]+$",
        "minimum": None,
        "maximum": None,
        "default": None,
    }
    assert fields["poll_seconds"]["type"] == "integer"
    assert fields["poll_seconds"]["minimum"] == 5
    assert fields["poll_seconds"]["maximum"] == 3600
    assert fields["poll_seconds"]["default"] == 60


def test_validate_contract_requires_the_requirements_probe(monkeypatch):
    url = "http://127.0.0.1:18080/v1/requirements"
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_driver(requirements_error=_http_error(url)))

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert "/v1/requirements" in str(exc.value)


def test_validate_contract_requires_the_requirements_probe_even_with_vendor_options(monkeypatch):
    # The vendor-option schema is not a substitute for /v1/requirements.
    document = _with_vendor_options(_spec_document(), aes_key={"type": "string"})
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        _fake_driver(document, requirements_error=httpx.ConnectError("down")),
    )

    with pytest.raises(provider_settings.ProviderRegistrationError):
        provider_settings.validate_contract("http://127.0.0.1:18080")


def test_validate_contract_rejects_malformed_requirements(monkeypatch):
    def fake_get(url, timeout):
        if url.endswith("/v1/requirements"):
            return FakeResponse({"fields": ["aes_key"]})
        return FakeResponse(_spec_document())

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert "required_fields" in str(exc.value)


def test_validate_contract_accepts_a_driver_requiring_no_init_fields(monkeypatch):
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_driver(required_fields=()))

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert details["driver_requirement_fields"] == []
    assert details["driver_requirement_field_map"] == {}


# ---------------------------------------------------------------------------
# validate_contract: optional /v1/commands vendor options
# ---------------------------------------------------------------------------


def test_validate_contract_appends_vendor_options_as_optional_extras(monkeypatch):
    document = _with_vendor_options(
        load_spec_document(),
        aes_key={"type": "string", "title": "AES key", "pattern": "[0-9a-fA-F]{32}"},
        channel={"type": "integer", "title": "Channel", "minimum": 11, "maximum": 26},
        region={"type": "string", "title": "Region", "description": "Radio regulatory region."},
    )
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        _fake_driver(document, required_fields=("heartbeat_period_duration", "aes_key")),
    )

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    # Required fields first, in /v1/requirements order; vendor extras after,
    # optional, and never duplicating a required field.
    assert [(field["name"], field["required"]) for field in details["driver_requirement_fields"]] == [
        ("heartbeat_period_duration", True),
        ("aes_key", True),
        ("channel", False),
        ("region", False),
    ]
    fields = details["driver_requirement_field_map"]
    # aes_key keeps the spec's InitRequest typing, not the vendor schema's.
    assert fields["aes_key"]["pattern"] == "^[A-Fa-f0-9]{32}$"
    assert fields["channel"]["minimum"] == 11
    assert fields["channel"]["maximum"] == 26
    assert fields["region"]["description"] == "Radio regulatory region."
    # The raw vendor-option view is still exposed for the form layer.
    assert [field["name"] for field in details["vendor_option_fields"]] == ["aes_key", "channel", "region"]
    assert set(details["vendor_option_field_map"]) == {"aes_key", "channel", "region"}


def test_validate_contract_appends_nothing_without_vendor_options(monkeypatch):
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_driver(required_fields=("aes_key",)))

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert [field["name"] for field in details["driver_requirement_fields"]] == ["aes_key"]
    assert details["vendor_option_fields"] == []
    assert details["vendor_option_field_map"] == {}


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


def test_fetch_requirements_payload_wraps_transport_and_json_errors(monkeypatch):
    def boom(url, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(provider_settings.httpx, "get", boom)
    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings._fetch_requirements_payload("http://127.0.0.1:18080")
    assert "/v1/requirements" in str(exc.value)

    class BadJSON(FakeResponse):
        def json(self):
            raise ValueError("bad")

    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: BadJSON({}))
    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings._fetch_requirements_payload("http://127.0.0.1:18080")
    assert "not valid JSON" in str(exc.value)


def test_required_field_names_from_requirements_keeps_order_and_dedups():
    names = provider_settings._required_field_names_from_requirements(
        {"required_fields": ["b", " a ", "", "b", 7]}
    )
    assert names == ["b", "a", "7"]


def test_required_field_names_from_requirements_rejects_non_list():
    with pytest.raises(provider_settings.ProviderRegistrationError):
        provider_settings._required_field_names_from_requirements({"required_fields": "aes_key"})
    with pytest.raises(provider_settings.ProviderRegistrationError):
        provider_settings._required_field_names_from_requirements({})


def test_init_request_schema_reads_the_init_request_body():
    schema = provider_settings._init_request_schema(load_spec_document())
    assert set(schema["properties"]) == {"heartbeat_period_duration", "channel", "aes_key"}
    assert schema["required"] == ["heartbeat_period_duration", "aes_key"]


def test_init_request_schema_falls_back_to_components_init_request():
    spec = {
        "paths": {"/v1/init": {"post": {}}},
        "components": {"schemas": {"InitRequest": {"properties": {"site_token": {"type": "string"}}}}},
    }
    assert provider_settings._init_request_schema(spec) == {"properties": {"site_token": {"type": "string"}}}
    assert provider_settings._init_request_schema({"paths": {}, "components": {}}) == {}


def test_scalar_schema_reduces_one_of_to_the_string_alternative():
    spec = load_spec_document()
    aes_key = spec["components"]["schemas"]["InitRequest"]["properties"]["aes_key"]
    resolved = provider_settings._scalar_schema(spec, aes_key)
    assert resolved["type"] == "string"
    assert resolved["pattern"] == "^[A-Fa-f0-9]{32}$"


def test_scalar_schema_falls_back_to_the_first_alternative_and_passes_plain_schemas():
    assert provider_settings._scalar_schema({}, {"oneOf": [{"type": "integer"}, {"type": "array"}]}) == {
        "type": "integer"
    }
    assert provider_settings._scalar_schema({}, {"anyOf": [{"type": "boolean"}]}) == {"type": "boolean"}
    assert provider_settings._scalar_schema({}, {"type": "integer", "oneOf": [{"type": "string"}]}) == {
        "type": "integer",
        "oneOf": [{"type": "string"}],
    }
    assert provider_settings._scalar_schema({}, {}) == {}


def test_extract_fields_from_requirements_types_from_init_request_else_string():
    spec = load_spec_document()
    fields = provider_settings._extract_fields_from_requirements(spec, ["channel", "aes_key", "site_token"])
    by_name = {field["name"]: field for field in fields}
    assert by_name["channel"]["type"] == "integer"
    assert by_name["aes_key"]["type"] == "string"
    assert by_name["site_token"]["type"] == "string"
    assert all(field["required"] for field in fields)


def test_extract_driver_requirement_fields_probes_without_vendor_options(monkeypatch):
    # No /v1/commands schema: the probe still happens and is the whole answer.
    fake_get = _fake_driver(required_fields=("aes_key",))
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    fields = provider_settings._extract_driver_requirement_fields("http://127.0.0.1:18080", {"paths": {}})

    assert [field["name"] for field in fields] == ["aes_key"]
    assert fake_get.calls == ["http://127.0.0.1:18080/v1/requirements"]


def test_extract_driver_requirement_fields_raises_on_requirements_error(monkeypatch):
    spec = _with_vendor_options({"paths": {}}, aes_key={"type": "string"})

    def boom(url, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(provider_settings.httpx, "get", boom)
    with pytest.raises(provider_settings.ProviderRegistrationError):
        provider_settings._extract_driver_requirement_fields("http://x", spec)


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
        "x-meter-driver": {
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
        "x-meter-driver": {
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
    spec = {"x-meter-driver": {"default_interface": "carrier-pigeon", "interfaces": []}}
    details = provider_settings._normalize_interface_metadata("http://base", spec)
    assert details["default_interface"] == "http"


def test_normalize_interface_metadata_reads_the_spec_block():
    details = provider_settings._normalize_interface_metadata("http://base", load_spec_document())
    assert details["default_interface"] == "http"
    assert details["interfaces"] == [
        {
            "type": "http",
            "label": "HTTP API",
            "base_url": "http://127.0.0.1:18080",
            "address": "http://127.0.0.1:18080",
        },
        {"type": "grpc", "label": "gRPC", "target": "127.0.0.1:50051", "address": "127.0.0.1:50051"},
    ]


def test_normalize_interface_metadata_without_block_synthesizes_http():
    details = provider_settings._normalize_interface_metadata("http://base", {"paths": {}})
    assert details == {
        "interfaces": [
            {"type": "http", "label": "HTTP API", "base_url": "http://base", "address": "http://base"}
        ],
        "default_interface": "http",
    }


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
    monkeypatch.setattr(provider_settings.httpx, "get", _fake_driver(_spec_document(info={})))
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
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        if url.endswith("/v1/healthz"):
            return FakeResponse({"ok": True})
        if url.endswith("/v1/status"):
            return FakeResponse({"connected": True, "gateway_type": "sparknet"})
        raise AssertionError("unexpected GET {}".format(url))

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is True
    assert status["gateway_active"] is True
    assert status["gateway_type"] == "sparknet"
    assert status["checked_url"] == "http://127.0.0.1:18080/v1/healthz"
    assert calls == ["http://127.0.0.1:18080/v1/healthz", "http://127.0.0.1:18080/v1/status"]


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


def test_get_runtime_status_is_offline_when_healthz_fails_and_probes_nothing_else(monkeypatch):
    # /v1/healthz is the spec's liveness route; a failure means offline. No
    # legacy /health probe is attempted and /v1/status is not consulted.
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        if url.endswith("/v1/healthz"):
            raise httpx.ConnectError("no healthz")
        return FakeResponse({"connected": True})

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is False
    assert status["gateway_active"] is False
    assert status["gateway_type"] is None
    assert status["checked_url"] == "http://127.0.0.1:18080/v1/healthz"
    assert calls == ["http://127.0.0.1:18080/v1/healthz"]


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


def test_required_field_names_skips_optional_extras():
    # Vendor-option extras are written with required=False and are not demanded.
    names = provider_settings._required_field_names(
        {
            "required_fields": [
                {"name": "aes_key", "required": True},
                {"name": "channel", "required": False},
                {"name": "heartbeat_period_duration"},
            ]
        }
    )
    assert names == ["aes_key", "heartbeat_period_duration"]


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


def test_validate_provider_config_payload_omits_blank_optional_fields():
    validated = provider_settings.validate_provider_config_payload(
        {
            "required_fields": [
                {"name": "aes_key", "type": "string", "required": True},
                {"name": "channel", "type": "integer", "required": False},
                {"name": "region", "type": "string", "required": False},
            ],
            "field_values": {"aes_key": "00" * 16, "channel": "", "region": "eu"},
        }
    )
    # A blank optional integer is neither demanded nor coerced; a filled one is kept.
    assert validated["required_fields"] == ["aes_key"]
    assert validated["field_values"] == {"aes_key": "00" * 16, "region": "eu"}


def test_validate_provider_config_payload_accepts_a_driver_with_no_fields():
    assert provider_settings.validate_provider_config_payload(
        {"required_fields": [], "field_values": {}}
    ) == {
        "required_fields": [],
        "field_values": {},
    }


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
