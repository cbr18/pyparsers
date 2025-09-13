#!/bin/bash

echo "🚀 Тестирование автоматических миграций..."

# Остановка и удаление существующих контейнеров
echo "📦 Остановка существующих контейнеров..."
docker-compose down -v

# Сборка образов
echo "🔨 Сборка образов..."
docker-compose build datahub-migrate datahub

# Запуск только PostgreSQL
echo "🐘 Запуск PostgreSQL..."
docker-compose up -d postgres

# Ожидание готовности PostgreSQL
echo "⏳ Ожидание готовности PostgreSQL..."
sleep 10

# Запуск миграций
echo "🔄 Запуск миграций..."
docker-compose up datahub-migrate

# Проверка статуса миграций
echo "✅ Проверка результата миграций..."
docker-compose logs datahub-migrate

# Запуск основного приложения
echo "🚀 Запуск основного приложения..."
docker-compose up -d datahub

# Проверка статуса приложения
echo "📊 Проверка статуса приложения..."
sleep 5
docker-compose logs datahub

echo "✨ Тестирование завершено!"
