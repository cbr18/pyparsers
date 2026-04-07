# Parser API Reference

The parser layer is split into two direct services:

- `pyparsers-dongchedi` on `http://localhost:5001`
- `pyparsers-che168` on `http://localhost:5002`

There is no shared nginx entrypoint for the parser contract. Use these service ports directly.

## Common Endpoints

Both services expose:

- `GET /`
- `GET /health`
- `GET /blocked`
- `GET /cars`
- `GET /cars/page/{page}`
- `GET /cars/all`
- `POST /cars/incremental`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`
- `GET /tasks/{task_id}/result`
- `POST /tasks/{task_id}/cancel`
- `GET /docs`
- `GET /openapi.json`

`/blocked` is public like `/health`. Task and parsing endpoints still respect `ALLOWED_IPS`.

## Task Contract

Tasks are now parser-side execution jobs with a unified lifecycle.

### Statuses

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

### Stages

- `queued`
- `initializing`
- `listing`
- `detailed`
- `finalizing`
- `completed`
- `failed`
- `cancelled`

### `POST /tasks`

Request:

```json
{
  "task_type": "incremental",
  "parameters": {
    "id_field": "car_id",
    "existing_ids": ["87014"]
  },
  "metadata": {
    "requested_by": "datahub"
  }
}
```

Response:

```json
{
  "data": {
    "id": "e1b918c2-60d0-4f84-98e1-15dc7d1d0539",
    "source": "dongchedi",
    "task_type": "incremental",
    "status": "queued",
    "stage": "queued",
    "message": "Task is queued"
  },
  "message": "Task created",
  "status": 202
}
```

### `GET /tasks/{task_id}`

Returns the current execution snapshot:

```json
{
  "data": {
    "id": "e1b918c2-60d0-4f84-98e1-15dc7d1d0539",
    "source": "dongchedi",
    "task_type": "incremental",
    "status": "running",
    "stage": "listing",
    "message": "Parsed dongchedi page 1",
    "progress_current": 1,
    "progress_total": 100,
    "progress_unit": "page",
    "items_found": 42,
    "items_processed": 0,
    "items_sent": 0,
    "cancel_requested": false,
    "result_available": false,
    "heartbeat_at": "2026-04-07T02:41:45.950928Z"
  },
  "message": "Task fetched",
  "status": 200
}
```

Important fields:

- `heartbeat_at`: parser-side liveness signal for long jobs
- `progress_current` / `progress_total` / `progress_unit`: shared progress model for `full`, `incremental`, and `detailed`
- `items_found`: how many items are already collected
- `items_processed`: useful for `detailed` jobs
- `items_sent`: set when the final result payload is ready
- `result_available`: `true` only after terminal success

### `GET /tasks/{task_id}/result`

Returns the full result payload after success:

```json
{
  "data": {
    "task": {
      "id": "e1b918c2-60d0-4f84-98e1-15dc7d1d0539",
      "status": "succeeded",
      "stage": "completed",
      "result_available": true
    },
    "result": []
  },
  "message": "Task result fetched",
  "status": 200
}
```

### `POST /tasks/{task_id}/cancel`

Requests cooperative cancellation.

- queued jobs become `cancelled` immediately
- running jobs set `cancel_requested=true` and stop on the next safe checkpoint

## Dongchedi Service

Base URL: `http://localhost:5001`

Additional endpoints:

- `GET /cars/car/{car_id}`
- `POST /cars/cars`
- `GET /cars/stats`
- `GET /cars/enhance/{sku_id}`
- `GET /cars/specs/{car_id}`
- `POST /cars/batch-enhance`
- `GET /update/full`

### Task Types

- `full`
  - no required parameters
- `incremental`
  - `parameters.id_field` default: `sku_id`
  - `parameters.existing_ids` list
- `detailed`
  - `parameters.items` list of:
    - `external_id`
    - optional `secondary_id`
    - optional `force_update`

## Che168 Service

Base URL: `http://localhost:5002`

Additional endpoints:

- `POST /cars/car`
- `POST /detailed/parse`
- `POST /detailed/parse-batch`
- `GET /detailed/health`
- `GET /update/full`

### Task Types

- `full`
  - no required parameters
- `incremental`
  - `parameters.id_field` default: `car_id`
  - `parameters.existing_ids` list
- `detailed`
  - `parameters.items` list of:
    - `external_id`
    - `secondary_id`
    - optional `force_update`

## Blocked Probe

`GET /blocked` runs:

1. real list parsing for page 1
2. one real detailed parse for a candidate from that page

Interpretation:

- `blocked=0` means the same public list+detailed flow succeeded
- `blocked=1` means one of those stages failed

## Runtime Specs

The authoritative OpenAPI documents are served by the running services:

- `http://localhost:5001/openapi.json`
- `http://localhost:5002/openapi.json`

Repository snapshots:

- [`OpenApi/dongchedi.json`](../OpenApi/dongchedi.json)
- [`OpenApi/che168.json`](../OpenApi/che168.json)
