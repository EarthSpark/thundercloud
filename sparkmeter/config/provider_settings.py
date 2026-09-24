# -*- coding: utf-8 -*-
"""Meter driver settings and validation helpers."""

import json
import logging
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx
from meter_driver_spec.http.models import RequirementsResponse
from pydantic import ValidationError

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

# The operations the Meter Driver Specification (v1.4.0, docs/spec/index.md
# section 4) marks Required, other than GET /openapi.json, which is the
# document being checked. A driver's /openapi.json must document every one
# of these under its path with this method; the two Recommended routes
# (/v1/nodes/{node_id}/balance-and-flags, /v1/shutdown) are not demanded.
REQUIRED_CONTRACT_OPERATIONS = (
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

# The spec's interface-discovery extension block on /openapi.json (section 5.1).
DISCOVERY_EXTENSION = "x-meter-driver"

# The gRPC profile's ConfigureDriver message (spec section 7,
# meter_driver.proto) has fixed fields, so a driver used over gRPC must list
# these on /v1/requirements whatever else it asks for.
GRPC_INIT_REQUIRED_FIELDS = ("heartbeat_period_duration", "aes_key")

# A path template parameter, e.g. {node_id}; its name is not significant
# when matching a driver's paths against the spec's.
_PATH_PARAM_RE = re.compile(r"\{[^}]*\}")

# The spec's AesKeyInput (section 3): a 16-byte key as 32 hex characters or
# as 16 byte values.
_AES_KEY_HEX_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_AES_KEY_BYTES = 16

# Bound on nested schema composition (allOf parts, $ref chains) followed
# while reading a document, so a self-referential schema cannot recurse
# without end.
_SCHEMA_DEPTH_LIMIT = 8


# ---------------------------------------------------------------------------
# OpenAPI schema helpers
# ---------------------------------------------------------------------------


def _resolve_local_ref(spec, ref):
    """Resolve a local JSON Pointer reference within an OpenAPI document."""
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return None

    node = spec
    for part in ref[2:].split("/"):
        if not isinstance(node, dict):
            return None
        node = node.get(part.replace("~1", "/").replace("~0", "~"))
        if node is None:
            return None
    return node


def _resolve_schema(spec, schema):
    """Resolve a schema object to a plain dict, following $ref chains.

    Anything that is not a dict, or a $ref that does not resolve to one,
    is an empty schema. A reference cycle stops at its first repeat.
    """
    seen = set()
    while isinstance(schema, dict) and "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str) or ref in seen:
            return {}
        seen.add(ref)
        schema = _resolve_local_ref(spec, ref)
    return schema if isinstance(schema, dict) else {}


def _schema_type(schema):
    """Return a schema's JSON type name, or "" when it declares none.

    An OpenAPI 3.1 type array (["string", "null"]) yields its first non-null
    entry.
    """
    value = (schema or {}).get("type")
    if isinstance(value, list):
        for entry in value:
            if entry != "null":
                return str(entry).strip().lower()
        return ""
    return str(value or "").strip().lower()


def _object_schema(spec, schema, depth=0):
    """Resolve an object schema, merging the properties and required lists of its allOf parts."""
    resolved = _resolve_schema(spec, schema)
    parts = resolved.get("allOf")
    if not isinstance(parts, list) or depth >= _SCHEMA_DEPTH_LIMIT:
        return resolved

    merged = {key: value for key, value in resolved.items() if key != "allOf"}
    properties = dict(merged["properties"]) if isinstance(merged.get("properties"), dict) else {}
    required = list(merged["required"]) if isinstance(merged.get("required"), list) else []
    for part in parts:
        part_schema = _object_schema(spec, part, depth + 1)
        if isinstance(part_schema.get("properties"), dict):
            properties.update(part_schema["properties"])
        if isinstance(part_schema.get("required"), list):
            required.extend(name for name in part_schema["required"] if name not in required)
        for key, value in part_schema.items():
            if key not in ("properties", "required", "allOf"):
                merged.setdefault(key, value)
    merged["properties"] = properties
    merged["required"] = required
    return merged


def _dig(node, *keys):
    """Walk nested dicts by key; anything missing or not a dict yields {}."""
    for key in keys:
        if not isinstance(node, dict):
            return {}
        node = node.get(key)
    return node if isinstance(node, dict) else {}


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
    properties = resolved.get("properties") if isinstance(resolved.get("properties"), dict) else {}
    command_type = _resolve_schema(spec, properties.get("command_type") or {})
    values = []
    if "const" in command_type:
        values.append(command_type["const"])
    if "enum" in command_type and isinstance(command_type["enum"], list):
        values.extend(command_type["enum"])
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _find_configure_provider_schema(spec):
    """Locate the configure-provider command schema in the OpenAPI document."""
    request_schema = _dig(
        spec, "paths", "/v1/commands", "post", "requestBody", "content", "application/json", "schema"
    )
    request_schema = _resolve_schema(spec, request_schema)

    candidates = request_schema.get("oneOf")
    for candidate in candidates if isinstance(candidates, list) else []:
        values = _command_type_values(spec, candidate)
        if "configure_provider" in values:
            return _resolve_schema(spec, candidate)

    components = _dig(spec, "components", "schemas")
    for schema in components.values():
        values = _command_type_values(spec, schema)
        if "configure_provider" in values:
            return _resolve_schema(spec, schema)

    return {}


def _field_spec(name, schema, required):
    """Normalize a field description for the form and config layers."""
    field_type = _schema_type(schema) or "string"
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
    properties = (
        command_schema.get("properties") if isinstance(command_schema.get("properties"), dict) else {}
    )
    vendor_schema = _object_schema(spec, properties.get("vendor_options") or {})

    fields = []
    required_fields = (
        set(vendor_schema["required"]) if isinstance(vendor_schema.get("required"), list) else set()
    )
    vendor_properties = (
        vendor_schema.get("properties") if isinstance(vendor_schema.get("properties"), dict) else {}
    )
    for field_name, field_schema in vendor_properties.items():
        resolved_field = _scalar_schema(spec, field_schema)
        fields.append(_field_spec(str(field_name), resolved_field, field_name in required_fields))

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


def _validation_summary(exc):
    """One line naming each pydantic validation error's location and message."""
    return "; ".join(
        "{}: {}".format(".".join(str(part) for part in error.get("loc") or ()) or "body", error.get("msg"))
        for error in exc.errors()
    )


def _required_field_names_from_requirements(payload):
    """Return the `required_fields` names from a RequirementsResponse, in the driver's order.

    The payload is validated as the spec's RequirementsResponse model
    (`required_fields` is an array of strings). A blank name is rejected;
    a repeated name is kept once.
    """
    try:
        requirements = RequirementsResponse.model_validate(payload)
    except ValidationError as exc:
        raise ProviderRegistrationError(
            "driver requirements response is not a valid RequirementsResponse: {}".format(
                _validation_summary(exc)
            )
        ) from exc
    names = []
    for name in requirements.required_fields:
        if not name.strip():
            raise ProviderRegistrationError("driver requirements response lists a blank field name")
        if name not in names:
            names.append(name)
    return names


def _fetch_requirements_payload(service_url, timeout=10.0):
    """GET /v1/requirements and return the driver's required field names."""
    url = _requirements_url(service_url)
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ProviderRegistrationError(
            "could not fetch driver requirements from /v1/requirements: {}".format(
                str(exc) or exc.__class__.__name__
            )
        ) from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ProviderRegistrationError("driver requirements response is not valid JSON") from exc
    return _required_field_names_from_requirements(payload)


def _init_request_schema(spec):
    """Return the document's InitRequest schema as one object schema.

    The POST /v1/init request-body schema is authoritative; a document that
    documents init fields only under components.schemas.InitRequest is
    read from there. $ref chains are followed and allOf parts merged.
    """
    schema = _dig(spec, "paths", "/v1/init", "post", "requestBody", "content", "application/json", "schema")
    resolved = _object_schema(spec, schema)
    if isinstance(resolved.get("properties"), dict) and resolved["properties"]:
        return resolved
    return _object_schema(spec, _dig(spec, "components", "schemas").get("InitRequest") or {})


def _scalar_schema(spec, schema):
    """Resolve a property schema to the alternative describing its scalar wire form.

    A oneOf/anyOf without its own type (the spec's AesKeyInput: 32-hex
    string or 16-byte array) reduces to its first string-typed alternative,
    else its first alternative, so the form layer sees one type and pattern.
    """
    resolved = _resolve_schema(spec, schema)
    alternatives = resolved.get("oneOf") or resolved.get("anyOf")
    if _schema_type(resolved) or not isinstance(alternatives, list) or not alternatives:
        return resolved
    # Alternatives that are not schema objects (or $refs to none) are skipped.
    resolved_alternatives = [
        resolved_alternative
        for resolved_alternative in (_resolve_schema(spec, alternative) for alternative in alternatives)
        if resolved_alternative
    ]
    for alternative in resolved_alternatives:
        if _schema_type(alternative) == "string":
            return alternative
    return resolved_alternatives[0] if resolved_alternatives else {}


def _extract_fields_from_requirements(spec, required_fields):
    """Build field specs for the advertised init fields, typed from InitRequest.

    A field the document does not describe is typed as a string, with a
    warning: the spec (section 5.2) says the names must match the init
    request schema in /openapi.json.
    """
    init_schema = _init_request_schema(spec)
    properties = init_schema.get("properties") if isinstance(init_schema.get("properties"), dict) else {}
    fields = []
    for name in required_fields:
        if name not in properties:
            logger.warning(
                "driver requirement field %r is not described by the contract's InitRequest schema; "
                "treating it as a string",
                name,
            )
        fields.append(_field_spec(name, _scalar_schema(spec, properties.get(name) or {}), True))
    return fields


def _extract_driver_requirement_fields(base_url, spec, timeout=10.0):
    """Discover the driver's init fields.

    GET /v1/requirements is required and its list order is kept; each name
    is typed from the document's InitRequest schema. Every other
    InitRequest property follows as an optional field, in schema order.
    Fields from the optional /v1/commands vendor-option extension, if the
    document has one, follow as optional extras for names not already
    listed, so InitRequest typing wins for a name present in both.
    """
    names = _fetch_requirements_payload(base_url, timeout=timeout)
    fields = _extract_fields_from_requirements(spec, names)
    known = {field["name"] for field in fields}
    init_schema = _init_request_schema(spec)
    init_properties = init_schema.get("properties") if isinstance(init_schema.get("properties"), dict) else {}
    for name, schema in init_properties.items():
        if name in known:
            continue
        fields.append(_field_spec(name, _scalar_schema(spec, schema), False))
        known.add(name)
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


def _stored_field_specs(payload):
    """Return a config payload's field specs keyed by name, in stored order.

    Entries in `required_fields` are the specs written at registration
    (dicts with name, type, required, pattern, minimum, maximum, ...). A
    bare name is a config written before field types were recorded: it is
    treated as a required string field, and a warning says that
    re-registering the driver records its types.
    """
    entries = payload.get("required_fields") or []
    if not isinstance(entries, list):
        raise DriverConfigError("required_fields must be a list")

    specs = {}
    untyped = []
    for entry in entries:
        if isinstance(entry, dict):
            name = str(entry.get("name") or "").strip()
            if name:
                specs[name] = entry
            continue
        name = str(entry).strip()
        if name:
            specs[name] = {"name": name, "type": "string", "required": True}
            untyped.append(name)
    if untyped:
        logger.warning(
            "driver config lists required_fields without types (%s); they are treated as required "
            "strings. Re-register the driver to record the types its contract declares.",
            ", ".join(untyped),
        )
    return specs


def _required_field_names(payload):
    """Return the names a config payload must supply values for.

    A spec entry marked `"required": false` is an optional extra and is
    not demanded.
    """
    return [name for name, spec in _stored_field_specs(payload).items() if spec.get("required") is not False]


def _field_values(payload):
    """Return the field_values mapping from a config payload."""
    values = payload.get("field_values") or {}
    if not isinstance(values, dict):
        raise DriverConfigError("field_values must be an object")
    return values


def _is_blank(value):
    """Whether a stored value counts as not supplied."""
    return value is None or (isinstance(value, str) and not value.strip())


def _coerce_aes_key(value):
    """Return an aes_key value in one of the spec's AesKeyInput forms.

    The wire forms (spec section 3) are 32 hex characters or an array of
    exactly 16 integers 0..255.
    """
    if isinstance(value, str):
        value = value.strip()
        if _AES_KEY_HEX_RE.fullmatch(value):
            return value
    elif (
        isinstance(value, list)
        and len(value) == _AES_KEY_BYTES
        and all(isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 255 for item in value)
    ):
        return list(value)
    raise DriverConfigError(
        "field 'aes_key' must be 32 hex characters or an array of {} byte values".format(_AES_KEY_BYTES)
    )


def _coerce_field_value(name, value, spec):
    """Coerce a raw JSON field value to the type the driver's contract declares."""
    if name == "aes_key":
        return _coerce_aes_key(value)
    if isinstance(value, str):
        value = value.strip()
    field_type = _schema_type(spec) or "string"
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
    if field_type == "array":
        if isinstance(value, list):
            return list(value)
        raise DriverConfigError("field {!r} must be an array".format(name))
    if field_type == "object":
        if isinstance(value, dict):
            return dict(value)
        raise DriverConfigError("field {!r} must be an object".format(name))
    if isinstance(value, (list, dict)):
        raise DriverConfigError("field {!r} must be a string".format(name))
    return value if isinstance(value, str) else str(value)


def _check_field_constraints(name, value, spec):
    """Enforce the pattern, minimum and maximum the driver's contract declared for a field."""
    pattern = str((spec or {}).get("pattern") or "")
    if pattern and isinstance(value, str):
        try:
            matched = re.search(pattern, value) is not None
        except re.error:
            logger.warning("field %r declares an unusable pattern %r; not checked", name, pattern)
            matched = True
        if not matched:
            raise DriverConfigError("field {!r} must match the pattern {}".format(name, pattern))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return
    minimum = (spec or {}).get("minimum")
    if isinstance(minimum, (int, float)) and not isinstance(minimum, bool) and value < minimum:
        raise DriverConfigError("field {!r} must be at least {}".format(name, minimum))
    maximum = (spec or {}).get("maximum")
    if isinstance(maximum, (int, float)) and not isinstance(maximum, bool) and value > maximum:
        raise DriverConfigError("field {!r} must be at most {}".format(name, maximum))


def validate_provider_config_payload(payload):
    """Validate a driver config payload and return the typed init body.

    Every required field needs a non-blank value. Values are coerced to
    the types the driver's contract declared and checked against its
    pattern/minimum/maximum. Only fields the driver asked for are
    returned: an optional field left blank is omitted, and a key the
    driver never listed is dropped with a warning.
    """
    specs = _stored_field_specs(payload)
    required_fields = [name for name, spec in specs.items() if spec.get("required") is not False]
    field_values = _field_values(payload)
    missing = [name for name in required_fields if _is_blank(field_values.get(name))]
    if missing:
        raise DriverConfigError("required fields are missing values: {}".format(", ".join(missing)))

    unknown = [name for name in field_values if name not in specs]
    if unknown:
        logger.warning(
            "driver config field_values has keys the driver did not ask for; not sent: %s", ", ".join(unknown)
        )

    coerced_field_values = {}
    for name, spec in specs.items():
        if name not in field_values or _is_blank(field_values[name]):
            continue
        value = _coerce_field_value(name, field_values[name], spec)
        _check_field_constraints(name, value, spec)
        coerced_field_values[name] = value
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


def check_grpc_selection(details):
    """Raise ProviderRegistrationError unless the contract supports being driven over gRPC.

    The spec fixes no gRPC port, so gRPC needs a grpc interface with a
    target in x-meter-driver. Its ConfigureDriver message has fixed
    fields, so the driver's /v1/requirements must list
    heartbeat_period_duration and aes_key among the required fields.
    """
    grpc_interface = next(
        (interface for interface in details.get("interfaces") or [] if interface.get("type") == "grpc"),
        None,
    )
    if grpc_interface is None:
        raise ProviderRegistrationError(
            "gRPC is not available: the driver's x-meter-driver block advertises no grpc interface"
        )
    if not (grpc_interface.get("target") or grpc_interface.get("address")):
        raise ProviderRegistrationError(
            "gRPC is not available: the driver's grpc interface advertises no target"
        )
    required_names = {
        field["name"] for field in details.get("driver_requirement_fields") or [] if field.get("required")
    }
    missing = [name for name in GRPC_INIT_REQUIRED_FIELDS if name not in required_names]
    if missing:
        raise ProviderRegistrationError(
            "gRPC init (ConfigureDriver) needs the init fields {} but the driver's /v1/requirements "
            "does not list: {}".format(", ".join(GRPC_INIT_REQUIRED_FIELDS), ", ".join(missing))
        )


def save_provider_settings(service_url, selected_interface, enabled=True, provider_id=None):
    """Persist a meter driver entry and return its id.

    A gRPC selection is refused (ProviderRegistrationError) unless the
    contract advertises a grpc target and the init fields gRPC needs; any
    other interface the contract does not advertise falls back to its
    default interface.
    """
    details = validate_contract(service_url)
    selected_interface = (selected_interface or details["default_interface"]).strip().lower()
    valid_interfaces = {interface["type"] for interface in details.get("interfaces") or []}
    if selected_interface == "grpc":
        check_grpc_selection(details)
    elif selected_interface not in valid_interfaces:
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
    That leniency goes beyond the spec, which says the block lists the
    active interfaces.
    """
    extension = spec.get(DISCOVERY_EXTENSION)
    if not isinstance(extension, dict):
        extension = {}
    interface_entries = extension.get("interfaces")
    if not isinstance(interface_entries, list):
        interface_entries = []

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


def _normalize_path_template(path):
    """Return a path with every {param} replaced by {} so parameter names do not matter."""
    return _PATH_PARAM_RE.sub("{}", path)


def _missing_required_operations(paths):
    """Return "METHOD /path" labels for the spec's required operations a document lacks.

    A path matches regardless of its parameter names (/v1/nodes/{id} is
    /v1/nodes/{node_id}); a trailing slash does not match.
    """
    by_template = {}
    for path, item in paths.items():
        if isinstance(path, str) and isinstance(item, dict):
            by_template.setdefault(_normalize_path_template(path), item)

    missing = []
    for method, path in REQUIRED_CONTRACT_OPERATIONS:
        item = by_template.get(_normalize_path_template(path), {})
        if not isinstance(item.get(method), dict):
            missing.append("{} {}".format(method.upper(), path))
    return missing


def _fetch_contract_document(service_url, timeout=10.0):
    """GET /openapi.json and check it is a document a compliant driver would serve.

    Returns `(base_url, openapi_url, document)`. The document must be a
    JSON object with `info.title`, a `paths` object listing every required
    operation, and, when present, an object-valued x-meter-driver block.
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
    if not isinstance(spec, dict):
        raise ProviderRegistrationError("driver OpenAPI document must be a JSON object")

    info = spec.get("info")
    if not isinstance(info, dict) or not info.get("title"):
        raise ProviderRegistrationError("driver contract missing info.title")

    paths = spec.get("paths")
    if not isinstance(paths, dict):
        raise ProviderRegistrationError("driver contract missing paths")
    missing = _missing_required_operations(paths)
    if missing:
        raise ProviderRegistrationError(
            "driver contract missing required routes: {}".format(", ".join(missing))
        )

    extension = spec.get(DISCOVERY_EXTENSION)
    if extension is not None and not isinstance(extension, dict):
        raise ProviderRegistrationError("driver contract {} must be an object".format(DISCOVERY_EXTENSION))

    return base_url, openapi_url, spec


def _contract_details(base_url, openapi_url, spec):
    """Build the details dict for a fetched contract, without init-field discovery."""
    info = spec["info"]
    return {
        "name": str(info["title"]),
        "base_url": base_url,
        "openapi_url": openapi_url,
        "service_version": str(info.get("version") or ""),
        "driver_requirement_fields": [],
        "driver_requirement_field_map": {},
        "vendor_option_fields": _extract_vendor_option_fields(spec),
        "vendor_option_field_map": _vendor_option_field_map(spec),
        **_normalize_interface_metadata(base_url, spec),
    }


def inspect_contract(service_url, timeout=10.0):
    """Fetch and validate the driver's OpenAPI contract and discover its interfaces.

    One round trip (GET /openapi.json). `driver_requirement_fields` is
    empty here: init-field discovery is a second round trip that
    registration makes through `validate_contract`.
    """
    base_url, openapi_url, spec = _fetch_contract_document(service_url, timeout=timeout)
    return _contract_details(base_url, openapi_url, spec)


def validate_contract(service_url, timeout=10.0):
    """Fetch and validate the driver's OpenAPI contract, then discover its init fields.

    Follows the spec's integration sequence (section 2): GET /openapi.json,
    check it lists every required operation, read x-meter-driver, then GET
    /v1/requirements typed by the document's InitRequest schema. A driver
    missing any of that is not registrable.
    """
    base_url, openapi_url, spec = _fetch_contract_document(service_url, timeout=timeout)
    details = _contract_details(base_url, openapi_url, spec)
    driver_requirement_fields = _extract_driver_requirement_fields(base_url, spec, timeout=timeout)
    details["driver_requirement_fields"] = driver_requirement_fields
    details["driver_requirement_field_map"] = {field["name"]: field for field in driver_requirement_fields}
    return details


def _stored_driver_fields(provider):
    """Return the field specs recorded in a saved provider's config file, if any."""
    if not provider:
        return []
    try:
        return list(_stored_field_specs(load_provider_runtime_settings(provider)).values())
    except DriverConfigError:
        return []


def get_live_interface_details(service_url, selected_interface=None, timeout=2.0, provider=None):
    """Fetch the interface inventory the driver advertises right now.

    Only GET /openapi.json is called, so an advertised gRPC target is
    never lost to a slow or failing /v1/requirements. When `provider` is
    given, `driver_requirement_fields` come from the fields recorded in
    its config file at registration.
    """
    base_url = normalize_base_url(service_url)
    try:
        details = inspect_contract(base_url, timeout=timeout)
    except ProviderRegistrationError as exc:
        details = _fallback_interface_metadata(base_url, selected_interface=selected_interface)
        details["error"] = str(exc)

    fields = _stored_driver_fields(provider)
    details["driver_requirement_fields"] = fields
    details["driver_requirement_field_map"] = {field["name"]: field for field in fields}
    return _apply_selected_interface(details, selected_interface=selected_interface)


def get_runtime_status(service_url, timeout=2.0, include_gateway_status=True):
    """Check driver liveness on GET /v1/healthz and, optionally, gateway state on GET /v1/status.

    Online means /v1/healthz answered 200 with the spec's HealthResponse
    `{"ok": true}`. With `include_gateway_status`, the `connected` and
    `gateway_type` of the JSON object /v1/status answers are reported; a
    transport failure, invalid JSON or a body that is not an object there
    leaves the driver online with no gateway.
    """
    base_url = normalize_base_url(service_url)
    healthz_url = base_url.rstrip("/") + "/v1/healthz"
    status_url = base_url.rstrip("/") + "/v1/status"

    def offline(message):
        return {
            "online": False,
            "message": message,
            "checked_url": healthz_url,
            "gateway_checked": bool(include_gateway_status),
            "gateway_active": False,
            "gateway_type": None,
        }

    try:
        response = httpx.get(healthz_url, timeout=timeout)
        response.raise_for_status()
        health = response.json()
    except httpx.HTTPError as exc:
        return offline(str(exc) or "unreachable")
    except ValueError:
        return offline("driver /v1/healthz response is not valid JSON")
    if not isinstance(health, dict) or health.get("ok") is not True:
        return offline('driver /v1/healthz did not answer {"ok": true}')

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
    except (httpx.HTTPError, ValueError):
        gateway_data = None
    if not isinstance(gateway_data, dict):
        status["gateway_active"] = False
        status["gateway_type"] = None
        return status
    status["gateway_active"] = bool(gateway_data.get("connected"))
    status["gateway_type"] = gateway_data.get("gateway_type")
    return status
