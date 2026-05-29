# Plan: Fix sort_number for listing batches

Task: [28_05_2026_21_11_edit_sortnumber_for_batches.md](../tasks/28_05_2026_21_11_edit_sortnumber_for_batches.md)
Status: IN WORK

## Goal

Make `sort_number` represent source-level listing order for task/result and task/push-batch flows, instead of resetting the value on every parsed page.

## Sequence

1. Add unit coverage that reproduces the bug with two pages per source.
2. Refactor listing ranking in `task_service.py` so each listing task uses one source-level rank sequence.
3. Apply the same rank semantics to `dongchedi`, `che168`, and `encar`.
4. Verify push-batch delivery does not flush rows before their final rank is known, or switch to a rank formula that is correct before flushing.
5. Update parser/DataHub contract notes to define `sort_number` as source-level listing rank.
6. Run focused unit tests, then integration smoke checks if source containers are available.
7. Verify repeated incremental runs do not add `1_000_000` layers above `max_sort_number`.

## Validation

- Page 1 ranks higher than page 2 for every source.
- Within each page, earlier source rows rank higher than later source rows.
- Incremental tasks preserve stop-on-existing behavior.
- Push-batch and result modes produce equivalent ordering semantics.

## Risks

- Buffering rows until final ranking may increase memory usage for full tasks.
- Using a large task-local base avoids buffering but does not make ranks monotonic across historical runs unless DataHub passes `max_sort_number`.
- Changing rank semantics may require a one-time DataHub data refresh or re-ingest to fix existing rows.

## Rollback

Revert the ranking changes in `task_service.py` and associated tests/docs.
