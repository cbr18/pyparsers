# PyParsers Prometheus Metrics

PyParsers exports Prometheus metrics from each parser service process. There is no pyparsers-side aggregator endpoint.

Each service exposes its own `GET /metrics` endpoint:

| Service | Internal Docker target | Typical host URL |
| --- | --- | --- |
| `dongchedi` | `pyparsers-dongchedi:5000/metrics` | `http://localhost:5001/metrics` |
| `che168` | `pyparsers-che168:5000/metrics` | `http://localhost:5002/metrics` |
| `encar` | `pyparsers-encar:5000/metrics` | `http://localhost:5003/metrics` |

Prometheus should scrape all source services and aggregate by the `source` label.

Example Docker-network scrape config:

```yaml
scrape_configs:
  - job_name: pyparsers
    metrics_path: /metrics
    static_configs:
      - targets:
          - pyparsers-dongchedi:5000
          - pyparsers-che168:5000
          - pyparsers-encar:5000
```

## Label Policy

Metrics intentionally avoid high-cardinality labels. Do not add raw `task_id`, `car_id`, `batch_id`, external URLs, or request paths containing IDs.

HTTP request paths are exported as FastAPI route patterns such as `/tasks/{task_id}` and `/cars/page/{page}`. The in-progress request gauge uses `path="pending"` while routing is not yet known.

Common labels:

| Label | Meaning |
| --- | --- |
| `source` | Parser source: `dongchedi`, `che168`, `encar`, or `legacy` for the old combined app. |
| `task_type` | Parser task type: `full`, `incremental`, or `detailed`. |
| `status` | HTTP status or task status, depending on the metric. |
| `stage` | Task execution stage such as `queued`, `listing`, `detailed`, `completed`, or `failed`. |
| `result` | Stable outcome: usually `success`, `failure`, `blocked`, or `available`. |
| `banned` | `true` when che168 reported or inferred a blocked/banned detail result. |
| `kind` | che168 fallback kind: `desktop` or `mobile`. |

## HTTP Metrics

### `pyparsers_http_requests_total`

Counter of handled HTTP requests.

Labels: `source`, `method`, `path`, `status`.

Use it to identify request volume and endpoint-level error rates.

```promql
sum by (source, path, status) (rate(pyparsers_http_requests_total[5m]))
```

### `pyparsers_http_request_duration_seconds`

Histogram of HTTP request duration.

Labels: `source`, `method`, `path`, `status`.

Use it to detect slow parser endpoints.

```promql
histogram_quantile(
  0.95,
  sum by (source, path, le) (rate(pyparsers_http_request_duration_seconds_bucket[10m]))
)
```

### `pyparsers_http_requests_in_progress`

Gauge of requests currently in progress.

Labels: `source`, `method`, `path`.

The `path` label is `pending` to avoid raw-path cardinality while the router is still resolving the request.

## Task Metrics

### `pyparsers_tasks_created_total`

Counter of parser tasks accepted through `POST /tasks`.

Labels: `source`, `task_type`.

### `pyparsers_tasks_completed_total`

Counter of terminal task outcomes.

Labels: `source`, `task_type`, `status`.

Terminal statuses are `succeeded`, `failed`, and `cancelled`.

```promql
sum by (source, task_type, status) (rate(pyparsers_tasks_completed_total[30m]))
```

### `pyparsers_task_duration_seconds`

Histogram of task execution duration.

Labels: `source`, `task_type`, `status`.

Use it to track long full scans, slow incremental scans, or detailed-task regressions.

```promql
histogram_quantile(
  0.95,
  sum by (source, task_type, le) (rate(pyparsers_task_duration_seconds_bucket[1h]))
)
```

### `pyparsers_tasks_active`

Gauge of retained tasks by current state.

Labels: `source`, `task_type`, `status`, `stage`.

This includes queued/running tasks and recently retained completed task records.

```promql
sum by (source, task_type, status, stage) (pyparsers_tasks_active)
```

### `pyparsers_task_queue_size`

Gauge of the per-service task queue size.

Labels: `source`.

If this grows while completions do not, the service is saturated or tasks are stuck.

### `pyparsers_task_records`

Gauge of task records retained in memory by status.

Labels: `source`, `status`.

Task retention is controlled by `TASK_TTL_HOURS`.

### `pyparsers_results_cached`

Gauge of completed task result payloads retained in memory.

Labels: `source`.

Result retention is controlled by `TASK_RESULT_TTL_MINUTES`.

### `pyparsers_task_items_found_total`

Counter of items found by completed parser tasks.

Labels: `source`, `task_type`.

### `pyparsers_task_items_sent_total`

Counter of items sent or returned by completed parser tasks.

Labels: `source`, `task_type`.

For `delivery_mode=push_batches`, this tracks accepted DataHub batch items. For result mode, it tracks result item count.

## Listing Metrics

### `pyparsers_listing_pages_scanned_total`

Counter of listing pages scanned by completed listing tasks.

Labels: `source`, `task_type`.

### `pyparsers_listing_items_found_total`

Counter of listing items found by completed listing tasks.

Labels: `source`, `task_type`.

### `pyparsers_listing_items_filtered_total`

Counter of listing items filtered by stable reason.

Labels: `source`, `task_type`, `reason`.

Current stable reason:

