# DataHub Batch Ingestion Contract

This document is the implementation contract and technical assignment for moving parser listing ingestion from "collect everything and return one result" to page/batch delivery. It applies to all parser sources:

- `dongchedi`
- `che168`
- `encar`

The goal is to keep parser jobs observable and cancellable while allowing `datahub` to persist listings incrementally and safely.

## Current Problem

The existing parser task contract is pull-based:

1. `datahub` creates `POST /tasks`.
2. `pyparsers` scans pages.
3. `pyparsers` stores every parsed listing in memory.
4. `datahub` waits until the task succeeds.
5. `datahub` calls `GET /tasks/{task_id}/result` and persists one large payload.

This is acceptable for small sources, but it is weak for larger inventories, especially Encar:

- large in-memory result inside `pyparsers`;
- large final JSON response;
- no partial persistence when the parser fails late;
- harder retry after a partial run;
- no durable page-level checkpoint in `datahub`;
- full Encar inventory can be around 160k live listings, so a synchronous full payload is operationally risky.

## Target Model

Use task-based orchestration, but deliver listing rows to `datahub` while the task is running.

Parser task request:

```json
{
  "task_type": "incremental",
  "parameters": {
    "delivery_mode": "push_batches",
    "batch_endpoint": "http://datahub:8080/parser/batches",
    "batch_size": 500,
    "id_field": "car_id",
    "existing_ids": ["41782412"]
  },
  "metadata": {
    "requested_by": "datahub",
    "upstream_task_id": "..."
  }
}
```

Parser behavior:

1. Parse listing pages.
2. Normalize source-specific rows into the canonical car payload.
3. Deduplicate rows inside the parser task by source + item id.
4. Send batches to `datahub`.
5. Update parser task progress (`items_found`, `items_sent`, `result_summary`).
6. Return a small final task result with summary only.

The old pull-result mode remains the default:

```json
{
  "task_type": "incremental",
  "parameters": {}
}
```

If `delivery_mode` is omitted, pyparsers still returns rows via `GET /tasks/{task_id}/result`.

## PyParsers Parameters

Supported for `full` and `incremental` tasks on all sources:

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `delivery_mode` | string | no | `result` | `result` keeps old behavior; `push_batches` sends rows to datahub while running. |
| `batch_endpoint` | string | required for push mode unless env is set | `DATAHUB_BATCH_ENDPOINT` or `${DATAHUB_URL}/parser/batches` | DataHub endpoint that accepts parser batches. |
| `batch_size` | integer | no | `BATCH_DELIVERY_DEFAULT_SIZE`, fallback `500` | Max listing rows per delivered batch. |
| `batch_timeout_seconds` | integer | no | `30` | HTTP timeout for one batch request. |
| `batch_max_retries` | integer | no | `3` | Retry count before parser task fails. |
| `batch_auth_token` | string | no | `DATAHUB_BATCH_TOKEN` | Optional bearer token for datahub batch endpoint. |

Source-specific parameters still apply:

- `dongchedi` incremental default `id_field`: `sku_id`
- `che168` incremental default `id_field`: `car_id`
- `encar` incremental default `id_field`: `car_id`

## DataHub Endpoint

Add this endpoint to `datahub`:

```http
POST /parser/batches
```

Headers sent by pyparsers:

```http
Content-Type: application/json
X-Parser-Task-Id: <parser task id>
X-Parser-Batch-Id: <parser task id>:<sequence>
Idempotency-Key: <parser task id>:<sequence>
Authorization: Bearer <token>   # optional
```

Request body:

```json
{
  "task_id": "49277059-7fb2-4146-b72f-2203e0878f5f",
  "source": "encar",
  "task_type": "incremental",
  "batch_id": "49277059-7fb2-4146-b72f-2203e0878f5f:1",
  "batch_sequence": 1,
  "page": 3,
  "is_final": false,
  "item_count": 500,
  "created_at": "2026-04-18T03:00:00.000000+00:00",
  "items": [
    {
      "source": "encar",
      "car_id": 41782412,
      "sku_id": "41782412",
      "title": "...",
      "price": 2370.0,
      "image": "https://ci.encar.com/...",
      "year": 2023,
      "mileage": 34670
    }
  ]
}
```

