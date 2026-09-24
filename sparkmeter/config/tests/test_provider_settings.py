# -*- coding: utf-8 -*-
"""Meter driver settings tests.

The spec-document fixture (`spec_document`, the spec's own
openapi/meter-driver.yaml as JSON) and the `fake_driver` httpx.get double
come from sparkmeter/conftest.py, which also documents how to regenerate
the fixture after a meter-driver-spec wheel bump.
"""

import importlib.metadata
import json
import logging

import httpx
import pytest

from sparkmeter.config import provider_settings
from sparkmeter.metering.provider_config import configured_provider_url

# The reference driver's /v1/requirements list (spec section 5.2 example).
_REFERENCE_REQUIRED_FIELDS = ("aes_key", "channel", "heartbeat_period_duration")

# The spec's Required operations (docs/spec/index.md section 4), written out
# rather than derived from the module under test.
_SPEC_REQUIRED_OPERATIONS = (
    ("get", "/v1/requirements"),
    ("post", "/v1/init"),
    ("post", "/v1/nodes/register"),
    ("delete", "/v1/nodes/{node_id}"),
    ("post", "/v1/nodes/{node_id}/configure-meter"),
    ("post", "/v1/meters/configure"),
    ("get", "/v1/events"),
    ("get", "/v1/status"),
    ("get", "/v1/healthz"),
)


def _paths(operations):
    """An OpenAPI `paths` object with an empty operation for each (method, path)."""
    paths = {}
    for method, path in operations:
        paths.setdefault(path, {})[method] = {}
    return paths


def _spec_document(**overrides):
    """A minimal document with the spec's required operations and an http x-meter-driver block."""
    document = {
        "openapi": "3.1.0",
        "info": {"title": "Spec Driver", "version": "1.2.3"},
        "paths": _paths(_SPEC_REQUIRED_OPERATIONS),
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
        "{} for {}".format(status_code, url),
        request=request,
        response=httpx.Response(status_code, request=request),
    )


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


def _use_temp_config_root(monkeypatch, tmp_path):
    """Redirect the module's config directory globals at a temp location."""
    monkeypatch.setattr(provider_settings, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(provider_settings, "_METER_DRIVER_CONFIG_DIR", tmp_path / "meter_driver_configs")


# ---------------------------------------------------------------------------
# validate_contract against the spec's own document
# ---------------------------------------------------------------------------


def test_spec_document_fixture_is_the_pinned_spec(spec_document):
    # The fixture is regenerated from the spec tag the wheel is built from;
    # a wheel bump without regeneration fails here.
    assert spec_document["info"]["version"] == importlib.metadata.version("meter-driver-spec")
    assert spec_document["x-meter-driver"]["default_interface"] == "http"
    for method, path in _SPEC_REQUIRED_OPERATIONS:
        assert method in spec_document["paths"][path]
    # The spec's routes, and nothing the reference driver adds.
    assert "/v1/commands" not in spec_document["paths"]


def test_validate_contract_accepts_a_spec_only_driver(monkeypatch, spec_document, fake_driver):
    # A driver serving exactly the spec document, with the reference
    # /v1/requirements list. This is the meter-driver-emulator case.
    fake_get = fake_driver(spec_document, required_fields=_REFERENCE_REQUIRED_FIELDS)
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


def test_validate_contract_accepts_the_spec_document_from_its_openapi_url(
    monkeypatch, spec_document, fake_driver
):
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(spec_document))

    details = provider_settings.validate_contract("http://127.0.0.1:18080/openapi.json")

    assert details["base_url"] == "http://127.0.0.1:18080"
    assert details["openapi_url"] == "http://127.0.0.1:18080/openapi.json"


def test_validate_contract_accepts_exactly_the_spec_required_operations(monkeypatch, fake_driver):
    # A document whose paths are the nine Required routes with their
    # methods and nothing else (no Recommended routes) registers.
    document = {
        "openapi": "3.1.0",
        "info": {"title": "Minimal Driver", "version": "0.1.0"},
        "paths": {
            "/v1/requirements": {"get": {}},
            "/v1/init": {"post": {}},
            "/v1/nodes/register": {"post": {}},
            "/v1/nodes/{node_id}": {"delete": {}},
            "/v1/nodes/{node_id}/configure-meter": {"post": {}},
            "/v1/meters/configure": {"post": {}},
            "/v1/events": {"get": {}},
            "/v1/status": {"get": {}},
            "/v1/healthz": {"get": {}},
        },
    }
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert details["name"] == "Minimal Driver"


def test_validate_contract_does_not_demand_recommended_routes(monkeypatch, spec_document, fake_driver):
    del spec_document["paths"]["/v1/nodes/{node_id}/balance-and-flags"]
    del spec_document["paths"]["/v1/shutdown"]
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(spec_document))

    assert provider_settings.validate_contract("http://127.0.0.1:18080")["name"] == "Meter Driver API"


# ---------------------------------------------------------------------------
# validate_contract: interfaces
# ---------------------------------------------------------------------------


def test_validate_contract_discovers_grpc_interface(monkeypatch, fake_driver):
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
    fake_get = fake_driver(document)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert fake_get.calls[0] == "http://127.0.0.1:18080/openapi.json"
    assert details["name"] == "Spec Driver"
    assert details["default_interface"] == "grpc"
    by_type = {interface["type"]: interface for interface in details["interfaces"]}
    assert set(by_type) == {"http", "grpc"}
    assert by_type["grpc"]["target"] == "h:50051"
    assert by_type["grpc"]["address"] == "h:50051"


def test_validate_contract_synthesizes_http_when_discovery_block_is_absent(monkeypatch, fake_driver):
    document = _spec_document()
    del document["x-meter-driver"]
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

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


def test_validate_contract_ignores_non_spec_discovery_blocks(monkeypatch, fake_driver):
    # A block under any other name is not the spec's; it is not read.
    document = _spec_document()
    del document["x-meter-driver"]
    document["x-vendor-extension"] = {
        "default_interface": "grpc",
        "interfaces": [{"type": "grpc", "target": "h:50051"}],
    }
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert [interface["type"] for interface in details["interfaces"]] == ["http"]
    assert details["default_interface"] == "http"


def test_validate_contract_rejects_a_non_object_discovery_block(monkeypatch, fake_driver):
    document = _spec_document(**{"x-meter-driver": ["http"]})
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    with pytest.raises(provider_settings.ProviderRegistrationError, match="x-meter-driver must be an object"):
        provider_settings.validate_contract("http://127.0.0.1:18080")


# ---------------------------------------------------------------------------
# validate_contract: required routes
# ---------------------------------------------------------------------------


