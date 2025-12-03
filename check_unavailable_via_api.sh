#!/bin/bash
# Скрипт для проверки количества недоступных машин через API

# URL API (можно изменить)
API_URL="${DATAHUB_URL:-http://localhost:8080}"

echo "Проверка статистики недоступных машин через API..."
echo "API URL: $API_URL"
echo "=========================================="
echo ""

# Получаем статус валидации
response=$(curl -s "${API_URL}/validation/status" 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$response" ]; then
    echo "📊 СТАТИСТИКА ВАЛИДАЦИИ:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
else
    echo "❌ Ошибка при запросе к API"
    echo "Проверьте, что:"
    echo "  1. Сервис datahub запущен"
    echo "  2. Переменная DATAHUB_URL установлена правильно"
    echo "  3. API доступен по адресу: $API_URL"
    echo ""
    echo "Или выполните SQL запрос из файла check_unavailable_cars.sql"
fi

