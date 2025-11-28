# Supporting Services

## Translator (`translator/`)

FastAPI + Redis microservice that translates scraped data (defaults: zh → ru) using Yandex Cloud.

### Capabilities
- `POST /translate/text` – translate a single string.
- `POST /translate/json` – walk JSON payloads and translate values.
- `POST /translate/db` – batch translate records before they hit Postgres.
- `GET /translate/stats` – translation counters.
- `GET /translate/cache/stats`, `POST /translate/cache/clear` – Redis cache introspection.
- Automatic retries/backoff + Redis caching built into the `TranslatorService`.

### Environment
```
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=...
REDIS_HOST=redis
REDIS_PORT=6379
```
The service loads the root `.env`, so compose deployments don’t need a separate env file.

### Running
```bash
# Docker (recommended)
docker compose up translator redis --build

# Local dev
cd translator
pip install -r requirements.txt
docker run -d -p 6379:6379 redis:7.2
uvicorn app.main:app --reload --port 8000
```

### Monitoring & Reliability
- Health endpoint: `GET /translate/health`.
- Logs include Redis connection status, API latency, and retry activity.
- Cache hit/miss metrics expose how much load is shifted off the external API.

## Admin Bot (`adminbot/`)

Telegram bot for administrators: search cars by UUID, manage admins, receive lead notifications.

### Features
- `/start` + inline buttons for:
  - 🔍 search by UUID (pulls via DataHub)
  - 👥 manage admin list
  - ℹ️ list active admins
- Webhook endpoints:
  - `GET /health`
  - `POST /lead` (expects `{ car, user }` payload; used by `telegramapp` → `/admin-lead` proxy)
  - `POST /bot` for Telegram updates.

### Configuration
```
ADMIN_BOT_TOKEN=...
ADMIN_WEBHOOK_URL=https://<your-domain>/admin-bot
DATAHUB_URL=http://datahub:8080
ADMIN_USERNAME=...
```

### Running
```bash
cd adminbot
pip install -r requirements.txt
cp env.example .env   # fill in values
python app.py         # local dev

# Docker image
docker build -t adminbot .
docker run -d --env-file .env -p 8002:8000 adminbot
```

### nginx Integration
```nginx
location /admin-lead {
    proxy_pass http://adminbot_backend/lead;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Hook `telegramapp/src/services/api.js::sendLeadRequest` to `/admin-lead` so UI submissions alert admins immediately.

