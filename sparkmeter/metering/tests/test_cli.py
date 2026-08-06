"""Tests for the discovery-driven metering CLI.

The CLI builds its command tree from the selected driver's live
`/openapi.json` at invocation time. These tests feed a fake OpenAPI
document and capture the HTTP submission, so no network or driver is
involved.
"""

from types import SimpleNamespace

import click
import pytest
from click.testing import CliRunner

from sparkmeter.metering import cli as metering_cli

# A minimal driver OpenAPI doc: two POST commands (one with a path param),
# one DELETE command, and a GET stream that must NOT become a command.
_FAKE_SPEC = {
    "paths": {
        "/v1/nodes/register": {
            "post": {
                "operationId": "registerNode",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["node_id", "node_type"],
                                "properties": {
                                    "node_id": {"type": "integer"},
                                    "node_type": {"type": "string"},
                                    "mac": {"type": "integer"},
                                },
                            }
                        }
                    }
                },
            }
        },
        "/v1/nodes/{node_id}/balance-and-flags": {
            "post": {
                "operationId": "setBalanceAndFlags",
                "parameters": [{"name": "node_id", "in": "path", "required": True}],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["balance", "low_balance_flag"],
                                "properties": {
                                    "balance": {"type": "number"},
                                    "low_balance_flag": {"type": "boolean"},
                                },
                            }
                        }
                    }
                },
            }
        },
        "/v1/nodes/{node_id}": {
            "delete": {
                "operationId": "unregisterNode",
                "parameters": [{"name": "node_id", "in": "path", "required": True}],
            }
        },
        "/v1/events": {"get": {"operationId": "subscribeEvents"}},
    }
}


@pytest.fixture
def submits(monkeypatch):
    captured: list = []

    def fake_submit(base_url, method, path, body):
        captured.append({"base_url": base_url, "method": method, "path": path, "body": body})

    monkeypatch.setattr(metering_cli, "_fetch_openapi", lambda base_url: _FAKE_SPEC)
    monkeypatch.setattr(metering_cli, "_submit", fake_submit)
    return captured


def _run(*args):
    return CliRunner().invoke(metering_cli.metering, list(args))


class TestDiscovery:
    def test_post_operation_is_a_command(self, submits):
        result = _run("--driver", "http://drv", "register-node", "--node-id", "1", "--node-type", "SM5R")
        assert result.exit_code == 0, result.output

    def test_get_operations_are_not_commands(self, submits):
        # GET /v1/events must not become a command.
        result = _run("--driver", "http://drv", "subscribe-events")
        assert result.exit_code != 0

    def test_command_absent_from_driver_is_unknown(self, submits):
        result = _run("--driver", "http://drv", "ping-meter", "--meter-id", "1")
        assert result.exit_code != 0

    def test_driver_help_lists_discovered_commands(self, submits):
        # With a driver selected, --help enumerates the discovered subcommands.
        result = _run("--driver", "http://drv", "--help")
        assert result.exit_code == 0, result.output
        assert "register-node" in result.output
        assert "unregister-node" in result.output


class TestRegisterNode:
    def test_body_assembled_from_options(self, submits):
        result = _run(
            "--driver",
            "http://drv",
            "register-node",
            "--node-id",
            "100",
            "--node-type",
            "SM5R",
            "--mac",
            "43981",
        )
        assert result.exit_code == 0, result.output
        assert len(submits) == 1
        call = submits[0]
        assert call["method"] == "post"
        assert call["path"] == "/v1/nodes/register"
        assert call["body"] == {"node_id": 100, "node_type": "SM5R", "mac": 43981}

    def test_required_option_missing_errors(self, submits):
        result = _run("--driver", "http://drv", "register-node", "--node-id", "100")
        assert result.exit_code != 0
        assert submits == []


class TestSetBalanceAndFlags:
    def test_path_param_substituted_and_body_built(self, submits):
        result = _run(
            "--driver",
            "http://drv",
            "set-balance-and-flags",
            "--node-id",
            "9",
            "--balance",
            "12.5",
            "--low-balance-flag",
        )
        assert result.exit_code == 0, result.output
        call = submits[0]
        assert call["method"] == "post"
        assert call["path"] == "/v1/nodes/9/balance-and-flags"
        assert call["body"] == {"balance": 12.5, "low_balance_flag": True}


class TestUnregisterNode:
    def test_delete_with_path_param_no_body(self, submits):
        result = _run("--driver", "http://drv", "unregister-node", "--node-id", "55")
        assert result.exit_code == 0, result.output
        call = submits[0]
        assert call["method"] == "delete"
        assert call["path"] == "/v1/nodes/55"
        assert call["body"] == {}


