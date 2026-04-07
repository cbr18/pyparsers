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

## Dongchedi

List page 1:

```bash
curl http://localhost:5001/cars/page/1
```

All cars:

```bash
curl http://localhost:5001/cars/all
```

Incremental parse:

```bash
curl -X POST http://localhost:5001/cars/incremental \
  -H "Content-Type: application/json" \
  -d '[{"car_id":39813}]'
```

One detailed car:

```bash
curl http://localhost:5001/cars/car/39813
```

Batch detailed fetch:

```bash
curl -X POST http://localhost:5001/cars/cars \
  -H "Content-Type: application/json" \
  -d '{"car_ids":["39813","39814"]}'
```

Stats:

```bash
curl http://localhost:5001/cars/stats
```

## Che168

List page 1:

```bash
curl http://localhost:5002/cars/page/1
```

All cars:

```bash
curl http://localhost:5002/cars/all
```

Incremental parse:

```bash
curl -X POST http://localhost:5002/cars/incremental \
  -H "Content-Type: application/json" \
  -d '[{"car_id":57885738}]'
```

Legacy URL-based detail endpoint for che168 service:

```bash
curl -X POST http://localhost:5002/cars/car \
  -H "Content-Type: application/json" \
  -d '{"car_url":"https://m.che168.com/cardetail/index?infoid=57885738"}'
```

Structured detailed parse:

```bash
curl -X POST http://localhost:5002/detailed/parse \
  -H "Content-Type: application/json" \
  -d '{"car_id":57885738,"shop_id":629891,"force_update":false}'
```

Batch detailed parse:

```bash
curl -X POST http://localhost:5002/detailed/parse-batch \
  -H "Content-Type: application/json" \
  -d '{"requests":[{"car_id":57885738,"shop_id":629891,"force_update":false}]}'
```

Detailed parser health:

```bash
curl http://localhost:5002/detailed/health
```
