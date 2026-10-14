# -*- coding: utf-8 -*-
"""Tests for the Prometheus metrics wiring (sparkmeter/metrics.py)."""

import asyncio
import gzip
from types import SimpleNamespace

import pytest
from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient
from flask import Flask, request_started
from prometheus_client import REGISTRY
from sqlalchemy import create_engine, text

from sparkmeter import asgi, metrics
from sparkmeter.metering import runtime_registry


def _sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def _requests(method, route, status):
    return _sample("http_requests_total", method=method, route=route, status=str(status))


@pytest.fixture()
def instrumented_client():
    """A public-app lookalike: FastAPI routes, the middleware, and Flask mounted under "/"."""
    flask_app = Flask(__name__)

    @flask_app.route("/_metrics_test/flask/<int:item_id>")
    def flask_item(item_id):
        return "item %d" % item_id

    request_started.connect(metrics._record_flask_rule, flask_app)

    api = FastAPI()
    api.add_middleware(metrics.HTTPMetricsMiddleware)

    @api.get("/_metrics_test/native/{item_id}")
    async def native_item(item_id: int):
        return {"item": item_id}

    @api.get("/_metrics_test/boom")
    async def boom():
        raise RuntimeError("boom")

    api.mount("/", WSGIMiddleware(flask_app))
    try:
        yield TestClient(api, raise_server_exceptions=False)
    finally:
        request_started.disconnect(metrics._record_flask_rule, flask_app)


class TestHTTPMetricsMiddleware:
    def test_native_route_is_labeled_with_its_template(self, instrumented_client):
        route = "/_metrics_test/native/{item_id}"
        before = _requests("GET", route, 200)

        assert instrumented_client.get("/_metrics_test/native/7").status_code == 200
        assert instrumented_client.get("/_metrics_test/native/8").status_code == 200

        # Two different paths, one series: the template, not the raw path.
        assert _requests("GET", route, 200) - before == 2
        assert _sample("http_request_duration_seconds_count", method="GET", route=route) >= 2

    def test_flask_route_is_labeled_with_its_url_rule(self, instrumented_client):
        route = "/_metrics_test/flask/<int:item_id>"
        before = _requests("GET", route, 200)

        response = instrumented_client.get("/_metrics_test/flask/42")

        assert response.text == "item 42"
        assert _requests("GET", route, 200) - before == 1

    def test_unmatched_path_is_collapsed(self, instrumented_client):
        before = _requests("GET", metrics.UNMATCHED_ROUTE, 404)

        assert instrumented_client.get("/_metrics_test/no/such/thing").status_code == 404

        assert _requests("GET", metrics.UNMATCHED_ROUTE, 404) - before == 1

    def test_unhandled_exception_counts_as_500(self, instrumented_client):
        route = "/_metrics_test/boom"
        before = _requests("GET", route, 500)

        assert instrumented_client.get(route).status_code == 500

        assert _requests("GET", route, 500) - before == 1
        assert _sample("http_requests_in_progress") == 0

    def test_unexpected_method_is_bucketed(self, instrumented_client):
        before = _requests("OTHER", metrics.UNMATCHED_ROUTE, 405)

        instrumented_client.request("PROPFIND", "/_metrics_test/flask/1")

        assert _requests("OTHER", metrics.UNMATCHED_ROUTE, 405) - before == 1


class TestScrapeEndpoint:
    @pytest.fixture()
    def internal_client(self):
        public = SimpleNamespace(state=SimpleNamespace(metering=None))
        return TestClient(asgi.create_internal_app(public))

    def test_serves_prometheus_text_without_redirect(self, internal_client):
        response = internal_client.get("/metrics", follow_redirects=False)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "# TYPE http_requests_total counter" in response.text
        assert "thundercloud_metering_runtime_active" in response.text
        # The client's process collector rides along in the default registry.
        assert "process_resident_memory_bytes" in response.text
        assert "_created" not in response.text

    def test_negotiates_openmetrics(self, internal_client):
        response = internal_client.get("/metrics", headers={"Accept": "application/openmetrics-text"})

        assert response.headers["content-type"].startswith("application/openmetrics-text")
        assert response.text.rstrip().endswith("# EOF")

    def test_gzips_when_accepted(self):
        body, headers = metrics.render("", "gzip")

        assert headers["Content-Encoding"] == "gzip"
        assert b"http_requests_total" in gzip.decompress(body)


