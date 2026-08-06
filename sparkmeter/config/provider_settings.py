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


def _requirements_url(service_url):
    """Build the requirements endpoint URL from a service URL."""
    return normalize_base_url(service_url) + "/v1/requirements"


def _fetch_requirements_payload(service_url, timeout=10.0):
    """Fetch the optional driver requirements payload."""
    response = httpx.get(_requirements_url(service_url), timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ProviderRegistrationError("driver requirements response must be a JSON object")
    return payload


def _iter_candidate_requirement_schemas(spec):
    """Yield object schemas that may describe driver requirement fields."""

    def _walk(schema, depth=0):
        if depth > 6:
            return
        resolved = _resolve_schema(spec, schema)
        if not isinstance(resolved, dict):
            return
        properties = resolved.get("properties") or {}
        if properties:
            yield resolved
            # Requirement fields are frequently nested (e.g. under
            # vendor_options), so descend into object-typed properties too.
            for prop_schema in properties.values():
                yield from _walk(prop_schema, depth + 1)

    components = (spec.get("components") or {}).get("schemas") or {}
    for schema in components.values():
        yield from _walk(schema)

    for path_item in (spec.get("paths") or {}).values():
        if not isinstance(path_item, dict):
            continue
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            schema = (
                ((operation.get("requestBody") or {}).get("content") or {})
                .get("application/json", {})
                .get("schema", {})
            )
            yield from _walk(schema)


def _best_matching_requirements_schema(spec, required_fields):
    """Find the schema whose properties best match the reported required fields."""
    required_names = set(required_fields or [])
    best_schema = {}
    best_score = 0
    for schema in _iter_candidate_requirement_schemas(spec):
        properties = set((schema.get("properties") or {}).keys())
        score = len(required_names & properties)
        if score > best_score:
            best_schema = schema
            best_score = score
    return best_schema if best_score else {}


# Type hints for the spec's standard driver init fields, used when the
# driver's OpenAPI does not describe a required field's schema itself.
_STANDARD_INIT_FIELD_TYPES = {
    "aes_key": "string",
    "channel": "integer",
    "heartbeat_period_duration": "integer",
}


def _extract_fields_from_requirements(spec, required_fields):
    """Build normalized field specs from a requirements list plus OpenAPI schema hints."""
    schema = _best_matching_requirements_schema(spec, required_fields)
    properties = schema.get("properties") or {}
    schema_required = set(schema.get("required") or [])
    fields = []
    for name in required_fields:
        resolved = dict(_resolve_schema(spec, properties.get(name) or {}))
        if not resolved.get("type") and name in _STANDARD_INIT_FIELD_TYPES:
            resolved["type"] = _STANDARD_INIT_FIELD_TYPES[name]
        fields.append(
            _field_spec(
                name,
                resolved,
                name in schema_required or name in set(required_fields),
            )
        )
    return fields


def _extract_driver_requirement_fields(base_url, spec, timeout=10.0):
    """Discover required driver fields from /v1/requirements, else OpenAPI."""
    vendor_option_fields = _extract_vendor_option_fields(spec)
    if not vendor_option_fields:
        # The driver declares no configurable requirements, so there is
        # nothing to enrich and no reason to probe /v1/requirements.
        return []
    try:
        payload = _fetch_requirements_payload(base_url, timeout=timeout)
        required_fields = payload.get("required_fields") or []
        if isinstance(required_fields, list) and required_fields:
            normalized = [str(name).strip() for name in required_fields if str(name).strip()]
            if normalized:
                return _extract_fields_from_requirements(spec, normalized)
    except (httpx.HTTPError, ValueError, ProviderRegistrationError):
        pass

    return vendor_option_fields


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
    """Return the required field names from a config payload."""
    names = payload.get("required_fields") or []
    if not isinstance(names, list):
        raise DriverConfigError("required_fields must be a list")
    normalized = []
    for entry in names:
        if isinstance(entry, dict):
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
    """Validate required field presence in a driver config payload."""
    required_fields = _required_field_names(payload)
    required_field_specs = _required_field_specs(payload)
    field_values = _field_values(payload)
    missing = [
        name for name in required_fields if name not in field_values or field_values[name] in (None, "")
    ]
    if missing:
        raise DriverConfigError("required fields are missing values: {}".format(", ".join(missing)))
    coerced_field_values = {
        name: _coerce_field_value(name, value, required_field_specs.get(name))
        for name, value in field_values.items()
    }
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
    """Extract the advertised interface inventory from a provider contract."""
    extension = spec.get("x-open-thunder") or {}
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
    """Fetch and validate the provider's OpenAPI contract."""
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
    required_paths = ("/v1/commands", "/v1/events")
    missing_paths = [path for path in required_paths if path not in paths]
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
    """Check whether the provider service is currently reachable."""
    base_url = normalize_base_url(service_url)
    healthz_url = base_url.rstrip("/") + "/v1/healthz"
    legacy_health_url = base_url.rstrip("/") + "/health"
    status_url = base_url.rstrip("/") + "/v1/status"
    urls = (healthz_url, legacy_health_url)
    last_error = None
    for url in urls:
        try:
            response = httpx.get(url, timeout=timeout)
            response.raise_for_status()
            status = {
                "online": True,
                "message": "online",
                "checked_url": url,
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
                status["gateway_checked"] = True
                status["gateway_active"] = False
                status["gateway_type"] = None
            return status
        except httpx.HTTPError as exc:
            last_error = exc

    return {
        "online": False,
        "message": str(last_error) if last_error is not None else "unreachable",
        "checked_url": healthz_url,
        "gateway_checked": bool(include_gateway_status),
        "gateway_active": False,
        "gateway_type": None,
    }
