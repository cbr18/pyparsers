#!/bin/bash
# Скрипт для основного сервера / datahub (217.114.1.62)
# Запускать после git pull

set -e

cd "$(dirname "$0")"

echo "=== Настройка для основного сервера (datahub) ==="

# Бэкап текущего docker-compose.yml если есть
if [ -f "docker-compose.yml" ]; then
    echo "Создаём бэкап docker-compose.yml -> docker-compose.yml.bak"
    cp docker-compose.yml docker-compose.yml.bak
fi

# Копируем нужный compose файл
echo "Копируем docker-compose-main.yml -> docker-compose.yml"
cp docker-compose-main.yml docker-compose.yml

# Добавляем переменные в .env если их нет
if [ -f ".env" ]; then
    if ! grep -q "PYPARSERS_SERVER_IP" .env; then
        echo ""
        echo "Добавляем PYPARSERS_SERVER_IP и ALLOWED_IPS в .env"
        cat >> .env << 'EOF'

# Pyparsers server protection (added by renamedockerfordatahub.sh)
ALLOWED_IPS=31.128.44.218
PYPARSERS_SERVER_IP=31.128.44.218
EOF
    else
        echo "PYPARSERS_SERVER_IP уже есть в .env, пропускаем"
    fi
else
    echo "!!! ВНИМАНИЕ: .env не найден! Создайте его из .env.example !!!"
fi

echo ""
echo "=== Готово! ==="
echo "Теперь можно запустить: docker compose up -d --build"

