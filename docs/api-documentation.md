# Parser API Reference

Current local setup exposes two direct parser services:

- `pyparsers-dongchedi` on `http://localhost:5001`
- `pyparsers-che168` on `http://localhost:5002`

There is no shared nginx entrypoint in the current parser stack. Use the service ports directly.

## Common Endpoints

Both services expose:

- `GET /`
- `GET /health`
- `GET /blocked`
- `GET /cars`
- `GET /cars/page/{page}`
- `GET /cars/all`
- `POST /cars/incremental`
- `GET /docs`
- `GET /openapi.json`

`/blocked` is public like `/health`. The list/detail endpoints still respect `ALLOWED_IPS`.

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

### `GET /blocked`

Runs a short live probe:

1. Parse `page 1` through the normal list endpoint code path.
2. Pick one candidate from that page.
3. Parse one detailed car through the normal detailed endpoint code path.

Response shape:

```json
{
  "data": {
    "source": "dongchedi",
    "blocked": 0,
    "checks": {
      "list": 1,
      "detailed": 1
    },
    "details": {
      "list_count": 66,
      "probe_car_id": "39813",
      "detail_status": 200
    }
  },
  "message": "Source availability probe completed",
  "status": 200
}
```

Interpretation:

- `blocked=0` means the same list+detailed flow used by the public API succeeded.
- `blocked=1` means one of those two stages failed.

### `GET /cars/page/{page}`

Returns page-scoped list data:

```json
{
  "data": {
    "has_more": true,
    "search_sh_sku_info_list": [],
    "total": 1234,
    "current_page": 1
  },
  "message": "success",
  "status": 0
}
```

### `GET /cars/car/{car_id}`

Returns one detailed dongchedi car:

```json
{
  "data": {
    "car_id": 39813,
    "source": "dongchedi",
    "image": "https://...",
    "image_gallery": ["https://..."]
  },
  "message": "Success",
  "status": 200
}
```

## Che168 Service

Base URL: `http://localhost:5002`

Additional endpoints:

- `POST /cars/car`
- `POST /detailed/parse`
- `POST /detailed/parse-batch`
- `GET /detailed/health`
- `GET /update/full`

### `GET /blocked`

Works the same way as dongchedi, but uses:

1. `GET /cars/page/1`
2. `POST /detailed/parse`

Response shape:

```json
{
  "data": {
    "source": "che168",
    "blocked": 0,
    "checks": {
      "list": 1,
      "detailed": 1
    },
    "details": {
      "list_count": 56,
      "probe_car_id": "57885738",
      "probe_shop_id": "629891"
    }
  },
  "message": "Source availability probe completed",
  "status": 200
}
```

### `POST /detailed/parse`

Request:

```json
{
  "car_id": 57885738,
  "shop_id": 629891,
  "force_update": false
}
```

Successful response:

```json
{
  "success": true,
  "car_id": 57885738,
  "data": {
    "image": "https://...",
    "image_gallery": ["https://..."]
  },
  "is_banned": false
}
```

## Runtime Specs

The authoritative Swagger/OpenAPI documents are served by each running service:

- `http://localhost:5001/openapi.json`
- `http://localhost:5002/openapi.json`

Repository snapshots for these specs are stored in:

- [`OpenApi/dongchedi.json`](../OpenApi/dongchedi.json)
- [`OpenApi/che168.json`](../OpenApi/che168.json)
