# Скрипт для применения миграций с помощью Atlas

param (
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Настройки подключения к базе данных
$DB_URL = "postgres://postgres:3iop4r459u8988@localhost:5432/carsdb?sslmode=disable"

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
