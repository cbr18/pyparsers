# Parser & Enhancement Architecture

This note condenses every parser-related document (structure, requirements, improvements, worker behavior, retry/throttling utilities) into one place.

## Pipeline Overview

| Stage | Entry point | Purpose | Notes |
| --- | --- | --- | --- |
| 1. Listing scrape | `fetch_cars_by_page(page)` | Pull 20‑80 raw listings per page, minimal fields, stop early if IDs already exist when running incremental mode. | Filters by `year >= 2017` before doing any heavy work. |
| 2. Detail page | `fetch_car_detail(sku_id)` | Selenium+BeautifulSoup parser that reads `__NEXT_DATA__` and enriches the base entity. | Captures gallery (`head_images[]` → `image_gallery` string), dealer info, owner history, cert tags, counts. |
| 3. Specifications | `fetch_car_specifications(car_id)` | Parses the `/auto/params-carIds-{car_id}` table for performance/tech specs. | Fills 60+ fields (power, torque, EV metrics, suspension, brakes, safety, comfort, multimedia, headlights, etc.). |

`enhance_car_with_details()` orchestrates stages 2 and 3, merges the data, and sets `has_details` / `last_detail_update`.

## Modes & Requirements

- **Full mode**: iterate every page, skip previously-seen IDs, batch persist results (50‑100 per commit).
- **Incremental mode**: walk pages until the first known ID is found, then stop (only new entries are processed).
- **Filtering**: listings with year < 2017 are discarded before the expensive detail fetch.
- **Error handling**: failed detail/spec parsing skips the record but logs category + context. No partially-filled cars are stored.
- **Validation worker**: (future) dedicated worker in `datahub` can re-check availability and mark `is_available=false` when sources remove a listing.
- **Concurrency**: default target is 5 simultaneous requests per source with optional per-endpoint rate limiting. The HTTP client enforces this centrally.
- **Edge cases**: missing `car_id`/`sku_id` are skipped, `power` must contain digits, duplicates resolved via `(source, car_id)` partial index.

## Enhancement Worker

The Go `EnhancementWorker` inside datahub continuously enriches cars:

- Starts automatically once migrations finish.
- Pulls cars with `has_details=false` (both sources) and processes them in batches.
- Default config: `batch_size=10`, `delay_between_batches=300s`, `delay_between_cars=2s`, `max_concurrent=3`.
- Endpoints: `GET /enhancement/status`, `POST /enhancement/start|stop|config`.
- Cron container keeps inserting fresh listings so the worker always has something to do.
- Success path: call parser-service detail/spec routes → merge response → update car via GORM `.Updates()` (preserves indexed fields) → mark `has_details=true`.
- Failure path: log error, increment `failed_enhancement_attempts`, leave `has_details=false` so future cycles can retry.

**Throughput** (default config): ~120 cars/hour; adjust config for faster fill (example payload in `operations.md`).

## Che168 Improvements (2025‑11‑15)

- Expanded selector logic (no longer assumes label/value share CSS classes) so >110 labels map correctly.
- Added post-processing for combined fields such as `长*宽*高` → `length/width/height`, mileage normalization (`万公里` → km), year inference from registration date.
- `_convert_to_domain_car` now feeds Go's `domain.Car` 1:1 with dongchedi fields, ensuring `has_details` semantics match.
- FastAPI router at `/che168/detailed/*` exposes `parse`, `parse-batch`, and `health` endpoints, and is served by the dedicated `pyparsers-che168` service.
- Current smoke coverage is provided by `tests/integration/test_source_services.py`, which verifies split-service startup plus live list/detail parsing against the direct `5001/5002` endpoints.

## Parser Refactor Summary

- Che168 now uses the same clients, services, workers, and HTTP handlers as dongchedi. Legacy `car_detail_service.go`, `car_detail_worker.go`, and standalone handlers were removed.
- `EnhanceCar` and `BatchEnhanceCars` live on both `DongchediClient` and `Che168Client`.
- The enhancement worker automatically detects `car.Source` instead of branching per service, making future sources plug-and-play.

## HTTP Client Infrastructure

### Throttling (`api/throttling.py`)
- `RateLimiter` (token bucket) and `ConcurrencyLimiter` keep global/per-endpoint request counts under control.
- `ResourceManager` pairs both and powers the `@throttle` decorator.
- `HTTPClient` instantiates its own `ResourceManager` per instance; defaults are `rate_limit=10 req/s`, `burst=20`, `max_concurrency=10`.

### Retry & Circuit Breaker (`api/retry.py`)
- `RetryStrategy` supports exponential backoff, jitter, and per-status/per-exception filters.
- `CircuitBreaker` avoids hammering dead upstreams (`failure_threshold`, `recovery_timeout`, `half_open_max_calls`).
- Decorators `@async_retry` / `@sync_retry` wrap both behaviors; `HTTPClient` applies them automatically.

### Structured Logging (`api/logging_utils.py`)
- `StructuredLogger` emits JSON logs (timestamp, UUID, context, error metadata).
- `ErrorHandler` maps exception types to `ErrorCategory` enums and can dispatch custom handlers.
- `@log_function` / `@log_async_function` trace entry/exit and funnel exceptions into the error handler.

These utilities are shared by parsers, the async API server, and scheduled workers—keep them in mind whenever you add new external calls.
