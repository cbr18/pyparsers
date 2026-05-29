# Fix sort_number for listing batches

Status: FAILED
Created: 2026-05-28 21:11
Project: pyparsers
Plan: [28_05_2026_21_11_edit_sortnumber_for_batches.md](../plans/28_05_2026_21_11_edit_sortnumber_for_batches.md)

## Problem

`sort_number` is intended to preserve source listing order so DataHub can show cars in the same freshness/order as the marketplace. DataHub currently sorts the default catalog by `has_details DESC NULLS LAST, sort_number DESC, updated_at DESC`.

The current task/push-batch flow in pyparsers assigns `sort_number` as a page-local position:

- `dongchedi`: `sort_number = total_filtered - index`
- `che168`: `_normalize_che168_listing_car(..., index, total)` sets `sort_number = total - index`
- `encar`: `_normalize_encar_listing_car(..., index, total)` sets `sort_number = total - index`

Because this value resets on every parsed page, DataHub cannot distinguish page 1 from page 2 by `sort_number`. A car from page 2 can receive a larger `sort_number` than a car from page 1. This breaks the default listing order and can keep old cars at the top.

## Evidence

Observed live local parser responses:

- `dongchedi /cars/page/1` returned page-local `sort_number` values around `76..1`.
- `dongchedi /cars/page/2` returned page-local `sort_number` values around `80..1`.
- `che168 /cars/page/1` returned `10..1`.
- `che168 /cars/page/2` returned `9..1`.

Observed DataHub database distribution:

- `che168`: `sort_number` min `1`, max `10`
- `dongchedi`: `sort_number` min `1`, max `72`
- `encar`: `sort_number` min `1`, max `50`

That distribution matches per-page position, not source-level listing order.

## Non-Functional Constraints

Push-batch delivery was introduced to avoid collecting full parser results in memory and to preserve partial progress when long source scans fail late. This task must preserve those properties.

Do not fix `sort_number` by buffering the entire source inventory before sending batches unless that tradeoff is explicitly approved in a separate task decision.

Required constraints:

- Push-batch listing flows must keep streaming/partial-delivery behavior.
- A non-final batch must be emitted before the full source scan completes once the configured batch size is reached.
- Full tasks must not require all listing rows to be held until final ranking before the first batch can be sent.
- Any ranking formula must work at item emission time or use bounded state that does not defeat push-batch delivery.

## Desired Behavior

For listing tasks, `sort_number` must be a source-level rank, not a page-local rank.

Rules:

- Higher `sort_number` means higher/fresher in the source listing order.
- Page 1 items must rank above page 2 items.
- Within a page, earlier source items must rank above later source items.
- The rule must be consistent for `dongchedi`, `che168`, and `encar`.
- Push-batch mode and result mode must produce equivalent `sort_number` semantics.

## Affected Areas

- `pyparsers/task_service.py`
- Listing full/incremental runners for:
  - `dongchedi`
  - `che168`
  - `encar`
- Normalization helpers:
  - `_normalize_che168_listing_car`
  - `_normalize_encar_listing_car`
- Unit tests under `tests/unit/`
- Integration smoke behavior for parser page/task endpoints

## Implementation Notes

Do not compute `sort_number` independently per page.

Recommended approach:

- Accumulate normalized listing candidates in task order first, or track a global task-level listing index.
- Assign ranks from the final ordered list before returning/sending listings:
  - `sort_number = total_ranked_items - global_index` for full tasks.
  - For incremental tasks, use the same ordered list of newly found items. If DataHub provides `max_sort_number`, assign `max_sort_number + total_new_items - global_index`; otherwise use a large task-local base that keeps page order correct inside the task.
- Prefer passing `max_sort_number` from DataHub in task parameters if this needs to be monotonic across multiple incremental runs.
- Keep batch flushing compatible with the chosen ranking strategy. If ranks require knowing `total_new_items`, either buffer until ranks are assigned or use a monotonic base/rank strategy that is correct before flushing.

Important: DataHub batch payload currently has one `page` field per batch, not per item, so DataHub cannot reliably reconstruct item-level page order after receiving a mixed batch. The primary fix belongs in pyparsers.

## Acceptance Criteria

- `dongchedi`, `che168`, and `encar` task listing flows no longer reset `sort_number` on each page.
- For each source, all page 1 results rank above page 2 results when ordered by `sort_number DESC`.
- Push-batch mode and result mode preserve the same ordering semantics.
- Push-batch mode preserves streaming behavior and does not buffer the complete source inventory before sending the first non-final batch.
- Tests assert that a non-final batch is sent before the parser reaches the end of a multi-page scan.
- Incremental tests cover `max_sort_number` and assert that newly discovered rows rank above the previous maximum.
- Existing detail parsing behavior is unchanged.
- Existing source filters, duplicate handling, and stop-on-existing incremental behavior are preserved.
- Documentation or contract comments mention that `sort_number` is source-level listing rank, where higher means higher/fresher in the source order.

## Test Plan

- Add focused unit tests for task listing ranking:
  - multi-page `dongchedi` result has descending source-level ranks across pages;
  - multi-page `che168` result has descending source-level ranks across pages;
  - multi-page `encar` result has descending source-level ranks across pages;
  - incremental stop-on-existing still stops and ranks only new items.
- Run:
  - `python -m pytest tests/unit`
  - `python tests/integration/test_source_services.py` when source containers are available
  - `bash ./scripts/health-check.sh` for Docker/runtime verification when changing runtime behavior

## Rollback

Revert the task ranking changes in `task_service.py`. DataHub will return to current page-local `sort_number` behavior, which is known to produce incorrect default ordering.

## Failed Attempt Notes

An attempted implementation was rejected and rolled back.

What went wrong:

- The implementation expanded beyond the task scope and rewrote core `TaskService` lifecycle code instead of making a focused ranking change.
- It changed task orchestration semantics that were not part of this task: task state handling, result envelopes, cancellation behavior, worker implementation, and related internals.
- An intermediate version made `task_service.py` fail to import because it referenced task types that were not present in `models.py`.
- A later version still kept a large, risky `TaskService` rewrite and mixed the `sort_number` fix with adding a new source (`wyautoexport`), which should be a separate task.
- The first attempted ranking fix buffered full listing results before sending batches, which violated the push-batch non-functional requirement for streaming and partial delivery.

Required lesson for the next attempt:

- Keep the change narrow: do not rewrite `TaskService`.
- Do not change task lifecycle, task API shape, snapshots, result envelopes, cancellation, queue behavior, or endpoint contracts unless a separate task explicitly asks for that.
- Fix only listing rank assignment inside the existing full/incremental source runners and helper functions.
- Preserve push-batch streaming behavior: batches must still be emitted as they fill.
- Do not mix this task with adding new parser sources.
