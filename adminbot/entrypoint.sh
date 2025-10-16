#!/bin/bash
set -e

echo "Starting Admin Bot setup..."

# Настройка webhook
echo "Setting up webhook..."
python setup_webhook.py

# Запуск приложения
echo "Starting application..."
exec uvicorn app:app --host 0.0.0.0 --port 8000
