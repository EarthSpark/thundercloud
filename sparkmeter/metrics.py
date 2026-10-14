"""
Prometheus metrics.

Everything here registers in prometheus_client's default registry, which
also carries the client's own process (`process_*`) and runtime
(`python_*`) collectors. The webapp is a single Hypercorn process with no
worker processes, so the in-process registry is complete and the client's
multiprocess mode is not needed.

The scrape endpoint is `GET /metrics` on the internal listener (port 5001,
see `asgi.create_internal_app`). It is never served on the public listener.

HTTP metrics come from `HTTPMetricsMiddleware` on the public app. Its
`route` label is the matched route template, never the raw path, so
cardinality stays bounded:

- native FastAPI routes: the route path, e.g. `/health`;
- the WSGI-mounted Flask app: the matched URL rule, e.g.
  `/microgrid/<ground_serial>/<int:meter_code>/`. A `request_started`
  receiver (`instrument_flask_app`) writes it back into the ASGI scope,
  which a2wsgi exposes as `environ["asgi.scope"]`;
- anything that matched no route (404s, scanners): `unmatched`.

Domain metrics are prefixed `thundercloud_`. Label values come from fixed
sets (task names, command ops, event types, results); nothing is labeled by
meter, customer or user. No metric uses the `job` or `instance` label names,
which Prometheus reserves for the scrape target.
"""

import gzip
import time

from prometheus_client import REGISTRY, Counter, Gauge, Histogram, Info, disable_created_metrics
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.exposition import choose_encoder, gzip_accepted
from prometheus_client.registry import Collector
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Drop the `<name>_created` sample the client otherwise exports beside every
# counter and histogram series; it doubles the series count.
disable_created_metrics()

# Scope key the Flask request hook stores the matched URL rule under.
FLASK_RULE_SCOPE_KEY = "thundercloud.flask_rule"

UNMATCHED_ROUTE = "unmatched"

_HTTP_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})

# ----------------------------------------------------------------------
# HTTP (public listener)
# ----------------------------------------------------------------------

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests served on the public listener.",
    ["method", "route", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Time to serve an HTTP request on the public listener, including the response body.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being served on the public listener.",
)

# ----------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------

BUILD_INFO = Info(
    "thundercloud_build",
    "Running build: package version, git revision and system (ground or cloud).",
)

# ----------------------------------------------------------------------
# Periodic tasks (sparkmeter/periodic.py)
#
# Labeled `task`, not `job`: Prometheus attaches its own `job` label (the
# scrape job) and renames a scraped `job` label to `exported_job`.
# ----------------------------------------------------------------------

TASK_RUNS = Counter(
    "thundercloud_task_runs_total",
    "Periodic task runs, by task and result (success or error).",
    ["task", "result"],
)
TASK_DURATION = Histogram(
    "thundercloud_task_duration_seconds",
    "Periodic task run time.",
    ["task"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600, 1800),
)
TASK_LAST_SUCCESS = Gauge(
    "thundercloud_task_last_success_timestamp_seconds",
    "Unix time the task last completed without raising.",
    ["task"],
)

# ----------------------------------------------------------------------
# Metering runtime (ground only; sparkmeter/metering/)
# ----------------------------------------------------------------------