def test_required_contract_operations_are_the_spec_required_routes():
    assert provider_settings.REQUIRED_CONTRACT_OPERATIONS == _SPEC_REQUIRED_OPERATIONS


def test_validate_contract_rejects_missing_routes_naming_them(monkeypatch, fake_driver):
    document = _spec_document()
    del document["paths"]["/v1/requirements"]
    del document["paths"]["/v1/init"]
    del document["paths"]["/v1/healthz"]
    fake_get = fake_driver(document)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert "missing required routes" in str(exc.value)
    assert "GET /v1/requirements, POST /v1/init, GET /v1/healthz" in str(exc.value)
    # Rejected on the document alone; requirements are never probed.
    assert fake_get.calls == ["http://127.0.0.1:18080/openapi.json"]


def test_validate_contract_checks_the_method_not_just_the_path(monkeypatch, fake_driver):
    document = _spec_document()
    document["paths"]["/v1/init"] = {"get": {}}  # the spec's init is a POST
    document["paths"]["/v1/nodes/{node_id}"] = {"post": {}}  # the spec's unregister is a DELETE
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert "POST /v1/init" in str(exc.value)
    assert "DELETE /v1/nodes/{node_id}" in str(exc.value)
    assert "/v1/healthz" not in str(exc.value)


def test_validate_contract_matches_path_templates_by_position_not_parameter_name(monkeypatch, fake_driver):
    document = _spec_document()
    document["paths"]["/v1/nodes/{id}"] = document["paths"].pop("/v1/nodes/{node_id}")
    document["paths"]["/v1/nodes/{meter}/configure-meter"] = document["paths"].pop(
        "/v1/nodes/{node_id}/configure-meter"
    )
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    assert provider_settings.validate_contract("http://127.0.0.1:18080")["name"] == "Spec Driver"


def test_validate_contract_rejects_trailing_slashes(monkeypatch, fake_driver):
    document = _spec_document()
    document["paths"]["/v1/init/"] = document["paths"].pop("/v1/init")
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    with pytest.raises(provider_settings.ProviderRegistrationError, match="POST /v1/init"):
        provider_settings.validate_contract("http://127.0.0.1:18080")


def test_validate_contract_does_not_require_vendor_routes(monkeypatch, fake_driver):
    # /v1/commands is a reference-driver extension, not a spec route.
    document = _spec_document()
    assert "/v1/commands" not in document["paths"]
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert details["name"] == "Spec Driver"


def test_validate_contract_rejects_a_document_with_only_vendor_routes(monkeypatch, fake_driver):
    document = _spec_document(paths={"/v1/commands": {"post": {}}, "/v1/events": {"get": {}}})
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert "GET /v1/requirements" in str(exc.value)
    assert "POST /v1/init" in str(exc.value)


# ---------------------------------------------------------------------------
# validate_contract: malformed documents never raise anything but
# ProviderRegistrationError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "document, message",
    [
        (["not", "an", "object"], "must be a JSON object"),
        (_spec_document(paths=["/v1/init"]), "missing paths"),
        (_spec_document(info="Spec Driver"), "info.title"),
        (_spec_document(info={"version": "1"}), "info.title"),
    ],
)
def test_validate_contract_rejects_malformed_documents(monkeypatch, fake_driver, document, message):
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    with pytest.raises(provider_settings.ProviderRegistrationError, match=message):
        provider_settings.validate_contract("http://127.0.0.1:18080")


def test_validate_contract_tolerates_non_dict_path_items_and_operations(monkeypatch, fake_driver):
    document = _spec_document()
    document["paths"]["/v1/shutdown"] = "not-a-dict"
    document["paths"]["/v1/status"] = {"get": "not-a-dict"}
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert str(exc.value).endswith("missing required routes: GET /v1/status")


def test_validate_contract_tolerates_refs_to_non_dicts(monkeypatch, spec_document, fake_driver):
    spec_document["components"]["schemas"]["InitRequest"]["properties"]["aes_key"] = {"$ref": "#/tags"}
    spec_document["components"]["schemas"]["InitRequest"]["properties"]["channel"] = {
        "oneOf": ["integer", 7, {"type": "integer"}]
    }
    monkeypatch.setattr(
        provider_settings.httpx, "get", fake_driver(spec_document, required_fields=("aes_key", "channel"))
    )

    fields = provider_settings.validate_contract("http://127.0.0.1:18080")["driver_requirement_field_map"]

    # A $ref to a list is an empty schema (string); non-dict alternatives are skipped.
    assert fields["aes_key"]["type"] == "string"
    assert fields["channel"]["type"] == "integer"


# ---------------------------------------------------------------------------
# validate_contract: requirements probe
# ---------------------------------------------------------------------------


def test_validate_contract_returns_requirements_in_driver_order(monkeypatch, spec_document, fake_driver):
    fake_get = fake_driver(spec_document, required_fields=("channel", "aes_key", "heartbeat_period_duration"))
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert [field["name"] for field in details["driver_requirement_fields"]] == [
        "channel",
        "aes_key",
        "heartbeat_period_duration",
    ]
    assert fake_get.calls == [
        "http://127.0.0.1:18080/openapi.json",
        "http://127.0.0.1:18080/v1/requirements",
    ]


def test_validate_contract_types_undocumented_requirements_as_string_with_a_warning(
    monkeypatch, caplog, fake_driver
):
    # The minimal document has no InitRequest schema, so every field is a
    # string, and each is reported: the spec says the names must match the
    # init request schema.
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(_spec_document(), required_fields=("aes_key", "site_token")),
    )

    with caplog.at_level(logging.WARNING):
        details = provider_settings.validate_contract("http://127.0.0.1:18080")

    fields = details["driver_requirement_field_map"]
    assert fields["aes_key"]["type"] == "string"
    assert fields["site_token"]["type"] == "string"
    assert fields["site_token"]["required"] is True
    warned = [record.getMessage() for record in caplog.records if "not described" in record.getMessage()]
    assert any("'site_token'" in message for message in warned)
    assert any("'aes_key'" in message for message in warned)


def test_validate_contract_types_requirements_from_the_init_request_schema(
    monkeypatch, caplog, spec_document, fake_driver
):
    # A driver with different init fields documents them in InitRequest
    # (spec section 5.3) and lists them on /v1/requirements.
    spec_document["components"]["schemas"]["InitRequest"]["properties"]["site_token"] = {
        "type": "string",
        "title": "Site token",
        "pattern": "^[a-z]+$",
    }
    spec_document["components"]["schemas"]["InitRequest"]["properties"]["poll_seconds"] = {
        "type": "integer",
        "minimum": 5,
        "maximum": 3600,
        "default": 60,
    }
    fake_get = fake_driver(spec_document, required_fields=("site_token", "poll_seconds"))
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    with caplog.at_level(logging.WARNING):
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
    assert not any("not described" in record.getMessage() for record in caplog.records)


