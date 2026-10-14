# -*- coding: utf-8 -*-
"""Tests for log rendering (misc/logutils.py) and the access log (accesslog.py)."""

import asyncio
import io
import json
import logging

import pytest
import structlog
from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient
from flask import Flask
from structlog.contextvars import bound_contextvars

from sparkmeter import periodic
from sparkmeter.accesslog import AccessLogMiddleware
from sparkmeter.misc import logutils


@pytest.fixture()
def capture():
    """Attach a handler rendering `fmt` to a private logger; return (logger, read)."""
    handlers = []

    def _capture(fmt, name="test.logging"):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logutils._formatter(fmt, stream))
        logger = logging.getLogger(name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        handlers.append((logger, handler))
        return logger, lambda: stream.getvalue().splitlines()

    yield _capture
    for logger, handler in handlers:
        logger.removeHandler(handler)
        logger.propagate = True


def _logfmt(line):
    """Parse a logfmt line produced by structlog's LogfmtRenderer."""
    fields, i = {}, 0
    while i < len(line):
        eq = line.index("=", i)
        key = line[i:eq]
        i = eq + 1
        if i < len(line) and line[i] == '"':
            j, value = i + 1, []
            while line[j] != '"':
                if line[j] == "\\":
                    j += 1
                    value.append({"n": "\n"}.get(line[j], line[j]))
                else:
                    value.append(line[j])
                j += 1
            fields[key], i = "".join(value), j + 2
        else:
            end = line.find(" ", i)
            end = len(line) if end == -1 else end
            fields[key], i = line[i:end], end + 1
    return fields


class TestRendering:
    def test_logfmt_line_has_standard_keys_first(self, capture):
        logger, read = capture("logfmt")

        logger.info("registered=%d responded=%d", 12, 9)

        (line,) = read()
        assert line.startswith("time=")
        assert list(_logfmt(line))[:4] == ["time", "level", "logger", "msg"]
        fields = _logfmt(line)
        assert fields["level"] == "info"
        assert fields["logger"] == "test.logging"
        assert fields["msg"] == "registered=12 responded=9"
        assert fields["time"].endswith("Z")

    def test_logfmt_keeps_a_traceback_on_one_line(self, capture):
        logger, read = capture("logfmt")

        try:
            1 / 0
        except ZeroDivisionError:
            logger.exception("reading flush failed (batch size=%d)", 50)

        (line,) = read()
        fields = _logfmt(line)
        assert fields["level"] == "error"
        assert fields["exception"].startswith("Traceback (most recent call last):")
        assert "ZeroDivisionError: division by zero" in fields["exception"]

    def test_json_has_the_same_keys(self, capture):
        logger, read = capture("json")

        with bound_contextvars(request_id="abc123"):
            logger.warning("gateway %s", "down", extra={"site": "s1"})

        record = json.loads(read()[0])
        assert list(record)[:4] == ["time", "level", "logger", "msg"]
        assert record["msg"] == "gateway down"
        assert record["level"] == "warning"
        assert record["request_id"] == "abc123"
        assert record["site"] == "s1"

    def test_text_is_human_oriented(self, capture):
        logger, read = capture("text")

        logger.info("Creating an empty schema", extra={"tables": 3})

        (line,) = read()
        assert "Creating an empty schema" in line
        assert "test.logging" in line
        assert "tables=3" in line

    def test_structlog_loggers_render_through_the_same_handler(self, capture):
        _, read = capture("logfmt", name="test.logging.native")

        structlog.stdlib.get_logger("test.logging.native").info("flushed", batch=50, node_id=7)

        fields = _logfmt(read()[0])
        assert fields["msg"] == "flushed"
        assert fields["logger"] == "test.logging.native"
        assert fields["batch"] == "50"
        assert fields["node_id"] == "7"


class TestSetupLogging:
    @pytest.mark.parametrize(
        "level,expected",
        [
            (10, 10),
            ("10", 10),
            ("debug", 10),
            (" WARNING ", 30),
            ("bogus", logging.INFO),
            (None, logging.INFO),
        ],
    )
    def test_coerce_level(self, level, expected):
        assert logutils._coerce_level(level)[0] == expected

    def test_applies_level_and_falls_back_on_bad_values(self, caplog):
        root = logging.getLogger()
        saved_level, saved_formatter = root.level, logutils._handler.formatter
        try:
            logutils.setup_logging(level="DEBUG", fmt="logfmt")
            assert root.level == logging.DEBUG

            with caplog.at_level(logging.WARNING, logger=logutils.__name__):
                logutils.setup_logging(level="loud", fmt="xml")
            assert root.level == logging.INFO
            messages = [rec.getMessage() for rec in caplog.records]
            assert any("unrecognized LOG_LEVEL 'loud'" in m for m in messages)
            assert any("unrecognized LOG_FORMAT 'xml'" in m for m in messages)
        finally:
            root.setLevel(saved_level)
            logutils._handler.setFormatter(saved_formatter)

    def test_one_managed_root_handler(self):
        root = logging.getLogger()
        before = list(root.handlers)

        logutils.setup_logging()
        logutils.setup_logging()

        assert root.handlers.count(logutils._handler) == 1
        assert len(root.handlers) == len(before)


def _access_records(caplog):
    return [rec.msg for rec in caplog.records if rec.name == "sparkmeter.access"]


class TestAccessLog:
    @pytest.fixture()
    def client(self):
        flask_app = Flask(__name__)
        view_logger = logging.getLogger("test.logging.view")

        @flask_app.route("/_accesslog_test/flask")
        def flask_view():
            view_logger.info("inside the view")
            return "ok"

        api = FastAPI()

        @api.get("/_accesslog_test/health")
        async def health():
            return {"status": "ok"}

        @api.get("/_accesslog_test/boom")
        async def boom():
            raise RuntimeError("boom")

        api.mount("/", WSGIMiddleware(flask_app))
        api.add_middleware(AccessLogMiddleware, listener="public", quiet_paths={"/_accesslog_test/health"})
        return TestClient(api, raise_server_exceptions=False)

    def test_writes_structured_line_and_echoes_request_id(self, client, caplog):
        with caplog.at_level(logging.DEBUG, logger="sparkmeter.access"):
            response = client.get("/_accesslog_test/flask?token=secret", headers={"User-Agent": "probe/1"})

        (entry,) = _access_records(caplog)
        assert entry["event"] == "GET /_accesslog_test/flask 200"
        assert entry["level"] == "info"
        assert entry["route"] == "unmatched"  # no Flask rule capture installed on this test app
        assert entry["status"] == 200
        assert entry["bytes"] == 2
        assert entry["user_agent"] == "probe/1"
        assert entry["listener"] == "public"
        assert entry["duration_ms"] >= 0
        # The query string is never logged.
        assert "secret" not in repr(entry)
        assert entry["request_id"] == response.headers["x-request-id"]
        assert len(entry["request_id"]) == 32

    def test_honors_a_well_formed_caller_request_id(self, client, caplog):
        with caplog.at_level(logging.INFO, logger="sparkmeter.access"):
            response = client.get("/_accesslog_test/flask", headers={"X-Request-ID": "edge-7f3a.1"})

        assert response.headers["x-request-id"] == "edge-7f3a.1"
        assert _access_records(caplog)[0]["request_id"] == "edge-7f3a.1"

    def test_replaces_a_malformed_caller_request_id(self, client):
        response = client.get(
            "/_accesslog_test/flask", headers={"X-Request-ID": 'x" level=error msg="forged'}
        )

        assert len(response.headers["x-request-id"]) == 32

    def test_request_id_reaches_flask_view_logs(self, client, capture):
        _, read = capture("logfmt", name="test.logging.view")

        response = client.get("/_accesslog_test/flask")

        fields = _logfmt(read()[0])
        assert fields["msg"] == "inside the view"
        assert fields["request_id"] == response.headers["x-request-id"]

    def test_quiet_path_logs_at_debug(self, client, caplog):
        with caplog.at_level(logging.DEBUG, logger="sparkmeter.access"):
            client.get("/_accesslog_test/health")

        assert _access_records(caplog)[0]["level"] == "debug"

    def test_unhandled_exception_is_logged_as_500(self, client, caplog):
        with caplog.at_level(logging.INFO, logger="sparkmeter.access"):
            assert client.get("/_accesslog_test/boom").status_code == 500

        (entry,) = _access_records(caplog)
        assert entry["status"] == 500
        assert entry["route"] == "/_accesslog_test/boom"


def test_periodic_task_logs_carry_the_task_name(app, capture):
    _, read = capture("logfmt", name="test.logging.task")

    def _logging_task():
        logging.getLogger("test.logging.task").info("processing")

    asyncio.run(periodic._run_blocking(_logging_task, app))

    assert _logfmt(read()[0])["task"] == "_logging_task"
