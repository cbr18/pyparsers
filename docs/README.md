# CarCatch Documentation

## Overview

CarCatch is a microservice platform that scrapes dongchedi.com and che168.com, enriches the data, stores it in PostgreSQL, and serves it through multiple APIs and UIs (web, Angular, Telegram, admin tools).  
This folder aggregates every Markdown reference so you no longer have to guess where a document lives.

## Quick Start

```bash
git clone <repository>
cd CarsParser
cp pyparsers/env.example .env
docker compose up -d --build
./scripts/health-check.sh   # or .ps1 on Windows
```

Useful URLs after compose finishes:

- Dongchedi parser: http://localhost:5001
- Che168 parser: http://localhost:5002
- Dongchedi Swagger / ReDoc: http://localhost:5001/docs
- Che168 Swagger / ReDoc: http://localhost:5002/docs
- Dongchedi tasks: http://localhost:5001/tasks
- Che168 tasks: http://localhost:5002/tasks

## Service Map

- `postgres` & `admin-postgres` – main and admin databases
- `datahub` – Go API, enhancement worker, task orchestration
- `pyparsers-dongchedi` – FastAPI service on `:5001` with direct routes like `/blocked`, `/cars/page/{page}`, `/cars/car/{car_id}`
- `pyparsers-che168` – FastAPI service on `:5002` with direct routes like `/blocked`, `/cars/page/{page}`, `/detailed/parse`
- `translator` & `redis` – async translation microservice with caching
- `telegrambot`, `telegramapp`, `telegramngapp` – user‑facing entry points
- `adminbot`, `adminservice`, `adminweb` – internal tooling
- `cron-updater` – scheduled ingestion runner

## Documentation Map

- `api-documentation.md` – complete REST API reference (pyparsers, datahub, telegram services)
- `api-examples.md` – practical cURL/Postman snippets
- `data-structure.md` – parser task snapshots, result envelopes, and payload shape
- `datahub-task-contract.md` – parser task lifecycle and the expected datahub interaction pattern
- `operations.md` – deployment, migrations, task API, troubleshooting, backups
- `database-schema.md` – tables, indexes, and field glossary
- `parsers.md` – parser pipeline, enhancement worker, HTTP client utilities
- `changelog.md` – history of major parser/enhancement milestones
- `services.md` – translator service, admin bot, and other supporting components
- `telegram-app.md` – UI behavior, displayed fields, Angular/React quick start, image proxy details
- `testing.md` – smoke and integration checks for the split parser services

If you need something that is not covered yet, add it here—this README is now the single source of truth for documentation entry points.