Recommended response:

```json
{
  "data": {
    "batch_id": "49277059-7fb2-4146-b72f-2203e0878f5f:1",
    "received": 500,
    "inserted": 120,
    "updated": 380,
    "duplicates_in_batch": 0,
    "duplicates_existing": 24
  },
  "message": "Parser batch accepted",
  "status": 202
}
```

Any `2xx` response is treated as accepted by pyparsers. DataHub should return a structured JSON response for diagnostics, but pyparsers does not require it.

PyParsers sends a final `is_final=true` batch before completing the task. This final batch may contain zero items when the previous non-final batch ended exactly on a `batch_size` boundary.

## DataHub Persistence Requirements

DataHub must treat parser batches as idempotent.

Required storage additions:

### `parser_ingestion_batches`

Suggested columns:

| Column | Type | Notes |
| --- | --- | --- |
| `batch_id` | text primary key | Same as `Idempotency-Key`. |
| `task_id` | text not null | Parser task id. |
| `source` | text not null | `dongchedi`, `che168`, `encar`. |
| `task_type` | text not null | `full` or `incremental`. |
| `batch_sequence` | integer not null | Monotonic sequence inside parser task. |
| `page` | integer | Last parser page represented by this batch. |
| `item_count` | integer not null | Count declared by parser. |
| `received_at` | timestamptz not null | DataHub receive time. |
| `processed_at` | timestamptz | Set after upsert transaction succeeds. |
| `status` | text not null | `processing`, `succeeded`, `failed`. |
| `error_message` | text | Last processing error. |

Unique constraints:

- `batch_id` unique primary key
- optional: `(task_id, batch_sequence)` unique

### `cars`

DataHub must keep a unique source identity:

- preferred: unique `(source, car_id)` for rows with non-null `car_id`
- fallback if needed: unique `(source, sku_id)` for rows without numeric `car_id`

For Encar, `car_id` and `sku_id` currently represent the same Encar listing id, with `sku_id` stored as a string.

## Data Integrity Rules

Parser result pages can shift while scraping. A car can appear on page N during one request and page N+1 during the next request. This happens when upstream listings are inserted, removed, or reprioritized while the task is running.

To preserve data integrity, deduplication must happen in both systems.

### In PyParsers

PyParsers now deduplicates inside one task before delivery:

- key priority: `car_id`, then `sku_id`, then `link`;
- key scope: `source`;
- duplicate rows from later pages are skipped in the same task;
- this reduces unnecessary writes and keeps `items_sent` closer to real unique rows.

This is an optimization, not the integrity boundary.

### In DataHub

DataHub is the integrity boundary.

DataHub must:

- accept the same `batch_id` more than once without duplicating rows;
- upsert cars by `(source, car_id)` or source-specific fallback id;
- process each batch in one database transaction;
- either fully apply a batch or leave it marked failed;
- safely retry failed or interrupted batches;
- tolerate the same car in different batches or parser tasks;
- never rely on page number as identity.

Recommended transaction flow:

1. Begin transaction.
2. Insert `parser_ingestion_batches(batch_id, status='processing')`.
3. If `batch_id` already exists with `status='succeeded'`, return the stored/derived success response.
4. Normalize and validate every item.
5. Deduplicate rows inside the batch by `(source, car_id)` before upsert.
6. Upsert into `cars`.
7. Mark batch `succeeded`.
8. Commit transaction.

If any DB write fails:

1. Roll back item upserts.
2. Mark the batch failed in a separate transaction if possible.
3. Return non-2xx so pyparsers retries.

## Upsert Semantics

Listing batches should not erase detailed fields.

When datahub upserts listing rows:

- update listing-level fields such as title, price, image, mileage, year, city, source link, availability;
- preserve detailed fields unless the incoming payload contains a non-null replacement;
- do not set `has_details=false` for an existing row that already has details;
- keep `last_detail_update` unchanged on listing-only upserts;
- set `has_details=false` only for newly inserted listing rows.

