# Parser API Examples

## Health

```bash
curl http://localhost:5001/health
curl http://localhost:5002/health
```

## Blocked Probe

```bash
curl http://localhost:5001/blocked
curl http://localhost:5002/blocked
```

## Dongchedi Parsing

```bash
curl http://localhost:5001/cars/page/1
curl http://localhost:5001/cars/all
curl http://localhost:5001/cars/car/39813
curl -X POST http://localhost:5001/cars/cars \
  -H "Content-Type: application/json" \
  -d '{"car_ids":["39813","39814"]}'
```

## Che168 Parsing

```bash
curl http://localhost:5002/cars/page/1
curl http://localhost:5002/cars/all
curl -X POST http://localhost:5002/cars/car \
  -H "Content-Type: application/json" \
  -d '{"car_url":"https://m.che168.com/cardetail/index?infoid=57885738"}'
curl -X POST http://localhost:5002/detailed/parse \
  -H "Content-Type: application/json" \
  -d '{"car_id":57885738,"shop_id":629891,"force_update":false}'
```

## Create Parser Tasks

Dongchedi incremental:

```bash
curl -X POST http://localhost:5001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "incremental",
    "parameters": {
      "id_field": "car_id",
      "existing_ids": ["87014"]
    },
    "metadata": {
      "requested_by": "datahub"
    }
  }'
```

Dongchedi detailed:

```bash
curl -X POST http://localhost:5001/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "detailed",
    "parameters": {
      "car_ids": ["39813","39814"]
    }
  }'
```

Che168 detailed:

```bash
curl -X POST http://localhost:5002/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "detailed",
    "parameters": {
      "requests": [
        {"car_id": 57885738, "shop_id": 629891, "force_update": false}
      ]
    }
  }'
```

## Poll Task Status

```bash
curl http://localhost:5001/tasks
curl http://localhost:5001/tasks/<task_id>
curl http://localhost:5001/tasks/<task_id>/result
curl -X POST http://localhost:5001/tasks/<task_id>/cancel
```