def test_validate_contract_requires_the_requirements_probe_and_names_the_cause(monkeypatch, fake_driver):
    url = "http://127.0.0.1:18080/v1/requirements"
    monkeypatch.setattr(
        provider_settings.httpx, "get", fake_driver(_spec_document(), requirements_error=_http_error(url))
    )

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert "/v1/requirements" in str(exc.value)
    # The underlying transport error is part of the message the form shows.
    assert "404 for http://127.0.0.1:18080/v1/requirements" in str(exc.value)


def test_validate_contract_requires_the_requirements_probe_even_with_vendor_options(monkeypatch, fake_driver):
    # The vendor-option schema is not a substitute for /v1/requirements.
    document = _with_vendor_options(_spec_document(), aes_key={"type": "string"})
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(document, requirements_error=httpx.ConnectError("down")),
    )

    with pytest.raises(provider_settings.ProviderRegistrationError, match="down"):
        provider_settings.validate_contract("http://127.0.0.1:18080")


@pytest.mark.parametrize(
    "payload",
    [
        {"fields": ["aes_key"]},
        {"required_fields": "aes_key"},
        {"required_fields": ["aes_key", 7]},
        {"required_fields": [None]},
        {"required_fields": ["aes_key", " "]},
        ["aes_key"],
    ],
)
def test_validate_contract_rejects_malformed_requirements(monkeypatch, fake_json_response, payload):
    def fake_get(url, timeout):
        if url.endswith("/v1/requirements"):
            return fake_json_response(payload)
        return fake_json_response(_spec_document())

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")

    assert "requirements response" in str(exc.value)


def test_validate_contract_accepts_a_driver_requiring_no_init_fields(monkeypatch, fake_driver):
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document(), required_fields=()))

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert details["driver_requirement_fields"] == []
    assert details["driver_requirement_field_map"] == {}


# ---------------------------------------------------------------------------
# validate_contract: InitRequest schema composition
# ---------------------------------------------------------------------------


def test_validate_contract_reads_init_request_composed_with_all_of(monkeypatch, spec_document, fake_driver):
    schemas = spec_document["components"]["schemas"]
    schemas["BaseInit"] = {
        "type": "object",
        "required": ["site_token"],
        "properties": {"site_token": {"type": "string", "pattern": "^[a-z]+$"}},
    }
    schemas["InitRequest"] = {
        "allOf": [
            {"$ref": "#/components/schemas/BaseInit"},
            {"type": "object", "properties": {"poll_seconds": {"type": "integer", "minimum": 5}}},
        ]
    }
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(spec_document, required_fields=("site_token", "poll_seconds")),
    )

    fields = provider_settings.validate_contract("http://127.0.0.1:18080")["driver_requirement_field_map"]

    assert fields["site_token"]["pattern"] == "^[a-z]+$"
    assert fields["poll_seconds"]["type"] == "integer"
    assert fields["poll_seconds"]["minimum"] == 5


def test_validate_contract_follows_ref_chains(monkeypatch, spec_document, fake_driver):
    schemas = spec_document["components"]["schemas"]
    schemas["InitAlias"] = {"$ref": "#/components/schemas/InitRequest"}
    schemas["InitAliasAlias"] = {"$ref": "#/components/schemas/InitAlias"}
    spec_document["paths"]["/v1/init"]["post"]["requestBody"]["content"]["application/json"]["schema"] = {
        "$ref": "#/components/schemas/InitAliasAlias"
    }
    schemas["HexAlias"] = {"$ref": "#/components/schemas/AesKeyInput"}
    schemas["InitRequest"]["properties"]["aes_key"] = {"$ref": "#/components/schemas/HexAlias"}
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(spec_document, required_fields=("heartbeat_period_duration", "aes_key")),
    )

    fields = provider_settings.validate_contract("http://127.0.0.1:18080")["driver_requirement_field_map"]

    assert fields["heartbeat_period_duration"]["type"] == "integer"
    assert fields["aes_key"]["pattern"] == "^[A-Fa-f0-9]{32}$"


def test_validate_contract_stops_at_ref_cycles(monkeypatch, spec_document, fake_driver):
    schemas = spec_document["components"]["schemas"]
    schemas["Loop"] = {"$ref": "#/components/schemas/Loop"}
    schemas["InitRequest"]["properties"]["aes_key"] = {"$ref": "#/components/schemas/Loop"}
    schemas["InitRequest"]["allOf"] = [{"$ref": "#/components/schemas/InitRequest"}]
    monkeypatch.setattr(
        provider_settings.httpx, "get", fake_driver(spec_document, required_fields=("aes_key",))
    )

    fields = provider_settings.validate_contract("http://127.0.0.1:18080")["driver_requirement_field_map"]

    assert fields["aes_key"]["type"] == "string"


def test_validate_contract_reads_openapi_31_type_arrays(monkeypatch, spec_document, fake_driver):
    schemas = spec_document["components"]["schemas"]
    schemas["InitRequest"]["properties"]["channel"] = {"type": ["null", "integer"], "minimum": 11}
    schemas["InitRequest"]["properties"]["region"] = {"type": ["string", "null"]}
    schemas["InitRequest"]["properties"]["aes_key"] = {
        "oneOf": [{"type": ["array"]}, {"type": ["string", "null"], "pattern": "^[a-f]+$"}]
    }
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(spec_document, required_fields=("channel", "region", "aes_key")),
    )

    fields = provider_settings.validate_contract("http://127.0.0.1:18080")["driver_requirement_field_map"]

    assert fields["channel"]["type"] == "integer"
    assert fields["channel"]["minimum"] == 11
    assert fields["region"]["type"] == "string"
    assert fields["aes_key"]["type"] == "string"
    assert fields["aes_key"]["pattern"] == "^[a-f]+$"


# ---------------------------------------------------------------------------
# validate_contract: optional InitRequest properties
# ---------------------------------------------------------------------------


def test_validate_contract_offers_optional_init_request_properties(monkeypatch, spec_document, fake_driver):
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(spec_document, required_fields=("heartbeat_period_duration", "aes_key")),
    )

    fields = provider_settings.validate_contract("http://127.0.0.1:18080")["driver_requirement_fields"]

    # /v1/requirements fields first, then the InitRequest properties it did
    # not list, optional and typed from the schema.
    assert [(field["name"], field["required"], field["type"]) for field in fields] == [
        ("heartbeat_period_duration", True, "integer"),
        ("aes_key", True, "string"),
        ("channel", False, "integer"),
    ]


