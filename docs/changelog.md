# Changelog

This timeline highlights the parser/enhancement milestones that previously lived in multiple summary files.

## 2025‑11‑15 — Che168 detail parser overhaul
- Added resilient label matching (no reliance on `css-1rynq56`) and expanded the mapping to 110+ technical fields.
- Normalized complex values: `长×宽×高`, `万公里` mileage, registration year inference, gallery extraction via `head_images[]`.
- Updated `_convert_to_domain_car` so every parsed field maps 1:1 to the Go `domain.Car` struct.
- Verified via docker-compose acceptance test: `/enhancement/status`, `http://localhost:5002/che168/detailed/parse`, and DB counters.

## 2025‑10 — Automatic enhancement worker & infrastructure cleanup
- Replaced bespoke Che168 detail services with the same `EnhancementService`/`EnhancementWorker` stack used by dongchedi.
- Introduced `has_details`, `last_detail_update`, image gallery, dealer metadata, comfort/safety fields (60+ DB columns).
- Added `000009_*` and `000010_*` migrations with partial `(source, car_id)` index to avoid duplicate-key conflicts.
- Worker now auto-starts with datahub, respects configurable batch/parallelism, and exposes `/enhancement/*` control endpoints.
- Cron-based ingestion plus the worker ensures the DB eventually becomes fully enriched after `docker compose up`.

## 2025‑09 — Reliability tooling
- Hardened HTTP client to use a shared resource manager, retry strategy, and circuit breaker.
- Added structured logging + error categorisation for parser and worker code paths.
- Documented testing strategy (`pytest tests/unit`, coverage flags, CI-friendly commands).
