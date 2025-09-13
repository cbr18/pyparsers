# Тестирование автоматических миграций

Write-Host "🚀 Тестирование автоматических миграций..." -ForegroundColor Green

# Остановка и удаление существующих контейнеров
Write-Host "📦 Остановка существующих контейнеров..." -ForegroundColor Yellow
docker-compose down -v

# Сборка образов
Write-Host "🔨 Сборка образов..." -ForegroundColor Yellow
docker-compose build datahub-migrate datahub

# Запуск только PostgreSQL
Write-Host "🐘 Запуск PostgreSQL..." -ForegroundColor Yellow
docker-compose up -d postgres

# Ожидание готовности PostgreSQL
Write-Host "⏳ Ожидание готовности PostgreSQL..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Запуск миграций
Write-Host "🔄 Запуск миграций..." -ForegroundColor Yellow
docker-compose up datahub-migrate

# Проверка статуса миграций
Write-Host "✅ Проверка результата миграций..." -ForegroundColor Yellow
docker-compose logs datahub-migrate

# Запуск основного приложения
Write-Host "🚀 Запуск основного приложения..." -ForegroundColor Yellow
docker-compose up -d datahub

# Проверка статуса приложения
Write-Host "📊 Проверка статуса приложения..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
docker-compose logs datahub

Write-Host "✨ Тестирование завершено!" -ForegroundColor Green
