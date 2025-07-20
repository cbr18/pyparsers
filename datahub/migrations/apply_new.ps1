# Скрипт для применения новых миграций напрямую через psql

param (
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Настройки подключения к базе данных
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "carsdb"
$DB_USER = "postgres"
$DB_PASS = "3iop4r459u8988"

# Проверяем наличие psql
try {
    $psqlVersion = psql --version
    Write-Host "Найден psql: $psqlVersion" -ForegroundColor Green
} catch {
    Write-Host "Ошибка: psql не найден. Убедитесь, что PostgreSQL установлен и добавлен в PATH." -ForegroundColor Red
    exit 1
}

# Функция для выполнения SQL-файла
function Execute-SqlFile {
    param (
        [string]$FilePath
    )

    $fileName = Split-Path $FilePath -Leaf
    Write-Host "Выполнение миграции: $fileName" -ForegroundColor Cyan

    if ($DryRun) {
        Write-Host "Режим dry-run: файл не будет выполнен" -ForegroundColor Yellow
        Get-Content $FilePath | Write-Host
    } else {
        $result = psql -h $DB_HOST -p $DB_PORT -d $DB_NAME -U $DB_USER -f $FilePath 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Ошибка при выполнении миграции $fileName" -ForegroundColor Red
            Write-Host $result -ForegroundColor Red
            return $false
        }
        Write-Host "Миграция $fileName успешно выполнена" -ForegroundColor Green
    }

    return $true
}

# Устанавливаем переменную окружения для пароля PostgreSQL
$env:PGPASSWORD = $DB_PASS

# Выполняем новые миграции
$migration1 = Join-Path $PSScriptRoot "000007_create_brands_table.up.sql"
$migration2 = Join-Path $PSScriptRoot "000008_add_mybrand_id_to_cars.up.sql"

$success = $true

if (Test-Path $migration1) {
    $success = $success -and (Execute-SqlFile -FilePath $migration1)
} else {
    Write-Host "Файл миграции не найден: $migration1" -ForegroundColor Red
    $success = $false
}

if ($success -and (Test-Path $migration2)) {
    $success = $success -and (Execute-SqlFile -FilePath $migration2)
} else {
    Write-Host "Файл миграции не найден: $migration2" -ForegroundColor Red
    $success = $false
}

# Очищаем переменную окружения с паролем
Remove-Item Env:\PGPASSWORD

if ($success) {
    Write-Host "Все миграции успешно выполнены" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Произошли ошибки при выполнении миграций" -ForegroundColor Red
    exit 1
}