METERING_EVENTS = Counter(
    "thundercloud_metering_events_total",
    "Events received from the meter driver, by envelope type ('unknown' for unrecognized types).",
    ["type"],
)
METERING_LAST_EVENT = Gauge(
    "thundercloud_metering_last_event_timestamp_seconds",
    "Unix time the last meter-driver event was received; 0 if none yet.",
)
METERING_STREAM_RECONNECTS = Counter(
    "thundercloud_metering_stream_reconnects_total",
    "Times the meter-driver event stream ended or broke and was reconnected.",
)
METERING_NODES = Gauge(
    "thundercloud_metering_nodes",
    "Node counts from the meter driver's latest heartbeat summary "
    "(registered, attempted, responded in the current heartbeat).",
    ["state"],
)
METERING_COMMANDS = Counter(
    "thundercloud_metering_commands_total",
    "Commands sent through the dispatcher queue to the meter driver, by op and result "
    "(ok, error, dropped). Reconcile traffic is counted separately.",
    ["op", "result"],
)
METERING_COMMAND_DURATION = Histogram(
    "thundercloud_metering_command_duration_seconds",
    "Time for the meter driver to accept a command sent through the dispatcher queue.",
    ["op"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)
METERING_RECONCILES = Counter(
    "thundercloud_metering_reconciles_total",
    "Full driver reconciles (init, then register, configure and balance every meter), by result (ok, error). "
    "They run at startup, after a driver restart and after gateway recovery.",
    ["result"],
)
METERING_RECONCILE_DURATION = Histogram(
    "thundercloud_metering_reconcile_duration_seconds",
    "Time to complete a full driver reconcile.",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600),
)
METERING_RECONCILE_METER_FAILURES = Counter(
    "thundercloud_metering_reconcile_meter_failures_total",
    "Meters a reconcile failed to register, configure or set the balance of.",
)

READINGS = Counter(
    "thundercloud_readings_total",
    "Meter readings received from the meter driver, by write result "
    "(written, duplicate, lock_timeout, incomplete, error).",
    ["result"],
)
for _result in ("written", "duplicate", "lock_timeout", "incomplete", "error"):
    READINGS.labels(_result)

READING_INGEST_LAG = Histogram(
    "thundercloud_reading_ingest_lag_seconds",
    "Time from a reading's heartbeat end to its write to the database.",
    buckets=(0.25, 0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 21600, 86400),
)

# ----------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------

