# Metrics

ThunderCloud exposes [Prometheus](https://prometheus.io) metrics for the web
server, the periodic tasks, the meter-driver runtime and the database
connection pool. This page covers how to scrape them, what each metric means
and how to start graphing and alerting with Grafana.

## Where the metrics are served

The webapp process runs two HTTP listeners:

| Listener | Default bind | Serves |
|---|---|---|
| Public | `0.0.0.0:5000` (`PUBLIC_BIND`) | The web UI and APIs |
| Internal | `0.0.0.0:5001` (`INTERNAL_BIND`) | Admin endpoints and **`GET /metrics`** |

Metrics are served only on the internal listener, so users of a public
instance can't read them. The internal listener has **no authentication**:
it is protected only by not being reachable from untrusted networks. Expose
port 5001 to your Prometheus server and nothing else. Never publish it on a
public interface or route it through a public load balancer.

The endpoint returns the Prometheus text format, or OpenMetrics when the
scraper asks for it, gzipped when the scraper accepts gzip. Scrapes are left
out of the internal listener's access log.

```bash
docker compose exec ground curl -s localhost:5001/metrics | head
```

## Scraping

The webapp runs as a single process, so one scrape target per container or
pod covers everything.

### Prometheus alongside Docker Compose

Port 5001 is not published by default. Run Prometheus on the same Compose
network and scrape the service by name:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: thundercloud
    scrape_interval: 30s
    static_configs:
      - targets: ["ground:5001"]
        labels:
          site: my-site
```

If Prometheus runs elsewhere, publish the port only on a private interface,
for example `"10.0.0.5:5001:5001"`, never `"5001:5001"`.

### Kubernetes

Name the container port and select it with a `PodMonitor` (Prometheus
Operator), or with a `ServiceMonitor` on a Service that is not exposed
outside the cluster:

```yaml
# Pod spec
ports:
  - name: http
    containerPort: 5000
  - name: internal
    containerPort: 5001
---
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: thundercloud
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: thundercloud
  podMetricsEndpoints:
    - port: internal
      path: /metrics
      interval: 30s
```

Add a `NetworkPolicy` that admits port 5001 only from the Prometheus
namespace.

## Metric reference

Label values come from fixed sets. Nothing is labeled by meter, customer or
user, so series counts stay small however large the site is.

### HTTP (public listener)

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `http_requests_total` | counter | `method`, `route`, `status` | Requests served. |
| `http_request_duration_seconds` | histogram | `method`, `route` | Time to serve a request, including the response body. |
| `http_requests_in_progress` | gauge | | Requests being served right now. |

`route` is the matched route template, not the raw path: `/health` for API
routes, and the Flask URL rule for the web UI, such as
`/microgrid/<ground_serial>/<int:meter_code>/`. Requests that match no route (404s, scanners) are counted as `unmatched`.
`method` is `OTHER` for anything outside GET, HEAD, POST, PUT, PATCH, DELETE
and OPTIONS. An unhandled exception is counted as `500`.

### Periodic tasks

`process_events` and `process_transactions` run every minute.
`nightly_dashboard_tariff_summary` runs at 00:05 local time. The label is
`task`, not `job`, because Prometheus reserves `job` for the scrape job.

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `thundercloud_task_runs_total` | counter | `task`, `result` | Runs by result: `success` or `error`. The error series starts at 0. |
| `thundercloud_task_duration_seconds` | histogram | `task` | Run time. |
| `thundercloud_task_last_success_timestamp_seconds` | gauge | `task` | Unix time of the last successful run. |

### Meter-driver runtime (ground only)

These metrics describe the connection to the meter driver (see
[Meter drivers](../README.md#meter-drivers)). On cloud deployments, and on a
ground with no driver configured, only `thundercloud_metering_runtime_active`
is reported, with the value 0.

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `thundercloud_metering_runtime_active` | gauge | | 1 while this process is connected to a meter driver. |
| `thundercloud_metering_gateway_connected` | gauge | | 1 if the driver last reported its gateway connected, 0 if disconnected. Absent until the driver first reports it. |
| `thundercloud_metering_commands_paused` | gauge | | 1 while commands are held during gateway recovery. |
| `thundercloud_metering_command_queue_depth` | gauge | | Commands waiting to be sent to the driver. |
| `thundercloud_metering_commands_total` | counter | `op`, `result` | Commands sent through the command queue, which carries meter changes made in the app. By op (`configure_meter`, `set_balance`, `register_meter`, `unregister_meter`) and result (`ok`, `error`, or `dropped` for an unrecognized op). |
| `thundercloud_metering_command_duration_seconds` | histogram | `op` | Time for the driver to accept a queued command. |
| `thundercloud_metering_reconciles_total` | counter | `result` | Full reconciles by result (`ok` or `error`). A reconcile initializes the driver, then registers, configures and sets the balance of every meter. It runs at startup, after the driver restarts and after the gateway recovers, so a rising count means the driver or gateway is flapping. |
| `thundercloud_metering_reconcile_duration_seconds` | histogram | | Time to complete a reconcile. |
| `thundercloud_metering_reconcile_meter_failures_total` | counter | | Meters a reconcile failed to register, configure or set the balance of. |
| `thundercloud_metering_events_total` | counter | `type` | Events received from the driver, by event type. Unrecognized types are counted as `unknown`. |
| `thundercloud_metering_last_event_timestamp_seconds` | gauge | | Unix time of the last event received; 0 if none yet. |
| `thundercloud_metering_stream_reconnects_total` | counter | | Times the event stream ended or broke and was reconnected. |
| `thundercloud_metering_nodes` | gauge | `state` | From the driver's latest heartbeat summary: `registered` nodes, nodes `attempted` this heartbeat, and nodes that `responded`. |
| `thundercloud_readings_total` | counter | `result` | Meter readings received, by result: `written`, `duplicate`, `lock_timeout`, `incomplete` (no complete heartbeat window) or `error`. |
| `thundercloud_reading_ingest_lag_seconds` | histogram | | Time from the end of a reading's heartbeat window to its database write. |

### Database

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `thundercloud_db_query_duration_seconds` | histogram | `statement` | SQL execution time by statement type: `select`, `insert`, `update`, `delete` or `other`. |
| `thundercloud_db_pool_connections` | gauge | `state` | Connections in the SQLAlchemy pool: `checked_out` (in use) or `idle`. |
| `thundercloud_db_pool_size` | gauge | | Configured pool size. Overflow connections can push `checked_out` above it. |

### Build and process

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `thundercloud_build_info` | gauge | `version`, `revision`, `system` | Always 1. `system` is `ground` or `cloud`. |
| `process_*` | various | | CPU, resident memory, open file descriptors and start time, from the Prometheus client. |
| `python_*` | various | | Garbage-collector activity and interpreter version, from the Prometheus client. |

## Grafana

Add your Prometheus server as a data source (**Connections → Data sources →
Prometheus**), then import the ready-made dashboard,
[`grafana/thundercloud.json`](grafana/thundercloud.json) (**Dashboards → New
→ Import**). It asks for nothing at import: pick the data source and the
instances from the variables at the top. It has rows for HTTP, periodic
tasks, the meter driver, and the database and process.

To provision it instead, point a Grafana
[dashboard provider](https://grafana.com/docs/grafana/latest/administration/provisioning/#dashboards)
at a directory that holds the file.

The queries below are the building blocks for your own panels. The `job` and
`instance` labels come from your scrape configuration.

### Queries

| Panel | PromQL |
|---|---|
| Request rate by route | `sum by (route) (rate(http_requests_total[5m]))` |
| 5xx ratio | `(sum(rate(http_requests_total{status=~"5.."}[5m])) or vector(0)) / sum(rate(http_requests_total[5m]))` |
| p95 latency by route | `histogram_quantile(0.95, sum by (le, route) (rate(http_request_duration_seconds_bucket[5m])))` |
| Task duration, p95 | `histogram_quantile(0.95, sum by (le, task) (rate(thundercloud_task_duration_seconds_bucket[30m])))` |
| Time since a task last succeeded | `time() - thundercloud_task_last_success_timestamp_seconds` |
| Readings written per minute | `sum(rate(thundercloud_readings_total{result="written"}[5m])) * 60` |
| Reading ingest lag, p95 | `histogram_quantile(0.95, sum by (le) (rate(thundercloud_reading_ingest_lag_seconds_bucket[30m])))` |
| Meters responding | `thundercloud_metering_nodes{state="responded"} / ignoring(state) thundercloud_metering_nodes{state="attempted"}` |
| Driver command rate by result | `sum by (op, result) (rate(thundercloud_metering_commands_total[5m]))` |
| DB pool in use | `thundercloud_db_pool_connections{state="checked_out"} / ignoring(state) thundercloud_db_pool_size` |
| DB query p95 by statement | `histogram_quantile(0.95, sum by (le, statement) (rate(thundercloud_db_query_duration_seconds_bucket[5m])))` |
| Running version | `thundercloud_build_info` |

### Alerting starting points

Tune the thresholds to your site. The meter-driver rules assume the default
15-minute heartbeat period (`SM_HEARTBEAT_PERIOD`).

```yaml
groups:
  - name: thundercloud
    rules:
      - alert: ThunderCloudHighErrorRate
        expr: |
          sum by (instance) (rate(http_requests_total{status=~"5.."}[5m]))
            / sum by (instance) (rate(http_requests_total[5m])) > 0.05
        for: 10m
      - alert: ThunderCloudTaskFailing
        expr: increase(thundercloud_task_runs_total{result="error"}[15m]) > 0
      - alert: ThunderCloudMinuteTaskStale
        expr: |
          time() - thundercloud_task_last_success_timestamp_seconds{task=~"process_events|process_transactions"} > 600
      - alert: ThunderCloudMeterDriverSilent
        expr: |
          thundercloud_metering_runtime_active == 1
            and on (instance) (time() - thundercloud_metering_last_event_timestamp_seconds) > 1800
      - alert: ThunderCloudGatewayDisconnected
        expr: thundercloud_metering_gateway_connected == 0
        for: 10m
      - alert: ThunderCloudDriverCommandsFailing
        expr: sum by (instance, op) (increase(thundercloud_metering_commands_total{result="error"}[15m])) > 0
      - alert: ThunderCloudReconcileFailing
        expr: |
          increase(thundercloud_metering_reconciles_total{result="error"}[15m]) > 0
            or increase(thundercloud_metering_reconcile_meter_failures_total[15m]) > 0
      - alert: ThunderCloudReadingWritesFailing
        expr: sum by (instance) (increase(thundercloud_readings_total{result=~"error|lock_timeout"}[1h])) > 0
      - alert: ThunderCloudDBPoolSaturated
        expr: |
          thundercloud_db_pool_connections{state="checked_out"}
            / ignoring(state) thundercloud_db_pool_size >= 1
        for: 10m
```