class TestNoDriver:
    def test_no_driver_lists_no_commands(self, submits):
        # Without --driver there is nothing to discover.
        result = _run("--help")
        assert result.exit_code == 0
        assert "register-node" not in result.output

    def test_subcommand_without_driver_is_unknown(self, submits):
        # get_command returns None when no spec is available.
        result = _run("register-node")
        assert result.exit_code != 0

    def test_fetch_failure_is_reported(self, monkeypatch):
        def boom(base_url):
            raise RuntimeError("connection refused")

        monkeypatch.setattr(metering_cli, "_fetch_openapi", boom)
        result = _run("--driver", "http://drv", "register-node")
        assert result.exit_code != 0
        assert "could not fetch" in result.output


# ---------------------------------------------------------------------------
# OpenAPI schema resolution helpers
# ---------------------------------------------------------------------------


class TestSchemaHelpers:
    def test_resolve_ref_walks_pointer(self):
        spec = {"components": {"schemas": {"Foo": {"type": "object"}}}}
        assert metering_cli._resolve_ref(spec, "#/components/schemas/Foo") == {"type": "object"}

    def test_resolve_schema_non_dict_returns_empty(self):
        assert metering_cli._resolve_schema({}, "not-a-dict") == {}

    def test_resolve_schema_follows_ref(self):
        spec = {"components": {"schemas": {"Foo": {"type": "string"}}}}
        assert metering_cli._resolve_schema(spec, {"$ref": "#/components/schemas/Foo"}) == {"type": "string"}

    def test_resolve_schema_merges_all_of(self):
        schema = {
            "allOf": [
                {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
                {"properties": {"b": {"type": "integer"}}},
            ],
            "properties": {"c": {"type": "string"}},
            "required": ["c"],
        }
        merged = metering_cli._resolve_schema({}, schema)
        assert set(merged["properties"]) == {"a", "b", "c"}
        assert set(merged["required"]) == {"a", "c"}

    def test_leaf_options_flattens_nested_objects(self):
        schema = {
            "type": "object",
            "required": ["configuration"],
            "properties": {
                "configuration": {
                    "type": "object",
                    "properties": {"power_limit": {"type": "number"}},
                }
            },
        }
        leaves = metering_cli._leaf_options({}, schema)
        assert [(path, required) for path, _prop, required in leaves] == [
            (("configuration", "power_limit"), False)
        ]

    def test_iter_command_operations_skips_non_dict_and_get(self):
        spec = {
            "paths": {
                "/x": "not-a-dict",
                "/y": {"get": {"operationId": "readY"}},
                "/z": {"post": {"operationId": "makeZ"}},
            }
        }
        names = [name for name, *_ in metering_cli._iter_command_operations(spec)]
        assert names == ["make-z"]

    def test_assemble_body_nests_dotted_paths(self):
        leaf_options = [(("configuration", "power_limit"), {}, False)]
        kwargs = {metering_cli._option_dest(("configuration", "power_limit")): 1500}
        assert metering_cli._assemble_body(leaf_options, kwargs) == {"configuration": {"power_limit": 1500}}


class TestClickKwargs:
    def test_enum_becomes_choice(self):
        kwargs = metering_cli._click_kwargs({"enum": ["on", "off"]}, required=True)
        assert isinstance(kwargs["type"], click.Choice)

    def test_integer_and_number_and_string(self):
        assert metering_cli._click_kwargs({"type": "integer"}, False)["type"] is click.INT
        assert metering_cli._click_kwargs({"type": "number"}, False)["type"] is click.FLOAT
        assert metering_cli._click_kwargs({"type": "string"}, False)["type"] is click.STRING

    def test_boolean_becomes_flag(self):
        kwargs = metering_cli._click_kwargs({"type": "boolean"}, False)
        assert kwargs["is_flag"] is True
        assert kwargs["default"] is False

    def test_array_is_multiple(self):
        kwargs = metering_cli._click_kwargs({"type": "array"}, False)
        assert kwargs["multiple"] is True
        assert kwargs["type"] is click.STRING


# ---------------------------------------------------------------------------
# Driver resolution + HTTP transport
# ---------------------------------------------------------------------------


class TestResolveDriverUrl:
    def test_url_passes_through(self):
        assert metering_cli._resolve_driver_url(None, "http://drv:18080/") == "http://drv:18080"

    def test_id_resolved_in_app_context(self, monkeypatch):
        monkeypatch.setattr("flask.has_app_context", lambda: True)
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.get_provider",
            lambda driver: {"base_url": "http://resolved:18080/"},
        )
        assert metering_cli._resolve_driver_url(None, "abc") == "http://resolved:18080"

    def test_unknown_id_raises(self, monkeypatch):
        monkeypatch.setattr("flask.has_app_context", lambda: True)
        monkeypatch.setattr("sparkmeter.config.provider_settings.get_provider", lambda driver: None)
        with pytest.raises(click.BadParameter):
            metering_cli._resolve_driver_url(None, "abc")

    def test_missing_base_url_raises(self, monkeypatch):
        monkeypatch.setattr("flask.has_app_context", lambda: True)
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.get_provider", lambda driver: {"base_url": ""}
        )
        with pytest.raises(click.BadParameter):
            metering_cli._resolve_driver_url(None, "abc")

    def test_no_context_and_no_app_raises(self, monkeypatch):
        monkeypatch.setattr("flask.has_app_context", lambda: False)
        ctx = SimpleNamespace(obj=None, parent=None)
        with pytest.raises(click.BadParameter):
            metering_cli._resolve_driver_url(ctx, "abc")

    def test_id_resolved_via_ctx_app_when_no_app_context(self, monkeypatch):
        import contextlib

        from flask.cli import ScriptInfo

        # No ambient app context: the driver id is resolved inside the app
        # loaded from the ScriptInfo on ctx.obj.
        monkeypatch.setattr("flask.has_app_context", lambda: False)
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.get_provider",
            lambda driver: {"base_url": "http://resolved:18080/"},
        )

        entered = []

        @contextlib.contextmanager
        def fake_app_context():
            entered.append(True)
            yield

        fake_app = SimpleNamespace(app_context=fake_app_context)
        script_info = ScriptInfo(create_app=lambda: fake_app, set_debug_flag=False)
        ctx = SimpleNamespace(obj=script_info, parent=None)

        assert metering_cli._resolve_driver_url(ctx, "abc") == "http://resolved:18080"
        assert entered == [True]  # the app context was actually entered


