# Скрипт для управления миграциями

param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("up", "down", "create", "version", "force")]
    [string]$Command,

    [Parameter(Mandatory=$false)]
    [string]$Name,

    [Parameter(Mandatory=$false)]
    [int]$Steps = 0,

    [Parameter(Mandatory=$false)]
    [int]$Version = 0
)

# Настройки подключения к базе данных
$DB_URL = "postgres://postgres:3iop4r459u8988@localhost:5432/carsdb?sslmode=disable"
$MIGRATIONS_DIR = "."

# Функция для выполнения миграций
function Run-Migration {
    param (
        [string]$MigrateCommand
    )

    Write-Host "Executing: $MigrateCommand"
    Invoke-Expression $MigrateCommand

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Migration command failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# Обработка команд
switch ($Command) {
    "up" {
        if ($Steps -gt 0) {
            Run-Migration "migrate -database `"$DB_URL`" -path $MIGRATIONS_DIR up $Steps"
        } else {
            Run-Migration "migrate -database `"$DB_URL`" -path $MIGRATIONS_DIR up"
        }
    }
    "down" {
        if ($Steps -gt 0) {
            Run-Migration "migrate -database `"$DB_URL`" -path $MIGRATIONS_DIR down $Steps"
        } else {
            Run-Migration "migrate -database `"$DB_URL`" -path $MIGRATIONS_DIR down 1"
        }
    }
    "create" {
        if ([string]::IsNullOrEmpty($Name)) {
            Write-Host "Error: Name parameter is required for create command" -ForegroundColor Red
            exit 1
        }

        # Получаем следующий номер миграции
        $files = Get-ChildItem -Path "./migrations" -Filter "*.up.sql" | Sort-Object Name
        $nextNum = 1

        if ($files.Count -gt 0) {
            $lastFile = $files | Select-Object -Last 1
            $lastNum = [int]($lastFile.Name -split "_")[0]
            $nextNum = $lastNum + 1
        }

        $prefix = "{0:D6}" -f $nextNum
        $fileName = "${prefix}_${Name}"

        # Создаем файлы миграции
        $upFile = "./migrations/${fileName}.up.sql"
        $downFile = "./migrations/${fileName}.down.sql"

        "" | Out-File -FilePath $upFile -Encoding utf8
        "" | Out-File -FilePath $downFile -Encoding utf8

        Write-Host "Created migration files:" -ForegroundColor Green
        Write-Host "  $upFile" -ForegroundColor Green
        Write-Host "  $downFile" -ForegroundColor Green
    }
    "version" {
        Run-Migration "migrate -database `"$DB_URL`" -path $MIGRATIONS_DIR version"
    }
    "force" {
        if ($Version -eq 0) {
            Write-Host "Error: Version parameter is required for force command" -ForegroundColor Red
            exit 1
        }

        Run-Migration "migrate -database `"$DB_URL`" -path $MIGRATIONS_DIR force $Version"
    }
}

Write-Host "Migration command completed successfully" -ForegroundColor Green