| Reason | Meaning |
| --- | --- |
| `year_lt_2017` | Listing item was filtered because it is older than the supported minimum year. |

### `pyparsers_listing_empty_pages_total`

Counter of listing pages that returned no cars.

Labels: `source`, `task_type`.

For `che168`, repeated empty pages are especially important because the full scan stops after several empty pages.

## DataHub Batch Delivery Metrics

These metrics cover `delivery_mode=push_batches` and are emitted around `_flush_listing_batch` / `_post_parser_batch`.

### `pyparsers_batch_delivery_attempts_total`

Counter of DataHub batch delivery attempts.

Labels: `source`, `task_type`, `result`.

`result` is `success` or `failure` for each HTTP attempt.

### `pyparsers_batch_delivery_duration_seconds`

Histogram of one DataHub batch delivery attempt.

Labels: `source`, `task_type`, `result`.

### `pyparsers_batch_items_sent_total`

Counter of listing items accepted by successful DataHub batch sends.

Labels: `source`, `task_type`.

### `pyparsers_batch_size_items`

Histogram of successful parser batch sizes.

Labels: `source`, `task_type`.

Final batches may contain zero items when the previous non-final batch ended exactly on a batch-size boundary.

### `pyparsers_batch_retries_total`

Counter of retry attempts after the first DataHub delivery attempt failed.

Labels: `source`, `task_type`.

### `pyparsers_batch_failures_total`

Counter of parser batches that failed after all configured retries.

Labels: `source`, `task_type`.

### `pyparsers_batch_final_total`

Counter of final batches successfully sent to DataHub.

Labels: `source`, `task_type`.

A task that uses push-batch delivery should normally emit one final batch.

## Source Probe Metrics

Source probe metrics are updated when `/blocked` runs.

### `pyparsers_source_probe_total`

Counter of source availability probe outcomes.

Labels: `source`, `result`.

`result` is `available` or `blocked`.

### `pyparsers_source_probe_duration_seconds`

Histogram of `/blocked` probe duration.

Labels: `source`, `result`.

### `pyparsers_source_blocked`

Gauge of the last observed blocked status.

Labels: `source`.

Values:

| Value | Meaning |
| --- | --- |
| `0` | Last probe considered the source available. |
| `1` | Last probe considered the source blocked or unavailable. |

```promql
pyparsers_source_blocked == 1
```

## Che168 Detail Metrics

Che168 detail parsing has extra metrics because it includes API calls, inflight coalescing, failure caching, and Selenium/mobile fallback.

### `pyparsers_che168_detail_requests_total`

Counter of che168 detail endpoint requests.

Labels: `endpoint`, `result`, `banned`.

`endpoint` is `parse` or `parse-batch`.

### `pyparsers_che168_detail_duration_seconds`

Histogram of che168 detail endpoint duration.

Labels: `endpoint`, `result`, `banned`.

### `pyparsers_che168_detail_batch_size_items`

Histogram of `/detailed/parse-batch` request sizes.

No labels.

### `pyparsers_che168_detail_batch_items_total`

Counter of per-car outcomes inside che168 detail batch requests.

Labels: `endpoint`, `result`, `banned`.

### `pyparsers_che168_detail_inflight`

Gauge of che168 detail parses currently owned by this process.

This tracks actual parser work, not coalesced waiters.

### `pyparsers_che168_detail_coalesced_total`

Counter of che168 detail requests that reused existing in-flight work for the same `car_id`.

High values mean callers are requesting duplicate car IDs concurrently.

### `pyparsers_che168_detail_failure_cache_hits_total`

Counter of che168 detail requests served from the short failure cache.

The cache stores recent banned failures to avoid hammering che168 during a cap/block window.

### `pyparsers_che168_detail_failure_cache_writes_total`

Counter of banned failed detail parses written to the failure cache.

### `pyparsers_che168_fallback_attempts_total`

Counter of che168 fallback attempts.

Labels: `kind`, `result`.

`kind` is `desktop` or `mobile`. `result` is `success` when the fallback returned a non-empty payload.

### `pyparsers_che168_fallback_duration_seconds`

Histogram of che168 fallback duration.

Labels: `kind`, `result`.

### `pyparsers_che168_fallback_in_progress`

Gauge of fallback operations currently holding a fallback slot.

Labels: `kind`.

Use this with `CHE168_FALLBACK_MAX_CONCURRENT` to see whether Selenium fallback is saturated.

## Runtime Exporter Metric

### `pyparsers_metrics_scrape_timestamp_seconds`

Gauge emitted at render time with the Unix timestamp of the scrape response.

This is useful for checking that a target is returning fresh output.

### `pyparsers_build_info`

Gauge reserved for source/build metadata.

Labels: `source`, `version`.

## Operational Checks

Useful quick checks:

```promql
# Error rate by service and route
sum by (source, path, status) (rate(pyparsers_http_requests_total{status!~"2.."}[5m]))

# Queued/running tasks
sum by (source, task_type, status, stage) (pyparsers_tasks_active{status=~"queued|running"})

# DataHub delivery failures
sum by (source, task_type) (rate(pyparsers_batch_delivery_attempts_total{result="failure"}[10m]))

# Sources currently considered blocked
pyparsers_source_blocked == 1

# Che168 fallback pressure
sum by (kind) (pyparsers_che168_fallback_in_progress)
```