def test_validate_contract_adds_no_optional_fields_when_all_are_required(
    monkeypatch, spec_document, fake_driver
):
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(spec_document, required_fields=("aes_key", "channel", "heartbeat_period_duration")),
    )

    fields = provider_settings.validate_contract("http://127.0.0.1:18080")["driver_requirement_fields"]

    assert [(field["name"], field["required"]) for field in fields] == [
        ("aes_key", True),
        ("channel", True),
        ("heartbeat_period_duration", True),
    ]


def test_validate_contract_without_init_request_lists_requirements_and_vendor_fields(
    monkeypatch, fake_driver
):
    document = _with_vendor_options(_spec_document(), region={"type": "string"})
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document, required_fields=("aes_key",)))

    fields = provider_settings.validate_contract("http://127.0.0.1:18080")["driver_requirement_fields"]

    assert [(field["name"], field["required"]) for field in fields] == [("aes_key", True), ("region", False)]


def _register_spec_driver_and_capture_init(
    session, monkeypatch, tmp_path, spec_document, fake_driver, channel
):
    """Register the spec driver, set its init values, run init, and return the init body sent."""
    import sparkmeter.metering.runtime_client as runtime_client

    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(spec_document, required_fields=("heartbeat_period_duration", "aes_key")),
    )
    provider_id = provider_settings.save_provider_settings("http://127.0.0.1:18080", "http")
    session.flush()
    provider = provider_settings.get_provider(provider_id)

    captured = {}

    def fake_initialize_provider_sync(provider, field_values, provider_details=None):
        captured["field_values"] = field_values

    monkeypatch.setattr(runtime_client, "initialize_provider_sync", fake_initialize_provider_sync)
    monkeypatch.setattr(provider_settings, "get_live_interface_details", lambda *a, **k: {})

    payload = provider_settings.load_provider_runtime_settings(provider)
    payload["field_values"] = {
        "heartbeat_period_duration": "60",
        "aes_key": "00112233445566778899aabbccddeeff",
        "channel": channel,
    }
    provider_settings.init_provider_from_payload(provider, payload)
    return captured["field_values"]


def test_registered_spec_driver_init_sends_optional_channel(
    session, monkeypatch, tmp_path, spec_document, fake_driver, caplog
):
    with caplog.at_level(logging.WARNING, logger=provider_settings.logger.name):
        field_values = _register_spec_driver_and_capture_init(
            session, monkeypatch, tmp_path, spec_document, fake_driver, channel="15"
        )

    assert field_values == {
        "heartbeat_period_duration": 60,
        "aes_key": "00112233445566778899aabbccddeeff",
        "channel": 15,
    }
    assert "not sent" not in caplog.text


def test_registered_spec_driver_init_omits_blank_optional_channel(
    session, monkeypatch, tmp_path, spec_document, fake_driver
):
    field_values = _register_spec_driver_and_capture_init(
        session, monkeypatch, tmp_path, spec_document, fake_driver, channel=""
    )

    assert field_values == {
        "heartbeat_period_duration": 60,
        "aes_key": "00112233445566778899aabbccddeeff",
    }


# ---------------------------------------------------------------------------
# validate_contract: optional /v1/commands vendor options
# ---------------------------------------------------------------------------


def test_validate_contract_appends_vendor_options_as_optional_extras(monkeypatch, spec_document, fake_driver):
    document = _with_vendor_options(
        spec_document,
        aes_key={"type": "string", "title": "AES key", "pattern": "[0-9a-fA-F]{32}"},
        channel={"type": "integer", "title": "Channel", "minimum": 11, "maximum": 26},
        region={"type": "string", "title": "Region", "description": "Radio regulatory region."},
        tx_power={"type": "integer", "title": "TX power", "minimum": 1, "maximum": 20},
    )
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(document, required_fields=("heartbeat_period_duration", "aes_key")),
    )

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    # Required fields first, in /v1/requirements order; the other InitRequest
    # properties next; vendor extras after, optional, and never duplicating
    # a name already listed.
    assert [(field["name"], field["required"]) for field in details["driver_requirement_fields"]] == [
        ("heartbeat_period_duration", True),
        ("aes_key", True),
        ("channel", False),
        ("region", False),
        ("tx_power", False),
    ]
    fields = details["driver_requirement_field_map"]
    # aes_key and channel keep the spec's InitRequest typing, not the vendor schema's.
    assert fields["aes_key"]["pattern"] == "^[A-Fa-f0-9]{32}$"
    assert fields["channel"]["type"] == "integer"
    assert fields["channel"]["minimum"] is None
    assert fields["channel"]["maximum"] is None
    assert fields["region"]["description"] == "Radio regulatory region."
    # A vendor-only field keeps the vendor schema's typing.
    assert fields["tx_power"]["type"] == "integer"
    assert fields["tx_power"]["minimum"] == 1
    assert fields["tx_power"]["maximum"] == 20
    # The raw vendor-option view is still exposed for the form layer.
    assert [field["name"] for field in details["vendor_option_fields"]] == [
        "aes_key",
        "channel",
        "region",
        "tx_power",
    ]
    assert set(details["vendor_option_field_map"]) == {"aes_key", "channel", "region", "tx_power"}


def test_validate_contract_skips_vendor_extras_the_init_request_schema_types(
    monkeypatch, spec_document, fake_driver
):
    document = _with_vendor_options(
        spec_document, channel={"type": "integer", "title": "Channel", "minimum": 11, "maximum": 26}
    )
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    fields = provider_settings.validate_contract("http://127.0.0.1:18080")["driver_requirement_fields"]

    channel_fields = [field for field in fields if field["name"] == "channel"]
    assert len(channel_fields) == 1
    assert channel_fields[0]["required"] is False
    assert channel_fields[0]["type"] == "integer"
    assert channel_fields[0]["minimum"] is None
    assert channel_fields[0]["maximum"] is None


def test_validate_contract_appends_nothing_without_vendor_options(monkeypatch, fake_driver):
    monkeypatch.setattr(
        provider_settings.httpx, "get", fake_driver(_spec_document(), required_fields=("aes_key",))
    )

    details = provider_settings.validate_contract("http://127.0.0.1:18080")

    assert [field["name"] for field in details["driver_requirement_fields"]] == ["aes_key"]
    assert details["vendor_option_fields"] == []
    assert details["vendor_option_field_map"] == {}


def test_configured_provider_url_uses_saved_setting(session, monkeypatch, fake_driver):
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document()))
    provider_settings.save_provider_settings("http://127.0.0.1:18080", "http")
    session.commit()

    assert configured_provider_url(default="") == "http://127.0.0.1:18080"


def test_configured_provider_url_ignores_env_override(session, monkeypatch, fake_driver):
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document()))
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


