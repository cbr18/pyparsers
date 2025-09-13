#!/bin/sh

set -e

echo "Starting migration process..."

# Ждем готовности базы данных
/app/wait-for-db.sh "$POSTGRES_HOST" "$POSTGRES_PORT" "$POSTGRES_USER" "$POSTGRES_PASSWORD" "$POSTGRES_DB" echo "Database is ready"

# Строим URL для подключения
DB_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}?sslmode=disable"

echo "Running migrations..."

# Применяем миграции
/app/migrate -database "$DB_URL" -path /app/migrations up

echo "Migrations completed successfully"
