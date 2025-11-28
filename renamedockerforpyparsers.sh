#!/bin/bash
# Скрипт для сервера pyparsers (31.128.44.218)
# Запускать после git pull

set -e

cd "$(dirname "$0")"

echo "=== Настройка для сервера pyparsers ==="

# Бэкап текущего docker-compose.yml если есть
if [ -f "docker-compose.yml" ]; then
    echo "Создаём бэкап docker-compose.yml -> docker-compose.yml.bak"
    cp docker-compose.yml docker-compose.yml.bak
fi

# Копируем нужный compose файл
echo "Копируем docker-compose-pyparsers.yml -> docker-compose.yml"
cp docker-compose-pyparsers.yml docker-compose.yml

# Создаём .env для pyparsers если не существует
if [ ! -f "pyparsers/.env" ]; then
    echo "Создаём pyparsers/.env из шаблона"
    cp pyparsers/env.pyparsers-server pyparsers/.env
    echo ""
    echo "!!! ВАЖНО: Проверьте pyparsers/.env и убедитесь что IP адреса верные !!!"
else
    echo "pyparsers/.env уже существует, пропускаем"
fi

echo ""
echo "=== Готово! ==="
echo "Теперь можно запустить: docker compose up -d --build"

