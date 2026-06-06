# Optimize che168 fallback concurrency and logging

Status: DONE
Created: 2026-06-06 09:54
Project: pyparsers
Plan: [06_06_2026_09_54_optimize_che168_ban_handling.md](../plans/06_06_2026_09_54_optimize_che168_ban_handling.md)

## Problem

When `che168` detail API is frequency-capped, the parser falls back to Selenium. Current logs show the same `car_id` can be parsed several times almost simultaneously, which can launch duplicate API and browser fallback work. This increases load, makes logs harder to interpret, and can create avoidable Chromium pressure while the source is already brittle.

This task is scoped to reducing duplicate `car_id` work, bounding Selenium fallback concurrency, improving observability, and replacing the synthetic per-car API `deviceid` with a more realistic per-session value. It does not change the API-ban/cooldown algorithm itself.

## Evidence

Production logs on 2026-06-05 showed:

- Listing API succeeded: `Страница 1: получено 7 автомобилей через signed API`.
- Detail API returned frequency-cap responses:
  - `getparamtypeitems вернул 514 для car_id=57021858 - API заблокирован`
  - `getcarinfo вернул 514 для car_id=57021858 - API заблокирован`
- The parser then used HTML fallback:
  - `Desktop selenium начинаем`
  - `Desktop fallback: УСПЕХ 67 изображений`
  - `Источник заблокирован для car_id=57021858, но fallback успешно получил критичные данные`
- The same `car_id=57021858` started multiple detail parses within seconds:
  - `23:49:14`
  - `23:49:16`
  - `23:49:20`
  - `23:49:28`

Code paths involved:

- `pyparsers/api/che168/detailed_api.py`
  - batch detail endpoint
  - `CHE168_BATCH_MAX_CONCURRENT`
  - `asyncio.Semaphore(CHE168_BATCH_MAX_CONCURRENT)`
- `pyparsers/api/che168/detailed_parser_api.py`
  - `_fetch_images_desktop`
  - `_fetch_images_fallback`
  - `_create_chrome_driver`
  - detail API request params/headers
  - existing `403`/`514` handling and HTML fallback paths

## Non-Functional Constraints

- Preserve the existing request and response contracts for che168 detail endpoints.
- Preserve fallback behavior: when API is capped, HTML/Selenium fallback should still retrieve critical fields where possible.
- Preserve push-batch delivery compatibility with DataHub.
- Avoid increasing persistent disk usage in container writable layers.
- Keep Chromium runtime data constrained by existing tmpfs/runtime storage protections.
- Do not introduce secrets, proxy credentials, or hardcoded tokens.
- Do not change unrelated sources (`dongchedi`, `encar`, `wyautoexport`) in this task.

## Out Of Scope

- Changing the che168 API cooldown algorithm.
- Changing `CHE168_BATCH_MAX_CONCURRENT` defaults as part of this task.
- Changing API signatures, cookies, or broader anti-ban strategy beyond the per-session `deviceid` and request header cleanup described here.
- Adding paid proxy or captcha-solving services.
- Rewriting task orchestration or batch delivery.
- Refactoring unrelated parser sources.
- Changing migrations, generated artifacts, lock files, compose files, or secrets.
- Removing Selenium fallback entirely.

## Desired Behavior

`che168` detail parsing should avoid duplicate concurrent work for the same car and keep browser fallback load bounded and observable.

Expected behavior:

- Duplicate detail work for the same `car_id` is avoided or coalesced within a short active window.
- Selenium/Chromium fallback concurrency is bounded by a che168-specific limit separate from overall batch concurrency.
- Detail API requests use a stable per-parser-session mobile-like `deviceid` instead of `api_parser_{car_id}`.
- Detail API requests send mobile-page referers matching the requested `car_id`.
- Logs clearly show:
  - when a `car_id` joins/reuses existing active work;
  - when Selenium fallback waits for a fallback concurrency slot;
  - when Selenium fallback starts and finishes;
  - whether fallback succeeded or failed.

## Affected Areas

- `pyparsers/api/che168/detailed_api.py`
- `pyparsers/api/che168/detailed_parser_api.py`
- `tests/unit/test_che168_parser.py` or new focused unit tests under `tests/unit/`
- Runtime configuration for any new che168-specific fallback concurrency environment variable
- Documentation or operational notes if a new env variable is introduced

## Implementation Notes

Recommended approach:

- Add a small in-process active-work registry keyed by `car_id` to prevent simultaneous duplicate detail parses for the same car.
- Add a separate Selenium fallback semaphore so browser work is not limited only by overall batch concurrency.
- Make the fallback semaphore limit env-configurable.
- Generate one opaque mobile-like `deviceid` per `Che168DetailedParserAPI` instance and reuse it for both detail API endpoints.
- Keep API params compatible: `infoid`, `deviceid`, `_appid`.
- Use per-car mobile detail referer headers for detail API calls.
- Keep the fallback path available because production evidence shows it can still retrieve images, mileage, and power while the API is capped.
- Add structured, concise logs for duplicate/coalesced work and fallback slot acquisition/release.

Known pitfalls:

- Coalescing must handle exceptions so one failing parse does not permanently poison the active-work registry.
- Coalescing should not leak tasks/futures after completion.
- Too strict fallback concurrency can slow batch completion during long API cap windows.
- Too loose fallback concurrency can overload Chromium memory/tmpfs.
- Browser fallback may be called from more than one method; the concurrency limit should cover all Selenium fallback entry points in che168 detail parsing.

## Acceptance Criteria

- Duplicate concurrent parses for the same `car_id` are coalesced or otherwise prevented.
- Selenium fallback concurrency is bounded by a che168-specific limit.
- `deviceid` no longer uses the synthetic `api_parser_{car_id}` format.
- One parser instance uses the same generated `deviceid` across che168 detail API calls.
- Detail API requests include a per-car mobile detail referer.
- The new fallback concurrency limit is env-configurable and documented.
- Logs distinguish duplicate/coalesced work, fallback waiting, fallback start, fallback success, and fallback failure.
- Existing successful fallback behavior remains intact.
- Existing detail response shape and `is_banned` semantics remain compatible.
- Unit tests cover duplicate work handling and fallback concurrency limiting.

## Test Plan

- Add a focused concurrency/deduplication test:
  - simultaneous requests for the same `car_id` do not launch duplicate parse/fallback work.
- Add a fallback concurrency test:
  - more concurrent fallback attempts than the configured limit are serialized by the che168 fallback semaphore.
- Add a detail API request-shape test:
  - generated `deviceid` is not `api_parser_{car_id}`;
  - generated `deviceid` is stable within one parser instance.
- Add a cleanup test if active-work registry futures/tasks are introduced:
  - completed or failed work is removed from the registry.
- Run:
  - `python -m pytest tests/unit`
  - `python tests/integration/test_source_services.py` when source containers are available
  - `bash ./scripts/health-check.sh` for Docker/runtime verification
- Manually verify production-like logs after deployment:
  - duplicate `car_id` requests are coalesced;
  - Selenium fallback concurrency remains bounded;
  - container writable layer remains small in `docker system df -v`.

## Rollback

Revert the che168 deduplication, fallback semaphore, and logging changes. If fallback throughput becomes too low, temporarily increase the che168 fallback concurrency env value.