class TestFlaskAppFromCtx:
    def test_finds_scriptinfo_and_loads_app(self):
        from flask.cli import ScriptInfo

        fake_app = SimpleNamespace()
        script_info = ScriptInfo(create_app=lambda: fake_app, set_debug_flag=False)
        ctx = SimpleNamespace(obj=script_info, parent=None)
        assert metering_cli._flask_app_from_ctx(ctx) is fake_app

    def test_returns_none_when_no_scriptinfo(self):
        ctx = SimpleNamespace(obj="not-script-info", parent=SimpleNamespace(obj=None, parent=None))
        assert metering_cli._flask_app_from_ctx(ctx) is None

    def test_returns_none_when_flask_cli_unimportable(self, monkeypatch):
        import sys

        # A None entry in sys.modules makes `from flask.cli import ScriptInfo`
        # raise ImportError, exercising the import-guard fallback.
        monkeypatch.setitem(sys.modules, "flask.cli", None)
        ctx = SimpleNamespace(obj="anything", parent=None)
        assert metering_cli._flask_app_from_ctx(ctx) is None


class _FakeHttpxResponse:
    def __init__(self, status_code=200, text="", payload=None, is_error=False):
        self.status_code = status_code
        self.text = text
        self.is_error = is_error
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHttpxClient:
    def __init__(self, response, **kwargs):
        self._response = response
        self.kwargs = kwargs
        self.request_args = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, path):
        self.request_args = ("GET", path)
        return self._response

    def request(self, method, path, json=None):
        self.request_args = (method, path, json)
        return self._response


class TestTransport:
    def test_fetch_openapi_reads_document(self, monkeypatch):
        response = _FakeHttpxResponse(payload={"paths": {}})
        holder = {}

        def factory(**kwargs):
            holder["client"] = _FakeHttpxClient(response, **kwargs)
            return holder["client"]

        monkeypatch.setattr(metering_cli.httpx, "Client", factory)
        assert metering_cli._fetch_openapi("http://drv") == {"paths": {}}
        # It fetches the OpenAPI document from the spec endpoint, not some other path.
        assert holder["client"].request_args == ("GET", "/openapi.json")

    def test_submit_echoes_status_and_body(self, monkeypatch, capsys):
        response = _FakeHttpxResponse(status_code=200, text="created", is_error=False)
        holder = {}

        def factory(**kwargs):
            holder["client"] = _FakeHttpxClient(response, **kwargs)
            return holder["client"]

        monkeypatch.setattr(metering_cli.httpx, "Client", factory)
        metering_cli._submit("http://drv", "post", "/v1/x", {"a": 1})
        out = capsys.readouterr().out
        assert "POST /v1/x -> 200" in out
        assert "created" in out
        # The method is upper-cased and the body is sent as JSON.
        assert holder["client"].request_args == ("POST", "/v1/x", {"a": 1})

    def test_submit_raises_on_error_status(self, monkeypatch):
        response = _FakeHttpxResponse(status_code=500, text="", is_error=True)
        holder = {}

        def factory(**kwargs):
            holder["client"] = _FakeHttpxClient(response, **kwargs)
            return holder["client"]

        monkeypatch.setattr(metering_cli.httpx, "Client", factory)
        with pytest.raises(SystemExit):
            metering_cli._submit("http://drv", "post", "/v1/x", {})
        # An empty body is sent as json=None, and the request still went out.
        assert holder["client"].request_args == ("POST", "/v1/x", None)
