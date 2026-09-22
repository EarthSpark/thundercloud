# -*- coding: utf-8 -*-
"""Meter driver settings and validation helpers."""

import json
import logging
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx

from sparkmeter.config.configdomain import ConfigParameter
from sparkmeter.config.configparameter import ParameterObject
from sparkmeter.database.alchemy import sql


class ProviderRegistrationError(ValueError):
    """Raised when a meter driver URL fails validation."""


class DriverConfigError(ValueError):
    """Raised when a driver JSON config file is invalid."""


class DriverInitializationError(ValueError):
    """Raised when driver initialization fails."""


_REPO_ROOT = Path(__file__).resolve().parents[2]
_METER_DRIVER_CONFIG_DIR = _REPO_ROOT / "meter_driver_configs"
logger = logging.getLogger(__name__)

# The routes the Meter Driver Specification (v1.4.0, docs/spec/index.md
# section 4) marks Required, other than /openapi.json, which is the document
# being checked. A driver's /openapi.json must list every one of these.
REQUIRED_CONTRACT_PATHS = (
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

# The spec's interface-discovery extension block on /openapi.json (section 5.1).
DISCOVERY_EXTENSION = "x-meter-driver"


def _resolve_local_ref(spec, ref):
    """Resolve a local JSON Pointer reference within an OpenAPI document."""
    if not ref or not ref.startswith("#/"):
        return None

    node = spec
    for part in ref[2:].split("/"):
        node = node.get(part.replace("~1", "/").replace("~0", "~"))
        if node is None:
            return None
    return node


def _resolve_schema(spec, schema):
    """Resolve a schema object or local ref to a plain dict."""
    if not isinstance(schema, dict):
        return {}
    if "$ref" in schema:
        return _resolve_local_ref(spec, schema["$ref"]) or {}
    return schema


# ---------------------------------------------------------------------------
# Optional extension: /v1/commands configure_provider vendor options
#
# Not part of the spec. A driver may additionally document a /v1/commands
# route whose configure_provider command carries a vendor_options object;
# its fields are offered as optional extras after the spec-discovered
# required fields. Nothing below is required for registration.
# ---------------------------------------------------------------------------


def _command_type_values(spec, schema):
    """Extract the possible command_type discriminator values from a schema."""
    resolved = _resolve_schema(spec, schema)
    properties = resolved.get("properties") or {}
    command_type = _resolve_schema(spec, properties.get("command_type") or {})
    values = []
    if "const" in command_type:
        values.append(command_type["const"])
    if "enum" in command_type and isinstance(command_type["enum"], list):
        values.extend(command_type["enum"])
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _find_configure_provider_schema(spec):
    """Locate the configure-provider command schema in the OpenAPI document."""
    request_schema = (
        (((spec.get("paths") or {}).get("/v1/commands") or {}).get("post") or {})
        .get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    request_schema = _resolve_schema(spec, request_schema)

    for candidate in request_schema.get("oneOf") or []:
        values = _command_type_values(spec, candidate)
        if "configure_provider" in values:
            return _resolve_schema(spec, candidate)

    components = (spec.get("components") or {}).get("schemas") or {}
    for schema in components.values():
        values = _command_type_values(spec, schema)
        if "configure_provider" in values:
            return _resolve_schema(spec, schema)

    return {}


def _field_spec(name, schema, required):
    """Normalize a vendor-option field description for the form layer."""
    field_type = str(schema.get("type") or "string").strip().lower() or "string"
    return {
        "name": name,
        "label": str(schema.get("title") or name.replace("_", " ").title()),
        "type": field_type,
        "required": bool(required),
        "description": str(schema.get("description") or "").strip(),
        "pattern": str(schema.get("pattern") or "").strip(),
        "minimum": schema.get("minimum"),
        "maximum": schema.get("maximum"),
        "default": schema.get("default"),
    }


def _extract_vendor_option_fields(spec):
    """Extract configure-provider vendor option requirements from OpenAPI."""
    command_schema = _find_configure_provider_schema(spec)
    properties = command_schema.get("properties") or {}
    vendor_schema = _resolve_schema(spec, properties.get("vendor_options") or {})

    fields = []
    required_fields = set(vendor_schema.get("required") or [])
    for field_name, field_schema in (vendor_schema.get("properties") or {}).items():
        resolved_field = _resolve_schema(spec, field_schema)
        fields.append(_field_spec(field_name, resolved_field, field_name in required_fields))

    return fields


def _vendor_option_field_map(spec):
    """Return vendor-option fields keyed by API field name."""
    return {field["name"]: field for field in _extract_vendor_option_fields(spec)}


# ---------------------------------------------------------------------------
# Init-field discovery: GET /v1/requirements typed by the InitRequest schema
# (spec sections 2, 5.2, 5.3 and 9)
# ---------------------------------------------------------------------------


def _requirements_url(service_url):
    """Build the requirements endpoint URL from a service URL."""
    return normalize_base_url(service_url) + "/v1/requirements"


def _fetch_requirements_payload(service_url, timeout=10.0):
    """Fetch the driver's GET /v1/requirements response (a RequirementsResponse object)."""
    try:
        response = httpx.get(_requirements_url(service_url), timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ProviderRegistrationError("could not fetch driver requirements from /v1/requirements") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ProviderRegistrationError("driver requirements response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ProviderRegistrationError("driver requirements response must be a JSON object")
    return payload


def _required_field_names_from_requirements(payload):
    """Return the `required_fields` names from a RequirementsResponse, in the driver's order."""
    names = payload.get("required_fields")
    if not isinstance(names, list):
        raise ProviderRegistrationError("driver requirements response must list required_fields")
    normalized = []
    for name in names:
        text = str(name).strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _init_request_schema(spec):
    """Return the document's InitRequest schema.

    The POST /v1/init request-body schema is authoritative; a document that
    documents init fields only under components.schemas.InitRequest is
    read from there.
    """
    schema = (
        (((spec.get("paths") or {}).get("/v1/init") or {}).get("post") or {})
        .get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    resolved = _resolve_schema(spec, schema)
    if resolved.get("properties"):
        return resolved
    components = (spec.get("components") or {}).get("schemas") or {}
    return _resolve_schema(spec, components.get("InitRequest") or {})


def _scalar_schema(spec, schema):
    """Resolve a property schema to the alternative describing its scalar wire form.

    A oneOf/anyOf without its own type (the spec's AesKeyInput: 32-hex
    string or 16-byte array) reduces to its first string-typed alternative,
    else its first alternative, so the form layer sees one type and pattern.
    """
    resolved = _resolve_schema(spec, schema)
    alternatives = resolved.get("oneOf") or resolved.get("anyOf") or []
    if resolved.get("type") or not alternatives:
        return resolved
    resolved_alternatives = [_resolve_schema(spec, alternative) for alternative in alternatives]
    for alternative in resolved_alternatives:
        if alternative.get("type") == "string":
            return alternative
    return resolved_alternatives[0]


def _extract_fields_from_requirements(spec, required_fields):
    """Build field specs for the advertised init fields, typed from InitRequest.

    A field the document does not describe is typed as a string.
    """
    properties = _init_request_schema(spec).get("properties") or {}
    return [
        _field_spec(name, _scalar_schema(spec, properties.get(name) or {}), True) for name in required_fields
    ]


def _extract_driver_requirement_fields(base_url, spec, timeout=10.0):
    """Discover the driver's init fields.

    GET /v1/requirements is required and its list order is kept; each name
    is typed from the document's InitRequest schema. Fields from the
    optional /v1/commands vendor-option extension, if the document has
    one, follow as optional extras.
    """
    payload = _fetch_requirements_payload(base_url, timeout=timeout)
    fields = _extract_fields_from_requirements(spec, _required_field_names_from_requirements(payload))
    known = {field["name"] for field in fields}
    for vendor_field in _extract_vendor_option_fields(spec):
        if vendor_field["name"] in known:
            continue
        extra = dict(vendor_field)
        extra["required"] = False
        fields.append(extra)
        known.add(extra["name"])
    return fields


def _get_parameter(name):
    """Return a config parameter by name."""
    return ConfigParameter.get_by_name(name)


def _create_parameter_if_missing(name):
    """Create a known config parameter on demand for existing databases."""
    parameter = _get_parameter(name)
    if parameter is not None:
        return parameter

    for attribute in ParameterObject.attributes:
        if attribute.name == name:
            parameter = ConfigParameter.create_with_default(attribute)
            sql.session.add(parameter)
            sql.session.flush()
            return parameter

    raise RuntimeError("unknown config parameter: {}".format(name))


def _providers_parameter():
    """Return the backing config parameter for the providers list."""
    return _create_parameter_if_missing("metering-providers")


def get_saved_providers():
    """Return configured meter drivers."""
    parameter = _providers_parameter()
    raw_value = (parameter.value or "").strip()
    if not raw_value:
        raw_value = "[]"

    try:
        providers = json.loads(raw_value)
    except ValueError:
        providers = []

    normalized = []
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        normalized.append(
            {
                "id": str(provider.get("id") or uuid.uuid4().hex),
                "name": str(provider.get("name") or "Meter driver"),
                "base_url": str(provider.get("base_url") or "").strip(),
                "openapi_url": str(provider.get("openapi_url") or "").strip(),
                "service_version": str(provider.get("service_version") or ""),
                "selected_interface": str(provider.get("selected_interface") or "http").strip().lower()
                or "http",
                "selected_interface_target": str(provider.get("selected_interface_target") or "").strip(),
                "enabled": bool(provider.get("enabled", True)),
            }
        )
    return normalized


def save_providers(providers):
    """Persist the full providers list."""
    parameter = _providers_parameter()
    parameter.value = json.dumps(providers, sort_keys=True)
    _cleanup_orphaned_driver_config_files(providers)


def get_provider(provider_id):
    """Return a configured provider by id."""
    for provider in get_saved_providers():
        if provider["id"] == provider_id:
            return provider
    return None


def get_enabled_provider():
    """Return the provider currently selected for runtime use."""
    providers = get_saved_providers()
    for provider in providers:
        if provider.get("enabled"):
            return provider
    return providers[0] if providers else None


def _default_config_path(provider_id):
    """Return the repo-relative JSON path for a driver config."""
    return "meter_driver_configs/{}.json".format(provider_id)


def _config_abspath(config_path):
    """Convert a repo-relative config path into an absolute path."""
    return _REPO_ROOT / config_path


def _cleanup_orphaned_driver_config_files(providers):
    """Delete driver JSON files whose provider ids are no longer saved."""
    expected_filenames = {
        "{}.json".format(str((provider or {}).get("id") or "").strip())
        for provider in (providers or [])
        if str((provider or {}).get("id") or "").strip()
    }

    if not _METER_DRIVER_CONFIG_DIR.exists():
        return

    for config_path in _METER_DRIVER_CONFIG_DIR.glob("*.json"):
        if config_path.name in expected_filenames:
            continue
        try:
            config_path.unlink()
        except OSError:
            # Best-effort cleanup only; persistence of the saved provider
            # list should not fail because a stale JSON file could not be removed.
            pass


def _load_existing_driver_config(config_path):
    """Load an existing driver JSON file, if present and valid."""
    if not config_path:
        return {}

    try:
        with _config_abspath(config_path).open() as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return {}

    return payload if isinstance(payload, dict) else {}


def _field_values_payload(details, existing_payload):
    """Build the editable field_values section from advertised requirements."""
    previous = (existing_payload or {}).get("field_values") or (
        (((existing_payload or {}).get("configure_provider") or {}).get("vendor_options")) or {}
    )
    field_values = {}
    for field in details.get("driver_requirement_fields") or []:
        name = field["name"]
        default = field.get("default")
        field_values[name] = previous.get(name, default if default is not None else "")
    return field_values


def _write_driver_config_file(provider_record, details):
    """Create or refresh the per-driver JSON config file."""
    config_path = _default_config_path(provider_record["id"])
    existing_payload = _load_existing_driver_config(config_path)

    payload = {
        "driver": {
            "id": provider_record["id"],
            "name": details["name"],
            "base_url": details["base_url"],
            "openapi_url": details["openapi_url"],
            "service_version": details["service_version"],
            "selected_interface": provider_record["selected_interface"],
            "selected_interface_target": provider_record.get("selected_interface_target", ""),
            "enabled": bool(provider_record.get("enabled", True)),
        },
        "field_values": _field_values_payload(details, existing_payload),
        "required_fields": details.get("driver_requirement_fields") or [],
        "init_status": (existing_payload or {}).get("init_status")
        or {
            "has_successful_init": False,
            "last_init_succeeded": False,
            "last_init_error": "",
        },
    }

    config_abspath = _config_abspath(config_path)
    config_abspath.parent.mkdir(parents=True, exist_ok=True)
    with config_abspath.open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def get_provider_config_abspath(provider):
    """Return the absolute JSON config path for a saved provider."""
    provider_id = str((provider or {}).get("id") or "").strip()
    if not provider_id:
        return ""
    return str(_config_abspath(_default_config_path(provider_id)))


def load_provider_runtime_settings(provider):
    """Load runtime vendor settings from the provider's JSON file."""
    provider_id = str((provider or {}).get("id") or "").strip()
    if not provider_id:
        return {}
    return _load_existing_driver_config(_default_config_path(provider_id))


def load_provider_config_text(provider):
    """Return the editable JSON text for a provider config file."""
    provider_id = str((provider or {}).get("id") or "").strip()
    if not provider_id:
        return "{}\n"

    config_path = _default_config_path(provider_id)
    config_abspath = _config_abspath(config_path)
    if config_abspath.exists():
        return config_abspath.read_text()

    payload = {
        "driver": {
            "id": provider["id"],
            "name": provider.get("name", ""),
            "base_url": provider.get("base_url", ""),
            "openapi_url": provider.get("openapi_url", ""),
            "service_version": provider.get("service_version", ""),
            "selected_interface": provider.get("selected_interface", "http"),
            "selected_interface_target": provider.get("selected_interface_target", ""),
            "enabled": bool(provider.get("enabled", True)),
        },
        "field_values": {},
        "required_fields": [],
        "init_status": {
            "has_successful_init": False,
            "last_init_succeeded": False,
            "last_init_error": "",
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _dump_provider_config_text(payload):
    """Serialize a provider config payload in canonical form."""
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _normalize_init_status(payload):
    """Return a normalized init-status payload."""
    status = (payload or {}).get("init_status") or {}
    if not isinstance(status, dict):
        status = {}
    return {
        "has_successful_init": bool(status.get("has_successful_init")),
        "last_init_succeeded": bool(status.get("last_init_succeeded")),
        "last_init_error": str(status.get("last_init_error") or ""),
    }


def parse_provider_config_text(config_text):
    """Parse driver JSON text into a dict."""
    try:
        payload = json.loads(config_text)
    except ValueError as exc:
        raise DriverConfigError("config JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise DriverConfigError("config JSON must be an object")
    return payload


def _required_field_names(payload):
    """Return the names a config payload must supply values for.

    Entries are the field specs written at registration (dicts) or bare
    names. A dict entry marked `"required": false` is an optional extra
    and is not demanded.
    """
    names = payload.get("required_fields") or []
    if not isinstance(names, list):
        raise DriverConfigError("required_fields must be a list")
    normalized = []
    for entry in names:
        if isinstance(entry, dict):
            if entry.get("required") is False:
                continue
            name = str(entry.get("name") or "").strip()
        else:
            name = str(entry).strip()
        if name:
            normalized.append(name)
    return normalized


def _field_values(payload):
    """Return the field_values mapping from a config payload."""
    values = payload.get("field_values") or {}
    if not isinstance(values, dict):
        raise DriverConfigError("field_values must be an object")
    return values


def _required_field_specs(payload):
    """Return required field metadata keyed by field name."""
    names = payload.get("required_fields") or []
    if not isinstance(names, list):
        raise DriverConfigError("required_fields must be a list")

    specs = {}
    for entry in names:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if name:
            specs[name] = entry
    return specs


def _coerce_field_value(name, value, spec):
    """Coerce a raw JSON field value to the type required by the driver."""
    field_type = str((spec or {}).get("type") or "string").strip().lower()
    if field_type == "integer":
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise DriverConfigError("field {!r} must be an integer".format(name)) from exc
    if field_type == "number":
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise DriverConfigError("field {!r} must be a number".format(name)) from exc
    if field_type == "boolean":
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in ("true", "1", "yes", "on"):
            return True
        if normalized in ("false", "0", "no", "off"):
            return False
        raise DriverConfigError("field {!r} must be a boolean".format(name))
    return value


def validate_provider_config_payload(payload):
    """Validate a driver config payload and return the typed init values.

    Every required field needs a value. An optional field left blank is
    omitted from the returned `field_values` rather than sent as "".
    """
    required_fields = _required_field_names(payload)
    required_field_specs = _required_field_specs(payload)
    field_values = _field_values(payload)
    missing = [
        name for name in required_fields if name not in field_values or field_values[name] in (None, "")
    ]
    if missing:
        raise DriverConfigError("required fields are missing values: {}".format(", ".join(missing)))
    coerced_field_values = {}
    for name, value in field_values.items():
        if value in (None, "") and name not in required_fields:
            continue
        coerced_field_values[name] = _coerce_field_value(name, value, required_field_specs.get(name))
    return {
        "required_fields": required_fields,
        "field_values": coerced_field_values,
    }


def save_provider_config_text(provider, config_text):
    """Persist edited JSON text for a provider."""
    payload = parse_provider_config_text(config_text)
    validated = validate_provider_config_payload(payload)
    payload["init_status"] = _normalize_init_status(payload)
    config_abspath = Path(get_provider_config_abspath(provider))
    config_abspath.parent.mkdir(parents=True, exist_ok=True)
    config_abspath.write_text(_dump_provider_config_text(payload))
    return payload, validated


def init_provider_from_payload(provider, payload, timeout=10.0):
    """Attempt driver initialization using the saved field_values payload."""
    validated = validate_provider_config_payload(payload)
    init_status = _normalize_init_status(payload)
    config_abspath = Path(get_provider_config_abspath(provider))
    provider_name = (
        str((provider or {}).get("name") or "").strip()
        or str((provider or {}).get("base_url") or "").strip()
        or "meter driver"
    )
    try:
        from sparkmeter.metering.runtime_client import initialize_provider_sync

        provider_details = get_live_interface_details(
            provider["base_url"],
            selected_interface=provider.get("selected_interface"),
            timeout=timeout,
        )
        initialize_provider_sync(
            provider,
            validated["field_values"],
            provider_details=provider_details,
        )
    except Exception as exc:
        init_status["last_init_succeeded"] = False
        detail = str(exc)
        init_status["last_init_error"] = detail
        payload["init_status"] = init_status
        config_abspath.write_text(_dump_provider_config_text(payload))
        if detail:
            raise DriverInitializationError("driver init failed: {}".format(detail)) from exc
        raise DriverInitializationError("driver init failed") from exc
    init_status["has_successful_init"] = True
    init_status["last_init_succeeded"] = True
    init_status["last_init_error"] = ""
    payload["init_status"] = init_status
    config_abspath.write_text(_dump_provider_config_text(payload))
    logger.info("meter driver init succeeded for %s; gateway initialized", provider_name)


def get_provider_init_status(provider):
    """Return persisted init status for a provider."""
    payload = load_provider_runtime_settings(provider)
    return _normalize_init_status(payload)


def initialize_configured_providers_on_startup(timeout=10.0):
    """Attempt init for every saved provider with a complete JSON config."""
    results = []
    for provider in get_saved_providers():
        payload = load_provider_runtime_settings(provider)
        if not payload:
            results.append(
                {
                    "provider": provider,
                    "attempted": False,
                    "success": False,
                    "reason": "missing config payload",
                }
            )
            continue

        try:
            validate_provider_config_payload(payload)
        except DriverConfigError as exc:
            results.append(
                {
                    "provider": provider,
                    "attempted": False,
                    "success": False,
                    "reason": str(exc),
                }
            )
            continue

        try:
            init_provider_from_payload(provider, payload, timeout=timeout)
        except DriverInitializationError as exc:
            results.append(
                {
                    "provider": provider,
                    "attempted": True,
                    "success": False,
                    "reason": str(exc),
                }
            )
            continue

        results.append(
            {
                "provider": provider,
                "attempted": True,
                "success": True,
                "reason": "",
            }
        )

    return results


def save_provider_settings(
    service_url, selected_interface, enabled=True, provider_id=None, aes_key="", channel=""
):
    """Persist a meter driver entry and return its id."""
    details = validate_contract(service_url)
    selected_interface = (selected_interface or details["default_interface"]).strip().lower()
    valid_interfaces = {interface["type"] for interface in details.get("interfaces") or []}
    if selected_interface not in valid_interfaces:
        selected_interface = details["default_interface"]

    selected_interface_details = next(
        (
            interface
            for interface in details.get("interfaces") or []
            if interface.get("type") == selected_interface
        ),
        {},
    )

    providers = get_saved_providers()
    saved_provider_id = provider_id or uuid.uuid4().hex
    provider_record = {
        "id": saved_provider_id,
        "name": details["name"],
        "base_url": details["base_url"],
        "openapi_url": details["openapi_url"],
        "service_version": details["service_version"],
        "selected_interface": selected_interface,
        "selected_interface_target": str(
            (selected_interface_details.get("target") or selected_interface_details.get("address") or "")
        ).strip(),
        "enabled": bool(enabled),
    }

    replaced = False
    updated = []
    for provider in providers:
        if provider["id"] == saved_provider_id:
            updated.append(provider_record)
            replaced = True
        else:
            updated.append(provider)
    if not replaced:
        updated.append(provider_record)

    _write_driver_config_file(provider_record, details)
    save_providers(updated)
    return saved_provider_id


def normalize_base_url(service_url):
    """Normalize a service URL or openapi URL to the provider base URL."""
    url = (service_url or "").strip().rstrip("/")
    if not url:
        raise ProviderRegistrationError("driver service URL is required")
    if url.endswith("/openapi.json"):
        url = url[: -len("/openapi.json")]
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ProviderRegistrationError("driver service URL must include scheme and host")
    return url


def get_openapi_url(service_url):
    """Build the OpenAPI URL from a service URL."""
    return normalize_base_url(service_url) + "/openapi.json"


def _normalize_interface_metadata(base_url, spec):
    """Extract the advertised interface inventory from the contract's x-meter-driver block.

    Without the block, or without an http entry in it, one http interface
    at the registered base URL is synthesized and becomes the default.
    """
    extension = spec.get(DISCOVERY_EXTENSION) or {}
    interface_entries = extension.get("interfaces") or []

    interfaces = []
    seen_types = set()
    for entry in interface_entries:
        if not isinstance(entry, dict):
            continue

        interface_type = str(entry.get("type") or "").strip().lower()
        if not interface_type or interface_type in seen_types:
            continue

        interface = {
            "type": interface_type,
            "label": str(entry.get("label") or interface_type.upper()),
        }
        if entry.get("base_url"):
            interface["base_url"] = str(entry["base_url"])
            interface["address"] = interface["base_url"]
        elif entry.get("target"):
            interface["target"] = str(entry["target"])
            interface["address"] = interface["target"]
        else:
            interface["address"] = ""

        interfaces.append(interface)
        seen_types.add(interface_type)

    if "http" not in seen_types:
        interfaces.insert(
            0,
            {
                "type": "http",
                "label": "HTTP API",
                "base_url": base_url,
                "address": base_url,
            },
        )
        seen_types.add("http")

    default_interface = str(extension.get("default_interface") or "").strip().lower()
    if default_interface not in seen_types:
        default_interface = (
            "http" if "http" in seen_types else (interfaces[0]["type"] if interfaces else "http")
        )

    return {
        "interfaces": interfaces,
        "default_interface": default_interface,
    }


def _apply_selected_interface(details, selected_interface=None):
    """Attach the selected interface and its live details to a metadata dict."""
    interface_map = {interface["type"]: interface for interface in details.get("interfaces") or []}
    selected = str(selected_interface or "").strip().lower()
    if not selected:
        selected = details.get("default_interface") or ""

    if selected not in interface_map:
        selected = details.get("default_interface") or next(iter(interface_map), "http")

    details["selected_interface"] = selected
    details["selected_interface_details"] = interface_map.get(selected)
    return details


def _fallback_interface_metadata(base_url, selected_interface=None):
    """Return a conservative interface inventory when live discovery fails."""
    interfaces = [
        {
            "type": "http",
            "label": "HTTP API",
            "base_url": base_url,
            "address": base_url,
        }
    ]
    normalized_selected = str(selected_interface or "").strip().lower()
    if normalized_selected and normalized_selected != "http":
        interfaces.append(
            {
                "type": normalized_selected,
                "label": normalized_selected.upper(),
                "address": "",
            }
        )

    return _apply_selected_interface(
        {
            "name": "",
            "base_url": base_url,
            "openapi_url": get_openapi_url(base_url),
            "service_version": "",
            "driver_requirement_fields": [],
            "driver_requirement_field_map": {},
            "vendor_option_fields": [],
            "vendor_option_field_map": {},
            "interfaces": interfaces,
            "default_interface": "http",
        },
        selected_interface=selected_interface,
    )


def validate_contract(service_url, timeout=10.0):
    """Fetch and validate the driver's OpenAPI contract, then discover its init fields.

    Follows the spec's integration sequence (section 2): GET /openapi.json,
    check it lists every required route, read x-meter-driver, then GET
    /v1/requirements. A driver missing any of that is not registrable.
    """
    base_url = normalize_base_url(service_url)
    openapi_url = get_openapi_url(service_url)
    try:
        response = httpx.get(openapi_url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ProviderRegistrationError("could not fetch driver OpenAPI contract") from exc

    try:
        spec = response.json()
    except ValueError as exc:
        raise ProviderRegistrationError("driver returned invalid JSON") from exc

    info = spec.get("info") or {}
    paths = spec.get("paths") or {}
    missing_paths = [path for path in REQUIRED_CONTRACT_PATHS if path not in paths]
    if missing_paths:
        raise ProviderRegistrationError(
            "driver contract missing required paths: {}".format(", ".join(missing_paths))
        )

    name = info.get("title")
    if not name:
        raise ProviderRegistrationError("driver contract missing info.title")

    driver_requirement_fields = _extract_driver_requirement_fields(base_url, spec, timeout=timeout)

    return {
        "name": str(name),
        "base_url": base_url,
        "openapi_url": openapi_url,
        "service_version": str(info.get("version") or ""),
        "driver_requirement_fields": driver_requirement_fields,
        "driver_requirement_field_map": {field["name"]: field for field in driver_requirement_fields},
        "vendor_option_fields": _extract_vendor_option_fields(spec),
        "vendor_option_field_map": _vendor_option_field_map(spec),
        **_normalize_interface_metadata(base_url, spec),
    }


def get_live_interface_details(service_url, selected_interface=None, timeout=2.0):
    """Fetch the current interface inventory advertised by the provider."""
    base_url = normalize_base_url(service_url)
    try:
        provider_data = validate_contract(base_url, timeout=timeout)
    except ProviderRegistrationError as exc:
        details = _fallback_interface_metadata(
            base_url,
            selected_interface=selected_interface,
        )
        details["error"] = str(exc)
        return details

    return _apply_selected_interface(
        provider_data,
        selected_interface=selected_interface,
    )


def get_runtime_status(service_url, timeout=2.0, include_gateway_status=True):
    """Check driver liveness on GET /v1/healthz and, optionally, gateway state on GET /v1/status."""
    base_url = normalize_base_url(service_url)
    healthz_url = base_url.rstrip("/") + "/v1/healthz"
    status_url = base_url.rstrip("/") + "/v1/status"
    try:
        response = httpx.get(healthz_url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {
            "online": False,
            "message": str(exc) or "unreachable",
            "checked_url": healthz_url,
            "gateway_checked": bool(include_gateway_status),
            "gateway_active": False,
            "gateway_type": None,
        }

    status = {
        "online": True,
        "message": "online",
        "checked_url": healthz_url,
        "gateway_checked": bool(include_gateway_status),
    }
    if not include_gateway_status:
        status["gateway_active"] = False
        status["gateway_type"] = None
        return status
    try:
        gateway_response = httpx.get(status_url, timeout=timeout)
        gateway_response.raise_for_status()
        gateway_data = gateway_response.json()
        status["gateway_active"] = bool(gateway_data.get("connected"))
        status["gateway_type"] = gateway_data.get("gateway_type")
    except (httpx.HTTPError, ValueError):
        status["gateway_active"] = False
        status["gateway_type"] = None
    return status
