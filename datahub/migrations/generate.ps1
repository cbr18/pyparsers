# Скрипт для генерации миграций с помощью Atlas

param (
    [Parameter(Mandatory=$true)]
    [string]$Name
)

# Настройки подключения к базе данных
$DB_URL = "postgres://postgres:3iop4r459u8988@localhost:5432/carsdb?sslmode=disable"

# Генерируем схему из моделей GORM
Write-Host "Генерация схемы из моделей GORM..." -ForegroundColor Cyan
$schema = go run ../cmd/atlas/main.go
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при генерации схемы из моделей GORM" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Сохраняем схему во временный файл
$schemaFile = "./schema/gorm_schema.json"
$schema | Out-File -FilePath $schemaFile -Encoding utf8

# Генерируем миграцию с помощью Atlas
Write-Host "Генерация миграции с помощью Atlas..." -ForegroundColor Cyan
atlas migrate diff $Name `
    --dir "file://migrations" `
    --to "file://$schemaFile" `
    --dev-url $DB_URL `
    --format golang-migrate

if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при генерации миграции с помощью Atlas" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "Миграция успешно создана" -ForegroundColor Green
