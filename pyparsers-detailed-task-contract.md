# Detailed Task Contract

This file describes the final unified `detailed` task contract between `datahub` and `pyparsers`.

## Goal

`detailed` parser jobs must use one request shape for every source.

Only the meaning of identifiers may differ by source.

## Unified Task Request

`datahub` creates parser tasks with:

```json
{
  "task_type": "detailed",
  "parameters": {
    "items": [
      {
        "external_id": "39813",
        "secondary_id": "optional",
        "force_update": true
      }
    ]
  },
  "metadata": {
    "requested_by": "datahub",
    "upstream_task_id": "..."
  }
}
```

## Field Semantics

- `external_id`
  - primary source-specific identifier used to fetch detailed data
- `secondary_id`
  - optional extra identifier
  - required only for sources that cannot fetch details by one id
- `force_update`
  - optional boolean
  - default: `false`

## Source Mapping

### Dongchedi

- `external_id` -> parser detail lookup id (`sku_id` / direct parser detail id)
- `secondary_id` -> optional extra identifier for diagnostics or persistence

### Che168

- `external_id` -> `car_id`
- `secondary_id` -> `shop_id`

## What Must Stay Unified

- `POST /tasks`
- `task_type = detailed`
- `parameters.items[]`
- task snapshot fields:
  - `status`
  - `stage`
  - `heartbeat_at`
  - `progress_current`
  - `progress_total`
  - `progress_unit`
  - `items_found`
  - `items_processed`
  - `items_sent`
  - `result_available`

## What May Stay Source-Specific

- how `external_id` and `secondary_id` are interpreted internally
- detailed parsing implementation
- detailed result internals before `datahub` persistence merge

## Responsibility Split

### `pyparsers`

- validate `parameters.items`
- interpret source-specific identifiers
- parse source responses
- map source data into canonical car payloads
- expose task execution state

### `datahub`

- create parser tasks
- poll parser tasks
- decide retries / timeout / cancellation
- merge detailed payload into existing cars
- translate / enrich / price-calculate
- persist final state and final result

## Current Expectation

Any new source added to `pyparsers` should support the same `detailed` envelope:

```json
{
  "task_type": "detailed",
  "parameters": {
    "items": [...]
  }
}
```

Only the internal mapping of `items[*]` to source identifiers should vary.
