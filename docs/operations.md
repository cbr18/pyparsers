# Operations Guide

This guide consolidates the deployment, migrations, automation, and operational tooling that used to live in multiple scattered READMEs.

## Deployment Profiles

### Development
1. Install Docker / Docker Compose.
2. Clone the repo and copy `pyparsers/env.example` → `.env`.
3. Start the parser stack with `docker compose up -d --build`.
4. Run `./scripts/health-check.sh` (or the PowerShell variant) to ensure both parser services reply.

### Production Basics
- Use a dedicated `.env.production` with hardened secrets.
- `docker compose up -d --build` deploys new images.
- Scaling example: `docker compose up -d --scale datahub=3 --scale telegramapp=2`.

### Service Access

| URL | Purpose |
| --- | --- |
| `http://localhost:5001` | Dongchedi parser API |
| `http://localhost:5002` | Che168 parser API |
| `http://localhost:5001/docs` | Dongchedi Swagger UI |
| `http://localhost:5002/docs` | Che168 Swagger UI |

### Common Compose Commands
```bash
docker compose up -d            # start/update
docker compose up -d --build    # rebuild everything
docker compose logs -f          # tail logs
docker compose logs service     # focus on one service
docker compose restart service  # bounce one service
docker compose down -v          # stop and drop volumes
```

## Health & Troubleshooting

- `./scripts/health-check.(sh|ps1)` – pings every HTTP health endpoint.
- `docker stats` – live container resources.
- `docker compose ps` – quick readiness check.
- Port conflicts: use `netstat -tulpn | grep :<port>` and stop foreign services (e.g., `sudo systemctl stop apache2`).
- Database woes: `docker compose logs postgres`, `docker compose exec postgres psql -U postgres -d carsdb`.
- Slow responses: inspect parser logs and review DB activity via `SELECT * FROM pg_stat_activity;`.

## Automated Migrations

Compose ships two Dockerfiles inside `datahub/`:
- `Dockerfile` – main service.
- `migrate.Dockerfile` – runs `golang-migrate` before the API starts.

Workflow:
1. `datahub-migrate` waits for Postgres via `wait-for-db.sh`.
2. `run-migrations.sh` applies every `migrations/*.up.sql`.
3. On success the container exits and `datahub` starts; on failure the app refuses to boot.
4. Logs live under `docker compose logs datahub-migrate`.

### Creating New Migrations
```bash
cd datahub
# Atlas / GORM diff
./migrations/generate.ps1 -Name add_new_feature

# Manual SQL pair
touch migrations/000014_add_feature.up.sql
touch migrations/000014_add_feature.down.sql

docker compose down
docker compose up -d            # auto-applies the new files
```

### Manual Control (Atlas / golang-migrate)
```bash
# Apply with Atlas (dry-run, then apply)
./migrations/apply.ps1 -DryRun
./migrations/apply.ps1

# Use golang-migrate inside Docker
docker run --rm -it \
  --network carcatch-network \
  --env-file ./.env \
  -v $(pwd)/datahub/migrations:/migrations \
  migrate/migrate:v4.17.0 \
  -path /migrations \
  -database "postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB?sslmode=disable" \
  up
```

**Troubleshooting:**  
`force VERSION_NUMBER` fixes a dirty state, `version` prints the current head, and `.down.sql` files allow safe rollbacks.

## Parser Task API

Each parser service now exposes its own execution job API:

| Endpoint | Description |
| --- | --- |
| `POST /tasks` | Create a parser job (`full`, `incremental`, `detailed`). |
| `GET /tasks` | List recent jobs for that parser service. |
| `GET /tasks/{id}` | Inspect one job snapshot with heartbeat and progress. |
| `GET /tasks/{id}/result` | Fetch the final payload after success. |
| `POST /tasks/{id}/cancel` | Request cancellation. |

Task statuses:

- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

This parser-side task state is execution state, not the system-of-record. The recommended orchestration contract for `datahub` lives in [`docs/datahub-task-contract.md`](datahub-task-contract.md).

## Backups & Recovery

```bash
# Full DB dump
docker compose exec postgres pg_dump -U postgres carsdb > backup.sql
# Compressed variant
docker compose exec postgres pg_dump -U postgres carsdb | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Restore
docker compose exec -T postgres psql -U postgres carsdb < backup.sql
gunzip -c backup.sql.gz | docker compose exec -T postgres psql -U postgres carsdb

# Backup named volumes
docker run --rm -v carcatch_pg_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/pg_backup.tar.gz -C /data .
```

## Quick Reference: Enhancement Worker

- Runs automatically inside `datahub`, reading cars with `has_details = false`.
- Defaults: `batch_size=10`, `delay_between_batches=300s`, `delay_between_cars=2s`, `max_concurrent=3`.
- Control endpoints (all `POST`): `/enhancement/start`, `/enhancement/stop`, `/enhancement/config`.
- Status endpoint: `GET /enhancement/status` (shows per-source backlog, config, running flag).
- Cron container (`cron-updater`) keeps seeding new IDs so the worker always has work.

## Troubleshooting Checklist

1. **Worker stuck?** Check `datahub` logs for enhancement errors, then `curl /enhancement/status`.
2. **Parser timeouts?** Adjust HTTP client rate limiting / retries (see `docs/parsers.md`) or bump `max_concurrent`.
3. **Admin bot webhook?** Ensure the client calls the correct admin bot endpoint and tokens match `env`.
4. **Translator failures?** Confirm Redis is reachable and Yandex credentials exist in `.env`.
5. **Image proxy issues?** Validate the image proxy endpoint returns 200 and the proxy service is reachable.

Keeping these references in a single file means on-call engineers have one bookmark for every operational task.
