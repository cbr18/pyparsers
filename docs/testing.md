# Testing Reference

## Split Parser Smoke Test

The parser layer is split into two services:

- `pyparsers-dongchedi` on `http://localhost:5001`
- `pyparsers-che168` on `http://localhost:5002`

The main live smoke test is [`tests/integration/test_source_services.py`](../tests/integration/test_source_services.py).

It verifies:

- blocked probe endpoint for each source
- dongchedi list parsing
- dongchedi detailed parsing for two cars
- che168 list parsing
- che168 detailed parsing for two cars when the upstream source responds
- presence of image data in parsed responses

## Run the Smoke Test

```bash
python tests/integration/test_source_services.py
```

Expected behavior:

- `GET /blocked/{source}` runs a short live probe: page 1 list + one detailed car
- `blocked=0` means the probe completed and the source looks available from the current IP
- `blocked=1` means the source likely blocks or degrades requests from the current IP, or the probe could not complete
- dongchedi should pass on live data
- che168 may be skipped when the external site times out or triggers anti-bot protection
- a non-zero exit code indicates a local regression

## Manual Checks

```bash
curl -s http://localhost:5001/health
curl -s http://localhost:5002/health
curl -s http://localhost:5001/blocked/dongchedi
curl -s http://localhost:5002/blocked/che168
curl -s http://localhost:5001/cars/dongchedi/page/1
curl -s http://localhost:5002/cars/che168/page/1
curl -s -X POST http://localhost:5002/che168/detailed/parse \
  -H "Content-Type: application/json" \
  -d '{"car_id":56481576,"force_update":true}'
```

## Notes

- blocked endpoints are public like `/health`, so external monitoring can call them without adding the monitor IP to `ALLOWED_IPS`
- the response includes `checks.list`, `checks.detailed`, and probe details for quick diagnostics
- `che168` remains externally unstable; timeouts there are not automatically a local bug.
- The smoke test is stdlib-only, so it can run without setting up a separate pytest environment on the host.
