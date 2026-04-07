# DataHub Task Contract

This document describes the recommended interaction pattern between `datahub` and the split parser services.

## Ownership

- `datahub` is the system of record for orchestration and persistence.
- `pyparsers` execute work and expose execution state.
- `pyparsers` do not push task status into `datahub`.
- `datahub` should create parser jobs, poll them, decide on retries/timeouts, and persist final data.

## Parser Job Lifecycle

Every parser task uses the same status model:

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

Every parser task also exposes a finer-grained `stage`:

- `queued`
- `initializing`
- `listing`
- `detailed`
- `finalizing`
- `completed`
- `failed`
- `cancelled`

## Recommended Flow

### 1. Create a parser task

`datahub` calls:

- `POST http://localhost:5001/tasks`
- or `POST http://localhost:5002/tasks`

with:

```json
{
  "task_type": "full|incremental|detailed",
  "parameters": {},
  "metadata": {
    "requested_by": "datahub",
    "upstream_task_id": "..."
  }
}
```

The parser returns `202` and a task snapshot in `queued`.

### 2. Poll the parser task

`datahub` polls:

- `GET /tasks/{task_id}`

and reads:

- `status`
- `stage`
- `heartbeat_at`
- `progress_current`
- `progress_total`
- `progress_unit`
- `items_found`
- `items_processed`
- `items_sent`
- `error_message`
- `result_available`

### 3. Decide liveness in datahub

Recommended rules:

- `queued` too long -> alert or retry orchestration
- `running` with stale `heartbeat_at` -> mark parser task stuck
- `failed` -> persist parser error and decide retry/backoff in `datahub`
- `cancelled` -> reflect user or system cancellation in `datahub`
- `succeeded` with `result_available=true` -> fetch final result

## Progress Semantics

The fields are shared across all task types:

- `full`
  - usually `progress_unit = "page"`
  - `progress_current = current scanned page`
  - `progress_total = estimated page cap`
- `incremental`
  - usually `progress_unit = "page"`
  - stops early on first known ID
- `detailed`
  - usually `progress_unit = "car"`
  - `progress_total = batch size`
  - `items_processed = completed detailed items`

This allows `datahub` to handle all task types with one status model.

## Fetching the Final Result

After `succeeded`, `datahub` calls:

- `GET /tasks/{task_id}/result`

The parser returns:

```json
{
  "data": {
    "task": { "...": "terminal task snapshot" },
    "result": []
  },
  "message": "Task result fetched",
  "status": 200
}
```

`result` is the actual parser payload that `datahub` should persist and post-process.

## Cancellation

If `datahub` decides a parser task should stop:

- `POST /tasks/{task_id}/cancel`

Behavior:

- queued task -> immediately becomes `cancelled`
- running task -> sets `cancel_requested=true` and stops at the next safe checkpoint

## Source-Specific Parameters

### Dongchedi

- `full`
  - no required parameters
- `incremental`
  - `parameters.id_field`, default `sku_id`
  - `parameters.existing_ids`
- `detailed`
  - `parameters.car_ids`

### Che168

- `full`
  - no required parameters
- `incremental`
  - `parameters.id_field`, default `car_id`
  - `parameters.existing_ids`
- `detailed`
  - `parameters.requests`
  - each item must contain:
    - `car_id`
    - `shop_id`
    - optional `force_update`

## Why This Contract

This keeps responsibilities clean:

- `datahub` owns orchestration, retries, timeout policy, and persistence
- `pyparsers` own execution, heartbeat, and parser-specific progress

That avoids split-brain task state between services and gives `datahub` enough live information to make operational decisions for multi-minute or multi-hour parser jobs.
