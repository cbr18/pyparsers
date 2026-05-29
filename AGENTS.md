# Repository Instructions

## Project Shape

`pyparsers` is the Python parser layer for CarCatch.

- One FastAPI app per source: `dongchedi`, `che168`, `encar`, `wyautoexport`.
- Thin entrypoints live in `app_*.py`.
- Shared orchestration lives in `async_api_server.py`, `source_apps.py`, and `task_service.py`.
- Parser implementations and adapters live under `pyparsers/api/`.
- Live smoke checks and unit tests live under `tests/`.
- Docker is the normal runtime path for local and integration work.

## Work Rules

- Do not write code unless the user explicitly asks for code changes.
- If requirements are unclear, ask before implementing.
- Keep one task or one PR to one change. Do not bundle unrelated refactors.
- Do not change migrations, generated artifacts, lock files, compose files, or secrets unless the user explicitly asks.
- Do not hardcode secrets or tokens. Use the existing `.env` / `env_file` pattern.
- Answer concisely and do only what was explicitly requested. Do not expand scope without approval.
- When changing an existing flow, preserve its documented non-functional properties unless the task explicitly changes them.
- When changing code, keep related documentation and contract notes up to date in the same task.

## Tasks And Plans

- Project tasks for this repository live in `tasks/`.
- Project plans for this repository live in `plans/`.
- Keep task and plan files scoped to this repository. Do not link this repository's task workflow to sibling project task folders.
- Name task and plan files as `DD_MM_YYYY_HH_MM_description.md` unless the user requests a different exact name.
- Create new task files from `tasks/blank.md` and fill every relevant section instead of inventing a new task format.
- Every task file must include a `Plan` link to the related file in `plans/` when a plan exists.
- Every plan file must include a `Task` link back to the related file in `tasks/`.
- Every task file must include a top-level status line in the form `Status: CREATED`, `Status: IN WORK`, `Status: DONE`, or `Status: REJECTED`.
- Keep task status inside the file, not in the filename, so links remain stable when status changes.
- Task files should describe the problem, evidence, desired behavior, affected areas, implementation notes, acceptance criteria, and test plan.
- Plan files should describe the intended implementation sequence, validation steps, risks, and rollback notes.

## Environment

- Python: `3.13` as declared in `pyparsers/pyproject.toml`.
- Runtime: FastAPI + Granian + aiohttp/requests.
- Docker Compose is the supported local stack.

## Code Style

- Follow the existing Python style in the repo.
- Keep edits small and consistent with nearby code.
- Do not introduce new formatting or linting tooling unless the user asks for it.

## Testing

- Any logic change must be tested.
- New features must include tests.
- Use focused unit tests first:
  - `python -m pytest tests/unit`
- For endpoint or runtime changes, also run the live smoke test:
  - `python tests/integration/test_source_services.py`
- For Docker/runtime changes, verify the stack with:
  - `bash ./scripts/health-check.sh`

## Operational Notes

- `che168` is more brittle than the other sources; timeouts and blocked probes there are not always local regressions.
- Push-batch delivery to DataHub is part of the contract; keep request/response shapes compatible.
- Prefer existing contracts and helpers over inventing new abstractions.
