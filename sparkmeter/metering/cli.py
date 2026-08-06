"""Dynamic metering CLI, built from the target driver's live /openapi.json.

    flask metering --driver <url|id> <command> [--field ...]

The command list and each command's options are discovered from the selected
driver's OpenAPI document at invocation time: every POST/DELETE operation
becomes a subcommand, and its options come from that operation's requestBody
schema (nested objects flatten to dotted options, e.g.
`--configuration.power-limit`). A command exists only if the chosen driver
publishes it, so optional operations (ping, query-neighbors, ...) appear only
for drivers that declare them. Path parameters (e.g. node_id) become required
options and are substituted into the request path.

`--driver` is used directly if it looks like a URL, otherwise it is treated as
a registered driver id and resolved to its base_url via provider settings.
"""

import logging
import re
import uuid
from typing import Any

import click
import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# Driver resolution + OpenAPI discovery
# ---------------------------------------------------------------------------


def _flask_app_from_ctx(ctx: click.Context):
    """Find the Flask app via the ScriptInfo the `flask` CLI stashes on ctx.obj."""
    try:
        from flask.cli import ScriptInfo
    except ImportError:
        return None
    node = ctx
    while node is not None:
        if isinstance(node.obj, ScriptInfo):
            return node.obj.load_app()
        node = node.parent
    return None


def _resolve_driver_url(ctx: click.Context, driver: str) -> str:
    """Resolve `--driver` (a URL, or a registered driver id) to a base URL."""
    if driver.startswith(("http://", "https://")):
        return driver.rstrip("/")

    from flask import has_app_context

    from sparkmeter.config.provider_settings import get_provider

    if has_app_context():
        provider = get_provider(driver)
    else:
        app = _flask_app_from_ctx(ctx)
        if app is None:
            raise click.BadParameter(
                "cannot resolve driver id {!r} without an app context; pass a URL".format(driver)
            )
        with app.app_context():
            provider = get_provider(driver)

    if not provider:
        raise click.BadParameter("no registered driver with id {!r}".format(driver))
    base_url = str(provider.get("base_url") or "").strip()
    if not base_url:
        raise click.BadParameter("driver {!r} has no base_url".format(driver))
    return base_url.rstrip("/")


def _fetch_openapi(base_url: str) -> dict[str, Any]:
    with httpx.Client(base_url=base_url, timeout=_DEFAULT_TIMEOUT) as client:
        response = client.get("/openapi.json")
        response.raise_for_status()
        return response.json()


def _spec_and_url(ctx: click.Context) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch (and memoize on the click ctx) the selected driver's OpenAPI doc."""
    driver = (ctx.params or {}).get("driver")
    if not driver:
        return None, None
    cache = ctx.meta.setdefault("_metering_spec", {})
    if "spec" not in cache:
        base_url = _resolve_driver_url(ctx, driver)
        cache["url"] = base_url
        try:
            cache["spec"] = _fetch_openapi(base_url)
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException("could not fetch {}/openapi.json: {}".format(base_url, exc)) from exc
    return cache.get("spec"), cache.get("url")


# ---------------------------------------------------------------------------
# OpenAPI schema -> click options
# ---------------------------------------------------------------------------


def _resolve_ref(spec: dict, ref: str) -> dict:
    node: Any = spec
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def _resolve_schema(spec: dict, schema: Any) -> dict:
    if not isinstance(schema, dict):
        return {}
    if "$ref" in schema:
        return _resolve_schema(spec, _resolve_ref(spec, schema["$ref"]))
    if "allOf" in schema:
        merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
        for sub in schema["allOf"]:
            sub = _resolve_schema(spec, sub)
            merged["properties"].update(sub.get("properties", {}))
            merged["required"].extend(sub.get("required", []))
        merged["properties"].update(schema.get("properties", {}))
        merged["required"].extend(schema.get("required", []))
        return merged
    return schema


def _leaf_options(spec: dict, schema: Any, prefix: tuple[str, ...] = ()):
    """Yield (path_segments, prop_schema, required) for each leaf field."""
    schema = _resolve_schema(spec, schema)
    out: list[tuple[tuple[str, ...], dict, bool]] = []
    required = set(schema.get("required", []))
    for name, prop in (schema.get("properties") or {}).items():
        resolved = _resolve_schema(spec, prop)
        if resolved.get("type") == "object" and resolved.get("properties"):
            out.extend(_leaf_options(spec, resolved, prefix + (name,)))
        else:
            out.append((prefix + (name,), resolved, name in required))
    return out


