# Testing Reference

## Che168 Enhancement Validation (Acceptance Snapshot)

Latest compose test (see former `TESTING_REPORT.md`) covered:

- ✅ **Docker build** – all containers built in ~2 minutes; fix for stray `package` typo already merged.
- ✅ **Enhancement API** – `https://localhost/enhancement/status` returned batch metrics for both sources (che168 + dongchedi).
- ✅ **Che168 parser API** – `POST /pyparsers/che168/detailed/parse` with `{"car_id":56481576,"force_update":true}` returned full `domain.Car` payload.
- ✅ **Worker logs** – background enhancement worker processed mixed-source batches and logged `[n/m] Successfully enhanced car ...`.
- ✅ **Database** – rows updated with `has_details=true`, `last_detail_update=UTC timestamp`, detail counts matched expectations (20 che168 cars with details, 20 without before worker caught up).
- ⚠️ **Known gaps** – some che168 fields (power, gallery) still depend on site variability; monitor logs for “Invalid power value” warnings.

Use these commands when you need to re-run the smoke suite:
```bash
curl -k -s https://localhost/enhancement/status | jq .
curl -k -s -X POST https://localhost/pyparsers/che168/detailed/parse \
  -H "Content-Type: application/json" \
  -d '{"car_id":56481576,"force_update":true}'
docker compose logs datahub --tail=50 | grep -i "enhanced\\|error"
```

## PyParsers Unit Tests

### Install dev dependencies
```bash
cd pyparsers
pip install -e ".[dev]"
```

### Run all tests
```bash
cd pyparsers
pytest tests/unit -v
```

### Focused test / coverage
```bash
pytest tests/unit/test_dongchedi_parser.py -v
pytest tests/unit -v --cov=api
pytest tests/unit --cov=api --cov-report=html   # generates htmlcov/
```

Notes:
- HTTP interactions are mocked with `responses`, so no real network access occurs.
- FastAPI routes use `TestClient`.
- Keep an eye on `tests/unit/test_memory_optimization_integration.py` whenever you tweak the async parser or `MemoryOptimizedList`.