DB_QUERY_DURATION = Histogram(
    "thundercloud_db_query_duration_seconds",
    "SQL statement execution time, by statement type (select, insert, update, delete, other).",
    ["statement"],
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

_STATEMENT_TYPES = frozenset({"select", "insert", "update", "delete"})

# Attribute the query timer keeps its start time under on the execution context.
_QUERY_START_ATTR = "_thundercloud_query_start"


def _statement_type(statement):
    head = statement.lstrip(" \t\r\n(").split(None, 1)
    word = head[0].lower() if head else ""
    return word if word in _STATEMENT_TYPES else "other"


@event.listens_for(Engine, "before_cursor_execute")
def _query_started(conn, cursor, statement, parameters, context, executemany):
    if context is not None:
        setattr(context, _QUERY_START_ATTR, time.perf_counter())


@event.listens_for(Engine, "after_cursor_execute")
def _query_finished(conn, cursor, statement, parameters, context, executemany):
    started = getattr(context, _QUERY_START_ATTR, None)
    if started is not None:
        DB_QUERY_DURATION.labels(_statement_type(statement)).observe(time.perf_counter() - started)


class _DatabasePoolCollector(Collector):
    """Connection-pool occupancy of the webapp's SQLAlchemy engine, read at scrape time."""

    def __init__(self):
        self.engine = None

    def collect(self):
        pool = getattr(self.engine, "pool", None)
        if pool is None or not hasattr(pool, "checkedout"):
            return
        connections = GaugeMetricFamily(
            "thundercloud_db_pool_connections",
            "Connections held by the SQLAlchemy pool, by state (checked_out or idle).",
            labels=["state"],
        )
        connections.add_metric(["checked_out"], pool.checkedout())
        connections.add_metric(["idle"], pool.checkedin())
        yield connections
        yield GaugeMetricFamily(
            "thundercloud_db_pool_size",
            "Configured size of the SQLAlchemy pool, excluding overflow connections.",
            value=pool.size(),
        )


class _MeteringStateCollector(Collector):
    """Live metering-runtime state, read from the running public app at scrape time."""

    def collect(self):
        from sparkmeter.metering.runtime_registry import get_running_app

        state = getattr(get_running_app(), "state", None)
        active = getattr(state, "metering", None) is not None
        yield GaugeMetricFamily(
            "thundercloud_metering_runtime_active",
            "1 while this process runs the meter-driver runtime (ground with a driver configured).",
            value=int(active),
        )
        if not active:
            return

        gateway = getattr(state, "metering_gateway_state", None) or {}
        connected = gateway.get("gateway_connected")
        # Unknown until the driver's first gateway_status event; omitted rather than reported as 0.
        if connected is not None:
            yield GaugeMetricFamily(
                "thundercloud_metering_gateway_connected",
                "1 when the meter driver last reported its gateway connected, 0 when disconnected.",
                value=int(bool(connected)),
            )
        yield GaugeMetricFamily(
            "thundercloud_metering_commands_paused",
            "1 while commands are held for gateway recovery.",
            value=int(bool(gateway.get("gateway_paused"))),
        )
        queue = getattr(state, "metering_command_queue", None)
        if queue is not None:
            yield GaugeMetricFamily(
                "thundercloud_metering_command_queue_depth",
                "Commands waiting for the dispatcher.",
                value=queue.qsize(),
            )


_DB_POOL_COLLECTOR = _DatabasePoolCollector()
REGISTRY.register(_DB_POOL_COLLECTOR)
REGISTRY.register(_MeteringStateCollector())


# ----------------------------------------------------------------------
# Wiring
# ----------------------------------------------------------------------


def _record_flask_rule(sender, **extra):
    """Flask `request_started` receiver: store the matched URL rule in the ASGI scope."""
    from flask import request

    rule = request.url_rule
    scope = request.environ.get("asgi.scope")
    if rule is not None and scope is not None:
        scope[FLASK_RULE_SCOPE_KEY] = rule.rule


def instrument_flask_app(flask_app):
    """Wire a bootstrapped Flask app into the metrics: route labels, DB pool and build info."""
    from flask import request_started

    from sparkmeter import __version__
    from sparkmeter.config.configdict import config

    request_started.connect(_record_flask_rule, flask_app)
    with flask_app.app_context():
        _DB_POOL_COLLECTOR.engine = flask_app.sql.engine
    BUILD_INFO.info(
        {
            "version": __version__.version,
            "revision": __version__.git_version,
            "system": config.local_system,
        }
    )


def route_template(scope):
    """The matched route template for a request scope, or "unmatched"."""
    flask_rule = scope.get(FLASK_RULE_SCOPE_KEY)
    if flask_rule:
        return flask_rule
    path = getattr(scope.get("route"), "path", None)
    return path or UNMATCHED_ROUTE


class HTTPMetricsMiddleware:
    """Pure ASGI middleware recording request count, duration and in-flight requests.

    Added with `app.add_middleware`, so it sits inside Starlette's
    ServerErrorMiddleware: an exception escaping the app is recorded as the
    500 that ServerErrorMiddleware then sends.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"] if scope["method"] in _HTTP_METHODS else "OTHER"
        status = 500

        async def send_with_status(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        HTTP_REQUESTS_IN_PROGRESS.inc()
        started = time.perf_counter()
        try:
            await self.app(scope, receive, send_with_status)
        finally:
            HTTP_REQUESTS_IN_PROGRESS.dec()
            route = route_template(scope)
            HTTP_REQUEST_DURATION.labels(method, route).observe(time.perf_counter() - started)
            HTTP_REQUESTS.labels(method, route, str(status)).inc()


def render(accept, accept_encoding):
    """Render the default registry for a scrape.

    Returns `(body, headers)`. Negotiates the Prometheus text or OpenMetrics
    format from `Accept` and gzips when `Accept-Encoding` allows it.
    """
    encoder, content_type = choose_encoder(accept)
    body = encoder(REGISTRY)
    headers = {"Content-Type": content_type}
    if gzip_accepted(accept_encoding):
        body = gzip.compress(body)
        headers["Content-Encoding"] = "gzip"
    return body, headers