# ---------------------------------------------------------------------------
# JSON-pointer / schema resolution helpers
# ---------------------------------------------------------------------------


def test_resolve_local_ref_rejects_non_local_refs():
    assert provider_settings._resolve_local_ref({}, "") is None
    assert provider_settings._resolve_local_ref({}, "https://x/y") is None
    assert provider_settings._resolve_local_ref({}, 7) is None


def test_resolve_local_ref_walks_and_unescapes_tokens():
    spec = {"components": {"sch~emas": {"a/b": {"leaf": 1}}}}
    # ~0 -> "~" and ~1 -> "/" per RFC 6901.
    assert provider_settings._resolve_local_ref(spec, "#/components/sch~0emas/a~1b") == {"leaf": 1}


def test_resolve_local_ref_returns_none_for_missing_or_non_dict_nodes():
    assert provider_settings._resolve_local_ref({"a": {}}, "#/a/missing") is None
    assert provider_settings._resolve_local_ref({"a": [1, 2]}, "#/a/0") is None


def test_resolve_schema_handles_non_dict_ref_and_plain():
    assert provider_settings._resolve_schema({}, "not-a-dict") == {}
    spec = {"components": {"schemas": {"Foo": {"type": "object"}}}}
    assert provider_settings._resolve_schema(spec, {"$ref": "#/components/schemas/Foo"}) == {"type": "object"}
    assert provider_settings._resolve_schema({}, {"$ref": "#/nope"}) == {}
    assert provider_settings._resolve_schema({}, {"type": "string"}) == {"type": "string"}
    # A $ref to something that is not a schema object is an empty schema.
    assert provider_settings._resolve_schema({"x": [1]}, {"$ref": "#/x"}) == {}
    assert provider_settings._resolve_schema({}, {"$ref": 7}) == {}


def test_resolve_schema_follows_chains_and_stops_at_cycles():
    spec = {
        "a": {"$ref": "#/b"},
        "b": {"$ref": "#/c"},
        "c": {"type": "integer"},
        "loop1": {"$ref": "#/loop2"},
        "loop2": {"$ref": "#/loop1"},
    }
    assert provider_settings._resolve_schema(spec, {"$ref": "#/a"}) == {"type": "integer"}
    assert provider_settings._resolve_schema(spec, {"$ref": "#/loop1"}) == {}


def test_schema_type_reads_strings_and_type_arrays():
    assert provider_settings._schema_type({"type": "Integer"}) == "integer"
    assert provider_settings._schema_type({"type": ["null", "string"]}) == "string"
    assert provider_settings._schema_type({"type": ["null"]}) == ""
    assert provider_settings._schema_type({}) == ""
    assert provider_settings._schema_type(None) == ""


def test_object_schema_merges_all_of_parts():
    spec = {"components": {"schemas": {"Base": {"required": ["a"], "properties": {"a": {"type": "string"}}}}}}
    merged = provider_settings._object_schema(
        spec,
        {
            "allOf": [
                {"$ref": "#/components/schemas/Base"},
                {"required": ["b"], "properties": {"b": {"type": "integer"}}},
                "not-a-schema",
            ],
            "description": "kept",
        },
    )
    assert merged["properties"] == {"a": {"type": "string"}, "b": {"type": "integer"}}
    assert merged["required"] == ["a", "b"]
    assert merged["description"] == "kept"
    assert "allOf" not in merged


def test_command_type_values_reads_const_and_enum():
    assert provider_settings._command_type_values({}, {"properties": {"command_type": {"const": "Foo"}}}) == {
        "foo"
    }
    values = provider_settings._command_type_values(
        {}, {"properties": {"command_type": {"enum": ["A", " b ", ""]}}}
    )
    assert values == {"a", "b"}
    assert provider_settings._command_type_values({}, {"properties": "nope"}) == set()


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
    assert provider_settings._find_configure_provider_schema({"paths": "nope", "components": []}) == {}


# ---------------------------------------------------------------------------
# Requirement discovery helpers
# ---------------------------------------------------------------------------


def test_fetch_requirements_payload_rejects_non_object(monkeypatch, fake_json_response):
    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: fake_json_response(["nope"]))
    with pytest.raises(provider_settings.ProviderRegistrationError):
        provider_settings._fetch_requirements_payload("http://127.0.0.1:18080")


def test_fetch_requirements_payload_wraps_transport_and_json_errors(monkeypatch, fake_json_response):
    def boom(url, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(provider_settings.httpx, "get", boom)
    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings._fetch_requirements_payload("http://127.0.0.1:18080")
    assert "/v1/requirements: down" in str(exc.value)

    class BadJSON(fake_json_response):
        def json(self):
            raise ValueError("bad")

    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: BadJSON({}))
    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings._fetch_requirements_payload("http://127.0.0.1:18080")
    assert "not valid JSON" in str(exc.value)


def test_fetch_requirements_payload_returns_the_names(monkeypatch, fake_json_response):
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        lambda url, timeout: fake_json_response({"required_fields": ["b", "a", "b"]}),
    )
    assert provider_settings._fetch_requirements_payload("http://127.0.0.1:18080") == ["b", "a"]


def test_required_field_names_from_requirements_validates_the_spec_model():
    names = provider_settings._required_field_names_from_requirements({"required_fields": ["b", "a", "b"]})
    assert names == ["b", "a"]
    # RequirementsResponse.required_fields is array[string]: nothing is stringified.
    for payload in ({"required_fields": "aes_key"}, {"required_fields": [7]}, {}, {"required_fields": [""]}):
        with pytest.raises(provider_settings.ProviderRegistrationError):
            provider_settings._required_field_names_from_requirements(payload)


def test_required_field_names_error_names_each_invalid_location():
    # The message joins pydantic's error locations and messages so the form
    # can show which part of the /v1/requirements payload was wrong.
    with pytest.raises(provider_settings.ProviderRegistrationError) as excinfo:
        provider_settings._required_field_names_from_requirements({"required_fields": ["a", 7]})
    message = str(excinfo.value)
    assert "required_fields.1" in message
    assert "string" in message


def test_init_request_schema_reads_the_init_request_body(spec_document):
    schema = provider_settings._init_request_schema(spec_document)
    assert set(schema["properties"]) == {"heartbeat_period_duration", "channel", "aes_key"}
    assert schema["required"] == ["heartbeat_period_duration", "aes_key"]


def test_init_request_schema_falls_back_to_components_init_request():
    spec = {
        "paths": {"/v1/init": {"post": {}}},
        "components": {"schemas": {"InitRequest": {"properties": {"site_token": {"type": "string"}}}}},
    }
    assert provider_settings._init_request_schema(spec) == {"properties": {"site_token": {"type": "string"}}}
    assert provider_settings._init_request_schema({"paths": {}, "components": {}}) == {}
    assert provider_settings._init_request_schema({"paths": [], "components": "x"}) == {}


