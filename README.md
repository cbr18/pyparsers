# CarCatch

CarCatch is a microservice platform that scrapes dongchedi.com and che168.com, enriches the data set, and exposes it through multiple APIs, bots, and web clients.

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
- Dongchedi docs: http://localhost:5001/docs
- Che168 docs: http://localhost:5002/docs

## Documentation

All markdown guides now live in `docs/`.

- [`docs/README.md`](docs/README.md) – entry point + service map
- [`docs/operations.md`](docs/operations.md) – deployment, migrations, task API, backups
- [`docs/parsers.md`](docs/parsers.md) – parser pipeline, enhancement worker, HTTP client tooling
- [`docs/api-documentation.md`](docs/api-documentation.md) / [`docs/api-examples.md`](docs/api-examples.md) – REST reference
- [`docs/telegram-app.md`](docs/telegram-app.md) – React/Angular UIs and image proxy
- [`docs/services.md`](docs/services.md) – translator and admin bot details
- [`docs/testing.md`](docs/testing.md) – smoke and integration checks for the split parser services

Use the docs folder for everything else (database schema, changelog, etc.).
