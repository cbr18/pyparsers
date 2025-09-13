# Автоматические миграции в Docker Compose

Этот проект настроен для автоматического применения миграций базы данных при запуске через Docker Compose.

## Как это работает

1. **Отдельный контейнер для миграций**: `datahub-migrate` запускается перед основным приложением
2. **Ожидание готовности БД**: Скрипт `wait-for-db.sh` ждет готовности PostgreSQL
3. **Применение миграций**: Используется `golang-migrate` для применения всех доступных миграций
4. **Запуск приложения**: После успешного завершения миграций запускается основное приложение

## Структура файлов

```
datahub/
├── Dockerfile                    # Основной Dockerfile для приложения
├── migrate.Dockerfile           # Dockerfile для контейнера миграций
├── wait-for-db.sh              # Скрипт ожидания готовности БД
├── run-migrations.sh           # Скрипт запуска миграций
├── migrations/                 # Папка с файлами миграций
│   ├── 000001_*.up.sql
│   ├── 000001_*.down.sql
│   └── ...
└── internal/infrastructure/migration/
    └── migrate.go              # Go модуль для миграций (опционально)
```

## Использование

### Запуск с миграциями

```bash
# Запуск всех сервисов (миграции применятся автоматически)
docker-compose up -d

# Просмотр логов миграций
docker-compose logs datahub-migrate

# Просмотр логов основного приложения
docker-compose logs datahub
```

### Создание новой миграции

1. Создайте файлы миграции в папке `migrations/`:
   ```
   000009_add_new_feature.up.sql
   000009_add_new_feature.down.sql
   ```

2. Перезапустите сервисы:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### Откат миграций (вручную)

```bash
# Подключитесь к контейнеру с migrate
docker run --rm -it \
  --network carcatch-network \
  --env-file .env \
  -v $(pwd)/datahub/migrations:/migrations \
  migrate/migrate:v4.17.0 \
  -path /migrations \
  -database "postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB?sslmode=disable" \
  down 1
```

## Особенности

- **Безопасность**: Контейнер миграций запускается с `restart: "no"` и завершается после выполнения
- **Зависимости**: Основное приложение ждет успешного завершения миграций
- **Логирование**: Все операции миграций логируются
- **Обработка ошибок**: При ошибке миграций основное приложение не запустится

## Переменные окружения

Используются те же переменные, что и для основного приложения:
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

## Troubleshooting

### Проблема с dirty state

Если база данных находится в "грязном" состоянии:

```bash
# Принудительно установить версию
docker run --rm -it \
  --network carcatch-network \
  --env-file .env \
  -v $(pwd)/datahub/migrations:/migrations \
  migrate/migrate:v4.17.0 \
  -path /migrations \
  -database "postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB?sslmode=disable" \
  force VERSION_NUMBER
```

### Проверка текущей версии

```bash
docker run --rm -it \
  --network carcatch-network \
  --env-file .env \
  -v $(pwd)/datahub/migrations:/migrations \
  migrate/migrate:v4.17.0 \
  -path /migrations \
  -database "postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB?sslmode=disable" \
  version
```
