# Скрипт для применения миграций с помощью Atlas

param (
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Настройки подключения к базе данных
$DB_URL = "postgres://postgres:3iop4r459u8988@localhost:5432/carsdb?sslmode=disable"

# Копируем миграции из корневой директории в подпапку migrations
$MigrationsDir = Join-Path $PSScriptRoot "migrations"
if (-not (Test-Path $MigrationsDir)) {
    New-Item -ItemType Directory -Path $MigrationsDir | Out-Null
    Write-Host "Создана директория для миграций: $MigrationsDir" -ForegroundColor Yellow
}

# Копируем все SQL файлы миграций из корневой директории в подпапку migrations
Get-ChildItem -Path $PSScriptRoot -Filter "*.sql" | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination $MigrationsDir -Force
    Write-Host "Копирование миграции: $($_.Name)" -ForegroundColor Cyan
}

# Обновляем контрольные суммы миграций
Write-Host "Обновление контрольных сумм миграций..." -ForegroundColor Cyan
atlas migrate hash --dir "file://migrations"

# Применяем миграции с помощью Atlas
if ($DryRun) {
    Write-Host "Проверка миграций (dry-run)..." -ForegroundColor Cyan
    atlas migrate apply `
        --dir "file://migrations" `
        --url $DB_URL `
        --dry-run
} else {
    Write-Host "Применение миграций..." -ForegroundColor Cyan
    atlas migrate apply `
        --dir "file://migrations" `
        --url $DB_URL
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при применении миграций с помощью Atlas" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Миграции успешно применены" -ForegroundColor Green
