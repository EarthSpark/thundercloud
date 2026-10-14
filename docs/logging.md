# Logging

ThunderCloud writes one log line per event to **stderr**. stdout is left to
the output of CLI commands, so they can still be piped. Everything goes
through the same formatter: the application, libraries, the web server and
the HTTP access log. It renders in one of three formats.

## Settings

| Environment variable | Values | Default |
|---|---|---|
| `SM_LOG_FORMAT` | `text`, `logfmt` or `json` | `text` |
| `SM_LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, or a number | `INFO` |

An unrecognized value falls back to the default, with a warning in the log.
Both can also be set as `LOG_FORMAT` and `LOG_LEVEL` in a settings file.

- **`text`** is for people reading the log directly, as with
  `docker compose logs`. Tracebacks print on the lines that follow.
- **`logfmt`** is for Loki and other aggregators that parse `key=value`
  lines. Each event is exactly one line, tracebacks included, and the line
  is still readable as plain text.
- **`json`** is for Elasticsearch and other aggregators that ingest JSON. Each
  event is one JSON object per line.

The same request in each format:

```
2026-10-13T22:05:31.497104Z [info     ] GET /login 200                 [sparkmeter.access] bytes=6958 client=172.23.0.1 duration_ms=146.8 listener=public method=GET path=/login request_id=c9d24dc4bf2d4a75b47dffa97e699595 route=/login status=200 user_agent=curl/8.7.1
```
```
time=2026-10-13T22:04:53.497374Z level=info logger=sparkmeter.access msg="GET /login 200" method=GET path=/login route=/login status=200 duration_ms=104.1 bytes=6958 client=172.23.0.1 user_agent=curl/8.7.1 listener=public request_id=probe-123
```
```json
{"time": "2026-10-13T22:05:46.631761Z", "level": "info", "logger": "sparkmeter.access", "msg": "GET /login 200", "method": "GET", "path": "/login", "route": "/login", "status": 200, "duration_ms": 190.6, "bytes": 6958, "client": "172.23.0.1", "user_agent": "curl/8.7.1", "listener": "public", "request_id": "65a72fd99dd947af89cf31a04734952c"}
```

## Fields

logfmt and JSON use the same keys, so switching formats doesn't change
any queries.

| Key | On | Meaning |
|---|---|---|
| `time` | every line | ISO 8601 timestamp, UTC. |
| `level` | every line | `debug`, `info`, `warning`, `error` or `critical`. |
| `logger` | every line | The Python logger, usually the module, such as `sparkmeter.metering.reconcile`. |
| `msg` | every line | The message. |
| `exception` | errors with a traceback | The full traceback, in one field. |
| `request_id` | lines logged while serving an HTTP request | See [Request ids](#request-ids). |
| `task` | lines logged by a periodic task | `process_events`, `process_transactions` or `nightly_dashboard_tariff_summary`. |

Access-log lines (`logger=sparkmeter.access`) add these keys:

| Key | Meaning |
|---|---|
| `method`, `path` | The request. The query string is never logged, because it can carry credentials. |
| `route` | The matched route template, such as `/microgrid/<ground_serial>/<int:meter_code>/`, or `unmatched`. |
| `status` | The response status code. |
| `duration_ms` | Time to serve the request, including the response body. |
| `bytes` | Response body bytes sent. |
| `client`, `user_agent` | The peer address and its `User-Agent`. |
| `listener` | `public` (port 5000) or `internal` (port 5001). |

Successful health probes (`/health`) and metrics scrapes (`/metrics`) are
logged at `debug`, so they don't flood the log at the default level.

## Request ids

Every HTTP request gets a `request_id`. It is attached to every line logged
while serving that request, including lines from the web UI's views, and
returned in the response's `X-Request-ID` header. If the request arrives
with an `X-Request-ID` header, that value is used instead, so an id set by a
proxy or load balancer carries through. A supplied id is accepted only if it
is 1 to 128 letters, digits or `.`, `_`, `:`, `-`. Anything else is replaced
with a new id.

## Loki

Use `SM_LOG_FORMAT=logfmt`. Keep stream labels coarse, such as the
container, service or site, and parse fields at query time:

```logql
{service="thundercloud"} | logfmt | level="error"
{service="thundercloud"} | logfmt | logger="sparkmeter.access" | status >= 500
{service="thundercloud"} | logfmt | request_id="c9d24dc4bf2d4a75b47dffa97e699595"
{service="thundercloud"} | logfmt | task="process_events" | level=~"warning|error"
```

Don't promote `request_id`, `route` or `path` to labels. Their values are
unbounded.

## Elasticsearch

Use `SM_LOG_FORMAT=json` and decode each line as JSON in your shipper
(Filebeat, Elastic Agent, Fluent Bit and so on). To index on the event's own
time rather than the time it was shipped, set `@timestamp` from `time`, for
example with an ingest pipeline:

```json
PUT _ingest/pipeline/thundercloud
{
  "processors": [
    { "date": { "field": "time", "formats": ["ISO8601"] } }
  ]
}
```

## Logging from code

Existing code logs through the standard library, and that keeps working
unchanged:

```python
logger = logging.getLogger(__name__)
logger.info("metering reconcile: registering %d meters", len(meters))
```

Values passed with `extra=` become fields of their own. New code can also use
structlog directly to log key/value pairs, which go through the same
formatter:

```python
log = structlog.stdlib.get_logger(__name__)
log.info("reading batch flushed", batch_size=50, duration_ms=12.5)
```

To attach a field to everything logged within a block, as the access log
does with `request_id`, bind it with
`structlog.contextvars.bound_contextvars(name=value)`.