def test_scalar_schema_reduces_one_of_to_the_string_alternative(spec_document):
    aes_key = spec_document["components"]["schemas"]["InitRequest"]["properties"]["aes_key"]
    resolved = provider_settings._scalar_schema(spec_document, aes_key)
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
    assert provider_settings._scalar_schema({}, {"oneOf": "nope"}) == {"oneOf": "nope"}
    assert provider_settings._scalar_schema({}, {"oneOf": ["nope", 3]}) == {}


def test_extract_fields_from_requirements_types_from_init_request_else_string(spec_document):
    fields = provider_settings._extract_fields_from_requirements(
        spec_document, ["channel", "aes_key", "site_token"]
    )
    by_name = {field["name"]: field for field in fields}
    assert by_name["channel"]["type"] == "integer"
    assert by_name["aes_key"]["type"] == "string"
    assert by_name["site_token"]["type"] == "string"
    assert all(field["required"] for field in fields)


def test_extract_driver_requirement_fields_probes_without_vendor_options(monkeypatch, fake_driver):
    # No /v1/commands schema: the probe still happens and is the whole answer.
    fake_get = fake_driver({}, required_fields=("aes_key",))
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


def test_normalize_interface_metadata_tolerates_malformed_blocks():
    for spec in ({"x-meter-driver": "http"}, {"x-meter-driver": {"interfaces": "grpc"}}):
        details = provider_settings._normalize_interface_metadata("http://base", spec)
        assert [interface["type"] for interface in details["interfaces"]] == ["http"]


def test_normalize_interface_metadata_reads_the_spec_block(spec_document):
    details = provider_settings._normalize_interface_metadata("http://base", spec_document)
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


def test_validate_contract_rejects_invalid_json(monkeypatch, fake_json_response):
    class BadJSON(fake_json_response):
        def json(self):
            raise ValueError("bad")

    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: BadJSON({}))
    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.validate_contract("http://127.0.0.1:18080")
    assert "invalid JSON" in str(exc.value)


def test_validate_contract_requires_info_title(monkeypatch, fake_driver):
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document(info={})))
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


def test_get_live_interface_details_applies_selection_on_success(monkeypatch, fake_driver):
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document()))
    details = provider_settings.get_live_interface_details("http://127.0.0.1:18080")
    assert details["selected_interface"] == "http"


def test_get_live_interface_details_does_not_probe_requirements(monkeypatch, spec_document, fake_driver):
    # Interface discovery is one round trip; a slow or failing
    # /v1/requirements cannot lose the advertised gRPC target.
    fake_get = fake_driver(spec_document, requirements_error=httpx.ConnectError("slow"))
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.get_live_interface_details(
        "http://127.0.0.1:18080", selected_interface="grpc"
    )

    assert "error" not in details
    assert details["selected_interface"] == "grpc"
    assert details["selected_interface_details"]["target"] == "127.0.0.1:50051"
    assert details["driver_requirement_fields"] == []
    assert fake_get.calls == ["http://127.0.0.1:18080/openapi.json"]


def test_get_live_interface_details_reads_recorded_fields_for_a_provider(monkeypatch, fake_driver):
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document()))
    recorded = [{"name": "aes_key", "type": "string", "required": True}]
    monkeypatch.setattr(
        provider_settings, "load_provider_runtime_settings", lambda provider: {"required_fields": recorded}
    )

    details = provider_settings.get_live_interface_details("http://127.0.0.1:18080", provider={"id": "abc"})

    assert details["driver_requirement_fields"] == recorded
    assert details["driver_requirement_field_map"] == {"aes_key": recorded[0]}


def test_inspect_contract_omits_requirements(monkeypatch, spec_document, fake_driver):
    fake_get = fake_driver(spec_document)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)

    details = provider_settings.inspect_contract("http://127.0.0.1:18080")

    assert details["name"] == "Meter Driver API"
    assert details["driver_requirement_fields"] == []
    assert [interface["type"] for interface in details["interfaces"]] == ["http", "grpc"]
    assert fake_get.calls == ["http://127.0.0.1:18080/openapi.json"]


def test_get_runtime_status_reports_gateway_when_connected(monkeypatch, fake_json_response):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        if url.endswith("/v1/healthz"):
            return fake_json_response({"ok": True})
        if url.endswith("/v1/status"):
            return fake_json_response({"connected": True, "gateway_type": "sparknet"})
        raise AssertionError("unexpected GET {}".format(url))

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is True
    assert status["gateway_active"] is True
    assert status["gateway_type"] == "sparknet"
    assert status["checked_url"] == "http://127.0.0.1:18080/v1/healthz"
    assert calls == ["http://127.0.0.1:18080/v1/healthz", "http://127.0.0.1:18080/v1/status"]


def test_get_runtime_status_can_skip_gateway_probe(monkeypatch, fake_json_response):
    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: fake_json_response({"ok": True}))
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080", include_gateway_status=False)
    assert status["online"] is True
    assert status["gateway_active"] is False
    assert status["gateway_checked"] is False


def test_get_runtime_status_tolerates_gateway_probe_failure(monkeypatch, fake_json_response):
    def fake_get(url, timeout):
        if url.endswith("/v1/status"):
            raise httpx.ConnectError("no status")
        return fake_json_response({"ok": True})

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is True
    assert status["gateway_active"] is False
    assert status["gateway_checked"] is True


@pytest.mark.parametrize("health", [{"ok": False}, {"ok": "true"}, {}, ["ok"], "ok", None])
def test_get_runtime_status_is_offline_unless_healthz_answers_ok_true(
    monkeypatch, fake_json_response, health
):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        if url.endswith("/v1/healthz"):
            return fake_json_response(health)
        raise AssertionError("unexpected GET {}".format(url))

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is False
    assert '{"ok": true}' in status["message"]
    assert status["gateway_active"] is False
    assert calls == ["http://127.0.0.1:18080/v1/healthz"]


def test_get_runtime_status_is_offline_when_healthz_is_not_json(monkeypatch, fake_json_response):
    class BadJSON(fake_json_response):
        def json(self):
            raise ValueError("bad")

    monkeypatch.setattr(provider_settings.httpx, "get", lambda url, timeout: BadJSON({}))
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is False
    assert "not valid JSON" in status["message"]


