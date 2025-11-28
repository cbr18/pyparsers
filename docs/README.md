# CarCatch Documentation

## Overview

CarCatch is a microservice platform that scrapes dongchedi.com and che168.com, enriches the data, stores it in PostgreSQL, and serves it through multiple APIs and UIs (web, Angular, Telegram, admin tools).  
This folder aggregates every Markdown reference so you no longer have to guess where a document lives.

## Quick Start

```bash
git clone <repository>
cd CarsParser
cp .env.example .env        # fill in secrets
docker compose up -d        # start everything
./scripts/health-check.sh   # or .ps1 on Windows
```

Useful URLs after compose finishes:

- Reverse proxy: http://localhost
- React app: http://localhost/podbortg
- Angular app: http://localhost/ng
- DataHub API: http://localhost:8080
- PyParsers API: http://localhost:5000
- Swagger / ReDoc: http://localhost/docs

## Service Map

- `nginx` – frontend router, TLS termination, image proxy
- `postgres` & `admin-postgres` – main and admin databases
- `datahub` – Go API, enhancement worker, task orchestration
- `pyparsers` – FastAPI service that handles scraping and translators
- `translator` & `redis` – async translation microservice with caching
- `telegrambot`, `telegramapp`, `telegramngapp` – user‑facing entry points
- `adminbot`, `adminservice`, `adminweb` – internal tooling
- `cron-updater` – scheduled ingestion runner

## Documentation Map

- `api-documentation.md` – complete REST API reference (pyparsers, datahub, telegram services)
- `api-examples.md` – practical cURL/Postman snippets
- `operations.md` – deployment, migrations, task API, troubleshooting, backups
- `database-schema.md` – tables, indexes, and field glossary
- `parsers.md` – parser pipeline, enhancement worker, HTTP client utilities
- `changelog.md` – history of major parser/enhancement milestones
- `services.md` – translator service, admin bot, and other supporting components
- `telegram-app.md` – UI behavior, displayed fields, Angular/React quick start, image proxy details
- `testing.md` – parser acceptance report and pyparsers unit-test guide

If you need something that is not covered yet, add it here—this README is now the single source of truth for documentation entry points.
