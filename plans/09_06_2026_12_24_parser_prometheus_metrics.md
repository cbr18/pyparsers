# Plan: Add Prometheus metrics for parser services

Task: [09_06_2026_12_24_parser_prometheus_metrics.md](../tasks/09_06_2026_12_24_parser_prometheus_metrics.md)
Status: DONE

## Goal

Expose Prometheus metrics from each source service's own `/metrics` endpoint and instrument the shared parser flows that matter operationally: HTTP requests, task lifecycle, listing progress, DataHub batch delivery, source blocked probes, and che168 detail/fallback behavior.

## Sequence

1. Confirm dependency approach for Prometheus exposition, including whether adding `prometheus-client` and updating `uv.lock` is approved.
2. Add a small shared metrics module with metric definitions, label helpers, normalized route extraction, and source-aware wrappers.
3. Register `GET /metrics` on each source app in `source_apps.py` and include `/metrics` in the public paths used by `IPWhitelistMiddleware`.
4. Instrument HTTP middleware with request counters, in-flight gauge, and duration histogram using normalized route labels.
5. Instrument `TaskService.create_task`, `_execute`, `_update_task`, and queue/result state for task counters, active task gauges, queue size, item counters, and duration histograms.
6. Instrument listing runners for pages scanned, item counts, empty pages, and stable filter reasons where the code already has explicit decisions.
7. Instrument `_flush_listing_batch` and `_post_parser_batch` for DataHub batch attempts, retries, failures, duration, batch sizes, sent items, and final batches.
8. Instrument source probe endpoints so `/blocked` updates source probe counters, duration, and blocked gauge.
9. Instrument che168 detail parsing in `detailed_api.py` for parse counts, durations, batch size, banned outcomes, inflight work, coalescing, and failure-cache hits/writes.
10. Instrument che168 Selenium/mobile fallback slots in `detailed_parser_api.py` with fallback in-progress gauges, attempts, duration, and result counters.
11. Add focused unit tests for route normalization, task metrics, batch metrics, and che168 detail metric events.
12. Update operations/service docs with scrape target examples and metric descriptions.
13. Run focused tests, unit tests, integration smoke checks where available, and manual `/metrics` curl checks.

## Validation

- `GET /metrics` returns Prometheus text output from each parser service.
- Scraped series include `source="dongchedi"`, `source="che168"`, or `source="encar"` as appropriate.
- Dynamic request paths are exported as route patterns rather than raw IDs.
- Task metrics change correctly when a task is queued, started, completed, failed, or cancelled.
- Batch delivery metrics reflect success, retry, failure, item count, and final-batch behavior without changing DataHub payloads.
- Che168 detail metrics distinguish successful, failed, banned, coalesced, cached, and fallback paths.
- Existing live smoke tests and health checks continue to pass.

## Risks

- Incorrect route labeling can create high-cardinality time series.
- Metrics initialization in multiple app contexts can accidentally duplicate collectors if not guarded.
- Instrumentation in hot paths can add overhead if labels or observations are built inefficiently.
- Adding `/metrics` to public paths may expose operational data if network access is not controlled.
- Che168 fallback instrumentation can be misleading if success/failure is inferred from partial parser outputs instead of clear control-flow points.
- Dependency and lock-file changes need explicit approval under repository rules.

## Rollback

Revert the metrics module, route registration, instrumentation calls, dependency updates, tests, and documentation. If a production issue is limited to scraping volume or access policy, remove the Prometheus scrape targets or block `/metrics` at the network layer while leaving parser API behavior untouched.