class TestMeteringStateCollector:
    def _collect(self):
        return {
            sample.name: sample.value
            for family in metrics._MeteringStateCollector().collect()
            for sample in family.samples
        }

    def _with_running_app(self, state):
        saved = runtime_registry.get_running_app()
        runtime_registry.set_running_app(SimpleNamespace(state=state))
        return saved

    def test_inactive_runtime_reports_only_the_active_flag(self):
        saved = self._with_running_app(SimpleNamespace(metering=None))
        try:
            assert self._collect() == {"thundercloud_metering_runtime_active": 0}
        finally:
            runtime_registry.set_running_app(saved)

    def test_active_runtime_reports_gateway_and_queue(self):
        queue = asyncio.Queue()
        queue.put_nowait({"op": "set_balance"})
        queue.put_nowait({"op": "set_balance"})
        state = SimpleNamespace(
            metering=object(),
            metering_gateway_state={"gateway_connected": False, "gateway_paused": True},
            metering_command_queue=queue,
        )
        saved = self._with_running_app(state)
        try:
            assert self._collect() == {
                "thundercloud_metering_runtime_active": 1,
                "thundercloud_metering_gateway_connected": 0,
                "thundercloud_metering_commands_paused": 1,
                "thundercloud_metering_command_queue_depth": 2,
            }
        finally:
            runtime_registry.set_running_app(saved)

    def test_gateway_state_is_omitted_until_the_driver_reports_it(self):
        state = SimpleNamespace(
            metering=object(),
            metering_gateway_state={"gateway_connected": None, "gateway_paused": False},
            metering_command_queue=None,
        )
        saved = self._with_running_app(state)
        try:
            assert "thundercloud_metering_gateway_connected" not in self._collect()
        finally:
            runtime_registry.set_running_app(saved)


class TestDatabaseMetrics:
    def test_pool_collector_reports_occupancy(self):
        collector = metrics._DatabasePoolCollector()
        assert list(collector.collect()) == []

        # Creating the engine opens no connection, so the pool is empty.
        collector.engine = create_engine("postgresql://u:p@127.0.0.1:1/db", pool_size=3)
        samples = {
            (sample.name, sample.labels.get("state")): sample.value
            for family in collector.collect()
            for sample in family.samples
        }

        assert samples == {
            ("thundercloud_db_pool_connections", "checked_out"): 0,
            ("thundercloud_db_pool_connections", "idle"): 0,
            ("thundercloud_db_pool_size", None): 3,
        }

    @pytest.mark.parametrize(
        "statement,expected",
        [
            ("SELECT 1", "select"),
            ("\n  insert into reading values (1)", "insert"),
            ("(SELECT a FROM b) UNION (SELECT c FROM d)", "select"),
            ("UPDATE meter SET x = 1", "update"),
            ("DELETE FROM meter", "delete"),
            ("WITH x AS (SELECT 1) SELECT * FROM x", "other"),
            ("", "other"),
        ],
    )
    def test_statement_type(self, statement, expected):
        assert metrics._statement_type(statement) == expected

    def test_query_duration_is_observed(self, session):
        before = _sample("thundercloud_db_query_duration_seconds_count", statement="select")

        session.execute(text("SELECT 1"))

        assert _sample("thundercloud_db_query_duration_seconds_count", statement="select") - before == 1


def test_instrument_flask_app_sets_build_info_and_tracks_the_engine(app):
    saved_engine = metrics._DB_POOL_COLLECTOR.engine
    try:
        metrics.instrument_flask_app(app)

        with app.app_context():
            assert metrics._DB_POOL_COLLECTOR.engine is app.sql.engine
        from sparkmeter import __version__
        from sparkmeter.config.configdict import config

        build = dict(
            version=__version__.version, revision=__version__.git_version, system=config.local_system
        )
        assert _sample("thundercloud_build_info", **build) == 1
    finally:
        request_started.disconnect(metrics._record_flask_rule, app)
        metrics._DB_POOL_COLLECTOR.engine = saved_engine
