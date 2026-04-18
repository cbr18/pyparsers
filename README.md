# CarCatch

CarCatch is a microservice platform that scrapes dongchedi.com, che168.com, and encar.com, enriches the data set, and exposes it through multiple APIs, bots, and web clients.

## Quick Start

```bash
git clone <repository>
cd CarsParser
cp pyparsers/env.example .env
docker compose up -d --build
./scripts/health-check.sh   # or .ps1
```

Useful URLs:
- Dongchedi parser: http://localhost:5001
- Che168 parser: http://localhost:5002
- Encar parser: http://localhost:5003
- Dongchedi docs: http://localhost:5001/docs
- Che168 docs: http://localhost:5002/docs
- Encar docs: http://localhost:5003/docs
- Dongchedi blocked probe: http://localhost:5001/blocked
- Che168 blocked probe: http://localhost:5002/blocked
- Encar blocked probe: http://localhost:5003/blocked
- Dongchedi tasks: http://localhost:5001/tasks
- Che168 tasks: http://localhost:5002/tasks
- Encar tasks: http://localhost:5003/tasks

## Documentation

All markdown guides now live in `docs/`.

- [`docs/README.md`](docs/README.md) – entry point + service map
- [`docs/operations.md`](docs/operations.md) – deployment, migrations, task API, backups
- [`docs/parsers.md`](docs/parsers.md) – parser pipeline, enhancement worker, HTTP client tooling
- [`docs/api-documentation.md`](docs/api-documentation.md) / [`docs/api-examples.md`](docs/api-examples.md) – REST reference
- [`docs/data-structure.md`](docs/data-structure.md) – task snapshot/result schema and parser payload shape
- [`docs/datahub-task-contract.md`](docs/datahub-task-contract.md) – how datahub should orchestrate parser jobs
- [`docs/datahub-batch-ingestion-contract.md`](docs/datahub-batch-ingestion-contract.md) – push-batch ingestion contract and datahub technical assignment
- [`pyparsers-detailed-task-contract.md`](pyparsers-detailed-task-contract.md) – final unified `detailed` task envelope for `datahub -> pyparsers`
- [`docs/telegram-app.md`](docs/telegram-app.md) – React/Angular UIs and image proxy
- [`docs/services.md`](docs/services.md) – translator and admin bot details
- [`docs/testing.md`](docs/testing.md) – smoke and integration checks for the split parser services

Use the docs folder for everything else (database schema, changelog, etc.).
