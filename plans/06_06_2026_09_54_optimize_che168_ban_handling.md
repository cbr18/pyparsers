# Plan: Optimize che168 fallback concurrency and logging

Task: [06_06_2026_09_54_optimize_che168_ban_handling.md](../tasks/06_06_2026_09_54_optimize_che168_ban_handling.md)
Status: DONE

## Goal

Prevent duplicate concurrent che168 detail work for the same `car_id`, bound Selenium fallback concurrency separately from overall batch concurrency, make fallback behavior clear in logs, and replace the synthetic per-car API `deviceid`.

## Sequence

1. Add che168-specific duplicate in-flight protection keyed by `car_id`, or another narrow coalescing strategy that prevents duplicate concurrent detail parses.
2. Add a separate Selenium fallback concurrency limit for che168 browser fallback work.
3. Replace `deviceid=api_parser_{car_id}` with a stable opaque per-parser-session mobile-like device id and send per-car mobile detail referer headers.
4. Improve logs around coalesced duplicate work, fallback slot waiting/acquisition, fallback start, fallback success, and fallback failure.
5. Add focused unit tests for duplicate work handling, fallback concurrency limiting, and detail API request shape.
6. Run focused unit tests, then broader unit tests.
7. Run live smoke checks when source containers are available.
8. Deploy and observe repeated `car_id` requests, Selenium session count, tmpfs usage, Docker writable layer size, and `514` frequency.

## Validation

- Concurrent requests for the same `car_id` do not launch repeated API and Selenium work.
- Selenium fallback concurrency is bounded by the configured che168-specific limit.
- Detail API `deviceid` is no longer synthetic per-car `api_parser_{car_id}`.
- Detail API calls include mobile detail referers for the requested car.
- Selenium fallback still retrieves critical data when the API is capped.
- Logs clearly show whether detail work was started, coalesced, waiting for fallback capacity, completed through fallback, or failed.
- `docker system df -v` does not show `carcatch-pyparsers-che168` writable layer growth under normal fallback load.
- tmpfs mounts remain bounded and visible in `docker inspect`.

## Risks

- Coalescing active work incorrectly could return stale or incomplete data if one parse fails.
- Active-work registry cleanup bugs could leak futures/tasks.
- Too strict fallback concurrency could slow batch completion during long API cap windows.
- Too loose fallback concurrency can still overload Chromium memory/tmpfs.
- Changing request identity can affect che168 API acceptance and should be monitored after deployment.

## Rollback

Revert the che168 duplicate-work protection, fallback concurrency limit, device id/header changes, and logging changes. If only throughput is affected, raise the new che168 fallback concurrency env value while keeping duplicate-work protection in place.
