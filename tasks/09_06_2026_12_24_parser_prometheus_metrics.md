# Add Prometheus metrics for parser services

Status: DONE
Created: 2026-06-09 12:24
Project: pyparsers
Plan: [09_06_2026_12_24_parser_prometheus_metrics.md](../plans/09_06_2026_12_24_parser_prometheus_metrics.md)

## Problem

The parser services expose health endpoints and task status APIs, but they do not expose Prometheus metrics. Operators cannot easily see whether a specific source is slow, blocked, accumulating queued tasks, failing batch delivery to DataHub, or spending excessive time in che168 detail fallback.

The services are separate FastAPI processes for `dongchedi`, `che168`, and `encar`, so observability should be exported from each service-local `/metrics` endpoint and aggregated by Prometheus through scrape targets.

## Evidence

- `docker-compose.yml` runs separate source services with Granian and internal port `5000`.
- `source_apps.py` builds one FastAPI app per source and registers common `/health` and `/tasks` routes.
- `async_api_server.py` already has `add_performance_info` middleware that measures request duration.
- `task_service.py` centralizes task creation, execution, status transitions, listing batch delivery, and DataHub push-batch retries.
- `api/che168/detailed_api.py` centralizes che168 detail parsing, batch parsing, inflight coalescing, and failure-cache behavior.
- `api/che168/detailed_parser_api.py` contains Selenium/mobile fallback paths and fallback concurrency control.

## Non-Functional Constraints

- Keep parser request and response contracts unchanged.
- Keep DataHub push-batch payload shape, retry behavior, idempotency headers, and final-batch behavior unchanged.
- Keep source services independent; do not add a pyparsers-side metrics aggregator service.
- Keep `/metrics` low-overhead and safe to scrape regularly.
- Avoid high-cardinality labels such as raw `task_id`, `car_id`, `batch_id`, full URLs, or unnormalized paths.
- Preserve IP whitelist behavior for protected APIs while allowing Prometheus to scrape `/metrics` through an explicitly configured public path or deployment network policy.

## Out Of Scope

- Changing parser business logic, source scraping algorithms, or filtering rules.
- Changing Docker Compose ports unless explicitly requested in a follow-up task.
- Replacing all direct `requests` calls with a shared HTTP client.
- Adding Grafana dashboards or alert rules.
- Adding metrics for DataHub internals; this task only covers pyparsers.
- Changing lock files or dependencies without explicit approval during implementation.

## Desired Behavior

Each source service exposes a service-local `/metrics` endpoint in Prometheus text format. Prometheus can scrape the three services separately and aggregate by labels such as `source`, `task_type`, `stage`, `status`, `endpoint`, and `result`.

The exported metrics should show:

- HTTP request count, in-flight requests, and latency by normalized route.
- Task creation, active task counts, completion counts, task duration, queue size, and task item counters.
- Listing page scans, found items, empty pages, and filtered items where the reason is stable and low cardinality.
- DataHub push-batch attempts, retries, failures, duration, batch size, sent item count, and final batch sends.
- Source blocked/probe status.
- Che168 detail parse request/result counts, duration, batch size, banned results, inflight work, coalesced requests, failure-cache hits/writes, and fallback attempts.
- Basic process/runtime metrics from the Prometheus client when available.

## Affected Areas

- `pyparsers/pyproject.toml`
- `pyparsers/uv.lock`
- `pyparsers/source_apps.py`
- `pyparsers/async_api_server.py`
- `pyparsers/task_service.py`
- `pyparsers/api/che168/detailed_api.py`
- `pyparsers/api/che168/detailed_parser_api.py`
- `tests/unit/`
- `tests/integration/test_source_services.py`
- `docs/operations.md`
- `docs/services.md`

## Implementation Notes

- Prefer a small shared metrics module that owns metric definitions and helper functions.
- Register the same `/metrics` route on each source app, but export source-specific label values from each process.
- Use normalized FastAPI route paths for HTTP labels, not raw request paths.
- Do not include `task_id`, `car_id`, `batch_id`, or external endpoint URL as metric labels.
- Use counters for events, gauges for active/current values, and histograms for latency and sizes.
- If `prometheus-client` is added, update dependency metadata only after explicit approval because lock files are protected by repository instructions.
- Keep tests focused on metrics registration, label normalization, task state updates, batch delivery counters, and che168 detail/fallback counters.

## Acceptance Criteria

- Each source service serves `GET /metrics` with Prometheus-compatible output.
- Prometheus can scrape `dongchedi`, `che168`, and `encar` separately and distinguish them by `source` label.
- HTTP metrics use normalized path labels and do not create unbounded label cardinality.
- Task metrics reflect queued, running, succeeded, failed, and cancelled task transitions.
- DataHub batch metrics count successful sends, retries/failures, sent items, and final batches.
- Che168 detail metrics distinguish success, failure, and banned outcomes.
- Existing `/health`, `/blocked`, `/tasks`, listing, detailed, and DataHub push-batch contracts remain unchanged.
- Documentation explains scrape targets and the meaning of the primary metrics.

## Test Plan

- Run focused unit tests for metrics helpers and task-service instrumentation.
- Run `python -m pytest tests/unit`.
- Run `python tests/integration/test_source_services.py` when source services are available.
- Run `bash ./scripts/health-check.sh` for Docker/runtime verification.
- Manually curl `/metrics` for each source service and verify expected metric names and `source` labels.
- Verify route labels are normalized for dynamic routes such as `/tasks/{task_id}` and `/cars/page/{page}`.

## Rollback

Remove the metrics module, `/metrics` route registration, instrumentation calls, tests, dependency changes, and documentation updates. If deployment fails only because scraping is too noisy or blocked by networking, disable Prometheus scraping for pyparsers while keeping the parser services running on the previous API contracts.