@pytest.mark.parametrize("gateway", [["connected"], [], "connected", None])
def test_get_runtime_status_stays_online_when_status_is_not_an_object(
    monkeypatch, fake_json_response, gateway
):
    # Liveness is /v1/healthz alone; an unusable /v1/status body means no
    # gateway, the same as a transport failure or invalid JSON there.
    def fake_get(url, timeout):
        if url.endswith("/v1/status"):
            return fake_json_response(gateway)
        return fake_json_response({"ok": True})

    monkeypatch.setattr(provider_settings.httpx, "get", fake_get)
    status = provider_settings.get_runtime_status("http://127.0.0.1:18080")
    assert status["online"] is True
    assert status["message"] == "online"
    assert status["gateway_checked"] is True
    assert status["gateway_active"] is False
    assert status["gateway_type"] is None


def test_get_runtime_status_is_offline_when_healthz_fails_and_probes_nothing_else(
    monkeypatch, fake_json_response
):
    # /v1/healthz is the spec's liveness route; a failure means offline. No
    # legacy /health probe is attempted and /v1/status is not consulted.
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        if url.endswith("/v1/healthz"):
            raise httpx.ConnectError("no healthz")
        return fake_json_response({"connected": True})

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
        provider_settings._stored_field_specs({"required_fields": "nope"})


def test_required_field_names_accepts_dicts_and_strings(caplog):
    with caplog.at_level(logging.WARNING):
        names = provider_settings._required_field_names(
            {"required_fields": [{"name": "aes_key"}, "channel", {"name": ""}, "  "]}
        )
    assert names == ["aes_key", "channel"]


def test_stored_field_specs_treats_bare_names_as_required_strings_and_says_so(caplog):
    # A config written before field types were recorded (spec entries were
    # bare names): usable as required strings, with a pointer to re-register.
    with caplog.at_level(logging.WARNING):
        specs = provider_settings._stored_field_specs(
            {"required_fields": ["channel", {"name": "aes_key", "type": "string", "required": True}]}
        )
    assert specs == {
        "channel": {"name": "channel", "type": "string", "required": True},
        "aes_key": {"name": "aes_key", "type": "string", "required": True},
    }
    assert any(
        "channel" in record.getMessage() and "Re-register the driver" in record.getMessage()
        for record in caplog.records
    )


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
    assert provider_settings._coerce_field_value("c", " 26 ", {"type": "integer"}) == 26
    assert provider_settings._coerce_field_value("r", "1.5", {"type": "number"}) == 1.5
    assert provider_settings._coerce_field_value("b", "yes", {"type": "boolean"}) is True
    assert provider_settings._coerce_field_value("b", "off", {"type": "boolean"}) is False
    assert provider_settings._coerce_field_value("b", True, {"type": "boolean"}) is True
    assert provider_settings._coerce_field_value("s", " kept ", {"type": "string"}) == "kept"
    assert provider_settings._coerce_field_value("s", 7, {"type": "string"}) == "7"
    assert provider_settings._coerce_field_value("s", "x", {"type": ["string", "null"]}) == "x"
    assert provider_settings._coerce_field_value("l", [1], {"type": "array"}) == [1]
    assert provider_settings._coerce_field_value("o", {"a": 1}, {"type": "object"}) == {"a": 1}


def test_coerce_field_value_raises_on_bad_input():
    for value, spec in (
        ("nope", {"type": "integer"}),
        ("nope", {"type": "number"}),
        ("maybe", {"type": "boolean"}),
        ("x", {"type": "array"}),
        ("x", {"type": "object"}),
        ([1], {"type": "string"}),
    ):
        with pytest.raises(provider_settings.DriverConfigError):
            provider_settings._coerce_field_value("f", value, spec)


def test_coerce_aes_key_accepts_the_two_spec_forms_only():
    hex_key = "00112233445566778899aabbccddeeff"
    assert (
        provider_settings._coerce_field_value("aes_key", " {} ".format(hex_key), {"type": "string"})
        == hex_key
    )
    assert provider_settings._coerce_field_value("aes_key", list(range(16)), {"type": "string"}) == list(
        range(16)
    )
    for bad in ("not-hex", hex_key[:-1], list(range(15)), list(range(17)), [256] + [0] * 15, [True] * 16, 7):
        with pytest.raises(provider_settings.DriverConfigError, match="aes_key"):
            provider_settings._coerce_field_value("aes_key", bad, {"type": "string"})


def test_check_field_constraints_enforces_pattern_and_bounds():
    provider_settings._check_field_constraints("s", "abc", {"pattern": "^[a-z]+$"})
    provider_settings._check_field_constraints("c", 11, {"minimum": 11, "maximum": 26})
    provider_settings._check_field_constraints("c", 26, {"minimum": 11, "maximum": 26})
    with pytest.raises(provider_settings.DriverConfigError, match="pattern"):
        provider_settings._check_field_constraints("s", "ABC", {"pattern": "^[a-z]+$"})
    with pytest.raises(provider_settings.DriverConfigError, match="at least"):
        provider_settings._check_field_constraints("c", 10, {"minimum": 11})
    with pytest.raises(provider_settings.DriverConfigError, match="at most"):
        provider_settings._check_field_constraints("c", 27, {"maximum": 26})
    # Booleans and non-numbers are not bounded; an unusable pattern is skipped.
    provider_settings._check_field_constraints("b", True, {"minimum": 5})
    provider_settings._check_field_constraints("s", "x", {"minimum": 5})
    provider_settings._check_field_constraints("s", "x", {"pattern": "(["})


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


def test_validate_provider_config_payload_treats_whitespace_as_missing():
    with pytest.raises(provider_settings.DriverConfigError, match="channel"):
        provider_settings.validate_provider_config_payload(
            {"required_fields": [{"name": "channel", "type": "integer"}], "field_values": {"channel": "   "}}
        )


def test_validate_provider_config_payload_enforces_recorded_constraints():
    payload = {
        "required_fields": [
            {"name": "channel", "type": "integer", "minimum": 11, "maximum": 26},
            {"name": "region", "type": "string", "pattern": "^[a-z]{2}$"},
        ],
        "field_values": {"channel": "27", "region": "eu"},
    }
    with pytest.raises(provider_settings.DriverConfigError, match="'channel' must be at most 26"):
        provider_settings.validate_provider_config_payload(payload)
    payload["field_values"] = {"channel": "26", "region": "EUR"}
    with pytest.raises(provider_settings.DriverConfigError, match="'region' must match"):
        provider_settings.validate_provider_config_payload(payload)
    payload["field_values"] = {"channel": "26", "region": "eu"}
    assert provider_settings.validate_provider_config_payload(payload)["field_values"] == {
        "channel": 26,
        "region": "eu",
    }