def _option_name(path: tuple[str, ...]) -> str:
    return "--" + ".".join(seg.replace("_", "-") for seg in path)


def _option_dest(path: tuple[str, ...]) -> str:
    return "__".join(path)


def _click_kwargs(prop: dict, required: bool) -> dict[str, Any]:
    enum = prop.get("enum")
    ptype = prop.get("type")
    kwargs: dict[str, Any] = {"required": required, "default": None}
    if enum:
        kwargs["type"] = click.Choice([str(e) for e in enum])
    elif ptype == "integer":
        kwargs["type"] = click.INT
    elif ptype == "number":
        kwargs["type"] = click.FLOAT
    elif ptype == "boolean":
        kwargs.pop("default", None)
        kwargs["is_flag"] = True
        kwargs["default"] = False
    elif ptype == "array":
        kwargs.pop("default", None)
        kwargs["multiple"] = True
        kwargs["type"] = click.STRING
    else:
        kwargs["type"] = click.STRING
    return kwargs


def _assemble_body(leaf_options, kwargs: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for path, _prop, _required in leaf_options:
        value = kwargs.get(_option_dest(path))
        if value is None or (isinstance(value, tuple) and not value):
            continue
        node = body
        for seg in path[:-1]:
            node = node.setdefault(seg, {})
        node[path[-1]] = list(value) if isinstance(value, tuple) else value
    return body


# ---------------------------------------------------------------------------
# Operation -> click command
# ---------------------------------------------------------------------------


def _kebab(operation_id: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", operation_id).lower()


def _iter_command_operations(spec: dict):
    """Yield (name, method, path, operation) for each POST/DELETE operation."""
    for path, methods in (spec.get("paths") or {}).items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.lower() not in ("post", "delete") or not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId") or "{}{}".format(method, path)
            yield (_kebab(operation_id), method.lower(), path, operation)


def _path_param_dest(name: str) -> str:
    return "path__" + name


def _submit(base_url: str, method: str, path: str, body: dict[str, Any]) -> None:
    headers = {"X-Client-Id": "cli-" + uuid.uuid4().hex[:8]}
    with httpx.Client(base_url=base_url, timeout=_DEFAULT_TIMEOUT, headers=headers) as client:
        response = client.request(method.upper(), path, json=body or None)
    click.echo("{} {} -> {}".format(method.upper(), path, response.status_code))
    text = response.text.strip()
    if text:
        click.echo(text)
    if response.is_error:
        raise SystemExit(1)


def _build_command(spec: dict, name: str, method: str, path: str, operation: dict, base_url: str):
    path_params = [p for p in operation.get("parameters", []) if p.get("in") == "path"]
    body_schema = (
        operation.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
    )
    leaf_options = _leaf_options(spec, body_schema) if body_schema else []

    def callback(**kwargs: Any) -> None:
        actual_path = path
        for param in path_params:
            pname = param["name"]
            actual_path = actual_path.replace("{%s}" % pname, str(kwargs.pop(_path_param_dest(pname))))
        _submit(base_url, method, actual_path, _assemble_body(leaf_options, kwargs))

    cmd = click.command(name, help=operation.get("summary") or "")(callback)
    for path_seg, prop, required in reversed(leaf_options):
        cmd = click.option(_option_name(path_seg), _option_dest(path_seg), **_click_kwargs(prop, required))(
            cmd
        )
    for param in reversed(path_params):
        pname = param["name"]
        cmd = click.option(
            "--" + pname.replace("_", "-"),
            _path_param_dest(pname),
            required=True,
            help=param.get("description") or "",
        )(cmd)
    return cmd


class _MeteringGroup(click.Group):
    """A click group whose subcommands are the selected driver's operations."""

    def list_commands(self, ctx: click.Context):
        spec, _ = _spec_and_url(ctx)
        if not spec:
            return []
        return sorted(name for name, *_ in _iter_command_operations(spec))

    def get_command(self, ctx: click.Context, name: str):
        spec, base_url = _spec_and_url(ctx)
        if not spec:
            return None
        for op_name, method, path, operation in _iter_command_operations(spec):
            if op_name == name:
                return _build_command(spec, name, method, path, operation, base_url)
        return None


@click.group(
    cls=_MeteringGroup,
    name="metering",
    help="Metering-provider commands, discovered from the target driver's /openapi.json.",
)
@click.option(
    "--driver",
    is_eager=True,  # parse before --help so the discovered commands show in help
    metavar="URL|ID",
    help="Target driver base URL or registered driver id.",
)
def metering(driver: str | None) -> None:
    """Root of the dynamic metering CLI; `--driver` selects the target."""