Recommended rule:

- non-null incoming listing values can update listing columns;
- null incoming values must not overwrite non-null stored values unless the field is explicitly allowed to clear.

## Task Completion Semantics

With `delivery_mode=push_batches`, parser task result should be small:

```json
{
  "pages_scanned": 12,
  "items_found": 570,
  "delivery_mode": "push_batches",
  "batches_sent": 2,
  "items_sent": 570,
  "failed_batches": 0,
  "batch_size": 500
}
```

DataHub should still poll parser task status:

- `status`
- `stage`
- `heartbeat_at`
- `items_found`
- `items_sent`
- `result_summary`
- `error_message`

When parser task succeeds:

- DataHub confirms `items_sent` matches accepted batch totals.
- DataHub can mark its orchestration task completed.
- DataHub does not need to call `GET /tasks/{task_id}/result` for rows; it may call it only for summary/debugging.

## Detailed Enrichment

Batch delivery is for listing rows only.

Detailed enrichment remains a separate pipeline:

- create `detailed` parser tasks;
- or use source-specific detail endpoints;
- run with lower concurrency/rate limits;
- prioritize new rows and stale rows;
- update `has_details=true` only after a successful detailed merge.

Do not fetch detailed data while listing pages are being scanned by default. It makes discovery too slow and increases upstream pressure.

## Source Notes

### Dongchedi

- Detail lookup primarily uses `sku_id`.
- Incremental default id field remains `sku_id`.
- Listing pages are moderate size, but push batching still improves failure recovery.

### Che168

- Detail lookup requires `car_id` and usually `shop_id`.
- Listing can be unstable because of upstream anti-bot behavior.
- Push batches let DataHub preserve partial progress if later pages fail.

### Encar

- Listing and detail are direct JSON APIs.
- Detail lookup uses `car_id`.
- Full inventory is large; use `push_batches` for production full/incremental ingestion.
- The legacy synchronous `/update/full` route intentionally does not run a full Encar crawl.

## DataHub Technical Assignment

Implement these changes in the datahub service repository:

1. Add `POST /parser/batches`.
2. Add `parser_ingestion_batches` persistence table and migration.
3. Add idempotency handling by `batch_id`.
4. Add batch-level transaction boundaries.
5. Add car upsert logic for listing rows that preserves existing detailed fields.
6. Extend source enums/switches to include `encar`.
7. Add source config for parser base URLs:
   - `dongchedi`: `http://pyparsers-dongchedi:5000`
   - `che168`: `http://pyparsers-che168:5000`
   - `encar`: `http://pyparsers-encar:5000`
8. Change full/incremental orchestration to create parser tasks with `delivery_mode=push_batches`.
9. Poll parser task status until terminal state.
10. On parser failure, mark the datahub orchestration task failed but keep already committed batches.
11. Add reconciliation endpoint/job that compares parser task `items_sent` with DataHub accepted rows for the task id.
12. Add tests for:
    - duplicate batch id;
    - duplicate car across two batches;
    - duplicate car inside one batch;
    - partial failure rollback;
    - null listing fields not erasing detailed fields;
    - Encar source accepted by filters/update/checkcar paths.

## Rollout Plan

1. Keep default parser `delivery_mode=result`.
2. Implement DataHub batch endpoint behind feature flag.
3. Enable `push_batches` first for Encar incremental jobs.
4. Enable for Encar full jobs with conservative task/page limits.
5. Enable for Che168 incremental.
6. Enable for Dongchedi incremental/full.
7. After confidence, keep pull-result mode only for local debugging and small manual runs.

## Operational Metrics

DataHub should expose:

- batches received per source;
- batches failed per source;
- rows inserted/updated per source;
- duplicate rows skipped;
- last parser task heartbeat;
- oldest running parser task age;
- accepted rows vs parser `items_sent`;
- batch processing latency percentiles.

These metrics should be visible per source and per task id.