def test_validate_provider_config_payload_checks_aes_key_forms():
    payload = {
        "required_fields": [{"name": "aes_key", "type": "string", "pattern": "^[A-Fa-f0-9]{32}$"}],
        "field_values": {"aes_key": "not-hex"},
    }
    with pytest.raises(provider_settings.DriverConfigError, match="32 hex characters"):
        provider_settings.validate_provider_config_payload(payload)
    payload["field_values"] = {"aes_key": list(range(16))}
    assert provider_settings.validate_provider_config_payload(payload)["field_values"] == {
        "aes_key": list(range(16))
    }


def test_validate_provider_config_payload_drops_keys_the_driver_did_not_ask_for(caplog):
    with caplog.at_level(logging.WARNING):
        validated = provider_settings.validate_provider_config_payload(
            {
                "required_fields": [{"name": "channel", "type": "integer", "required": True}],
                "field_values": {"channel": "26", "leftover": "x", "aes_key": "00" * 16},
            }
        )
    # A hand-edited config's extra keys are not posted to the driver.
    assert validated["field_values"] == {"channel": 26}
    assert any("leftover" in record.getMessage() for record in caplog.records)


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
# gRPC selection checks
# ---------------------------------------------------------------------------


def _grpc_details(target="h:50051", required=("heartbeat_period_duration", "aes_key")):
    interfaces = [{"type": "http", "address": "http://x"}]
    if target is not None:
        interfaces.append({"type": "grpc", "target": target, "address": target})
    return {
        "interfaces": interfaces,
        "driver_requirement_fields": [{"name": name, "required": True} for name in required]
        + [{"name": "channel", "required": False}],
    }


def test_check_grpc_selection_accepts_an_advertised_target_with_the_fixed_init_fields():
    provider_settings.check_grpc_selection(_grpc_details())


def test_check_grpc_selection_rejects_a_missing_grpc_interface():
    with pytest.raises(provider_settings.ProviderRegistrationError, match="advertises no grpc interface"):
        provider_settings.check_grpc_selection(_grpc_details(target=None))


def test_check_grpc_selection_rejects_a_grpc_interface_without_target():
    with pytest.raises(provider_settings.ProviderRegistrationError, match="advertises no target"):
        provider_settings.check_grpc_selection(_grpc_details(target=""))


def test_check_grpc_selection_rejects_requirements_lacking_the_fixed_init_fields():
    with pytest.raises(provider_settings.ProviderRegistrationError) as exc:
        provider_settings.check_grpc_selection(_grpc_details(required=("aes_key",)))
    assert "does not list: heartbeat_period_duration" in str(exc.value)
    # An optional extra does not count: ConfigureDriver needs the value.
    details = _grpc_details(required=("heartbeat_period_duration",))
    details["driver_requirement_fields"].append({"name": "aes_key", "required": False})
    with pytest.raises(provider_settings.ProviderRegistrationError, match="does not list: aes_key"):
        provider_settings.check_grpc_selection(details)


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


def test_save_and_lookup_providers_roundtrip(session, monkeypatch, tmp_path, fake_driver):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document()))

    provider_id = provider_settings.save_provider_settings("http://127.0.0.1:18080", "http")
    session.flush()

    assert provider_settings.get_provider(provider_id)["base_url"] == "http://127.0.0.1:18080"
    assert provider_settings.get_provider("nonexistent") is None
    assert provider_settings.get_enabled_provider()["id"] == provider_id


def test_save_provider_settings_replaces_existing_by_id(session, monkeypatch, tmp_path, fake_driver):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document()))

    provider_id = provider_settings.save_provider_settings("http://127.0.0.1:18080", "http")
    session.flush()
    # Saving again with the same id replaces rather than appends.
    provider_settings.save_provider_settings("http://127.0.0.1:28080", "http", provider_id=provider_id)
    session.flush()

    providers = provider_settings.get_saved_providers()
    assert len(providers) == 1
    assert providers[0]["base_url"] == "http://127.0.0.1:28080"


def test_save_provider_settings_preserves_other_providers(session, monkeypatch, tmp_path, fake_driver):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document()))

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


def test_save_provider_settings_falls_back_for_unknown_non_grpc_interface(
    session, monkeypatch, tmp_path, fake_driver
):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document()))

    # "mqtt" is not advertised, so the default interface (http) is saved.
    provider_id = provider_settings.save_provider_settings("http://127.0.0.1:18080", "mqtt")
    session.flush()
    assert provider_settings.get_provider(provider_id)["selected_interface"] == "http"


def test_save_provider_settings_refuses_grpc_the_driver_does_not_advertise(
    session, monkeypatch, tmp_path, fake_driver
):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(_spec_document()))

    with pytest.raises(provider_settings.ProviderRegistrationError, match="advertises no grpc interface"):
        provider_settings.save_provider_settings("http://127.0.0.1:18080", "grpc")
    assert provider_settings.get_saved_providers() == []


def test_save_provider_settings_refuses_grpc_without_a_target(session, monkeypatch, tmp_path, fake_driver):
    _use_temp_config_root(monkeypatch, tmp_path)
    document = _spec_document(
        **{
            "x-meter-driver": {
                "default_interface": "http",
                "interfaces": [{"type": "http", "base_url": "http://127.0.0.1:18080"}, {"type": "grpc"}],
            }
        }
    )
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(document))

    with pytest.raises(provider_settings.ProviderRegistrationError, match="advertises no target"):
        provider_settings.save_provider_settings("http://127.0.0.1:18080", "grpc")


def test_save_provider_settings_refuses_grpc_when_requirements_lack_its_fields(
    session, monkeypatch, tmp_path, spec_document, fake_driver
):
    _use_temp_config_root(monkeypatch, tmp_path)
    # The spec document advertises grpc at 127.0.0.1:50051, but this driver's
    # /v1/requirements has no aes_key: ConfigureDriver could never be built.
    monkeypatch.setattr(
        provider_settings.httpx,
        "get",
        fake_driver(spec_document, required_fields=("heartbeat_period_duration", "site_token")),
    )

    with pytest.raises(provider_settings.ProviderRegistrationError, match="does not list: aes_key"):
        provider_settings.save_provider_settings("http://127.0.0.1:18080", "grpc")


def test_save_provider_settings_records_the_advertised_grpc_target(
    session, monkeypatch, tmp_path, spec_document, fake_driver
):
    _use_temp_config_root(monkeypatch, tmp_path)
    monkeypatch.setattr(provider_settings.httpx, "get", fake_driver(spec_document))

    provider_id = provider_settings.save_provider_settings("http://127.0.0.1:18080", "grpc")
    session.flush()

    provider = provider_settings.get_provider(provider_id)
    assert provider["selected_interface"] == "grpc"
    assert provider["selected_interface_target"] == "127.0.0.1:50051"
