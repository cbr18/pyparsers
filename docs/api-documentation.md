# Parser API Reference

The parser layer is split into direct per-source services:

- `pyparsers-dongchedi` on `http://localhost:5001`
- `pyparsers-che168` on `http://localhost:5002`
- `pyparsers-encar` on `http://localhost:5003`

There is no shared nginx entrypoint for the parser contract. Use these service ports directly.

## Common Endpoints

All parser services expose:

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
- `items_sent`: in pull-result mode, set when the final result payload is ready; in `delivery_mode=push_batches`, increments as listing batches are accepted by the configured batch endpoint
- `result_available`: `true` only after terminal success

For large `full` or production `incremental` jobs, prefer `POST /tasks` with `parameters.delivery_mode="push_batches"`. This mode is supported by all listing parsers: `dongchedi`, `che168`, and `encar`. The parser sends rows to `parameters.batch_endpoint` while running, then stores an empty final task result with delivery counters in `result_summary`.

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
- `GET /update/full` exists for route compatibility, but returns `status="unsupported"` for Encar. Use `POST /tasks` for managed `full`/`incremental` runs.
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

## Encar Service

Base URL: `http://localhost:5003`

Encar is fully independent from the other parser containers. It reuses the same Docker image and shared API/task framework, but it has no runtime `depends_on` relationship with `pyparsers-dongchedi` or `pyparsers-che168`.

Source access:

- listing API: `http://api.encar.com/search/car/list/premium`
- detail API: `http://api.encar.com/v1/readside/vehicle/{car_id}`

No Selenium or Playwright browser flow is used for Encar; the parser reads JSON APIs directly with `requests`.

Additional endpoints:

- `GET /cars/car/{car_id}`

### Response Shape

The response envelope is the same as the other parser list endpoints:

```json
{
  "data": {
    "has_more": true,
    "search_sh_sku_info_list": [],
    "total": 161701
  },
  "message": "Success",
  "status": 200
}
```

`search_sh_sku_info_list[]` uses the same broad car payload shape as the existing sources, with `source="encar"`.

### Parsed Fields

List parsing fills the primary listing fields:

- IDs and routing: `car_id`, `sku_id`, `uuid`, `source`, `link`
- title and catalog: `title`, `car_name`, `brand_name`, `series_name`, `car_year`, `year`, `first_registration_time`
- price and usage: `sh_price`, `price`, `car_mileage`, `mileage`
- media: `image`, `image_gallery`, `image_count`
- location and sale metadata: `city`, `car_source_city_name`, `dealer_info`, `tags`, `tags_v2`, `condition`, `certification`, `is_available`, `sort_number`
- basic specs: `transmission`, `fuel_type`

Detailed parsing adds or improves:

- catalog IDs: `brand_id`, `series_id`, `shop_id`
- full gallery from `photos[]`
- `description`
- `color`, `exterior_color`
- `engine_volume_ml`, `body_type`, `seat_count`
- `view_count`, `favorite_count`
- `contact_info`, expanded `dealer_info`, `warranty_info`

### Task Types

- `full`
  - no required parameters
- `incremental`
  - `parameters.id_field` default: `car_id`
  - `parameters.existing_ids` list
- `detailed`
  - `parameters.items` list of:
    - `external_id` (`car_id` from Encar)
    - optional `secondary_id`
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
- `http://localhost:5003/openapi.json`
- `http://localhost:5002/openapi.json`

Repository snapshots:

- [`OpenApi/dongchedi.json`](../OpenApi/dongchedi.json)
- [`OpenApi/che168.json`](../OpenApi/che168.json)
