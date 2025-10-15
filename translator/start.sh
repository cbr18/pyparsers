#!/bin/bash

# Скрипт для запуска сервиса переводчика

echo "🚀 Запуск сервиса переводчика..."

# Проверяем наличие .env файла в корне проекта
if [ ! -f "../.env" ]; then
    echo "❌ Файл .env не найден в корне проекта!"
    echo "Создайте файл CarsParser/.env с переменными:"
    echo "YANDEX_API_KEY=your_api_key_here"
    echo "YANDEX_FOLDER_ID=your_folder_id_here"
    echo "REDIS_HOST=redis"
    echo "REDIS_PORT=6379"
    exit 1
fi

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    exit 1
fi

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose не установлен!"
    exit 1
fi

echo "✅ Все проверки пройдены"

# Запускаем сервисы
echo "🐳 Запуск Docker контейнеров..."
docker-compose up --build -d

# Ждем запуска сервисов
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверяем статус сервисов
echo "🔍 Проверка статуса сервисов..."
docker-compose ps

# Проверяем доступность API
echo "🌐 Проверка API..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Сервис переводчика запущен успешно!"
    echo "📚 Документация API: http://localhost:8000/docs"
    echo "🔧 Health Check: http://localhost:8000/health"
else
    echo "❌ Сервис переводчика недоступен!"
    echo "Проверьте логи: docker-compose logs translator"
fi

echo "🎉 Готово!"
