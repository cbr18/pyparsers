# Миграции базы данных

В этом проекте используется комбинация GORM, Atlas и golang-migrate для управления миграциями базы данных.

## Структура

- `migrations/` - директория с файлами миграций
  - `*.up.sql` - SQL-скрипты для применения миграций
  - `*.down.sql` - SQL-скрипты для отката миграций
  - `migrate.ps1` - PowerShell скрипт для управления миграциями
- `cmd/atlas/main.go` - интеграция Atlas с GORM для генерации схемы

## Использование миграций

### Применение миграций

```powershell
# Применить все миграции
./migrations/migrate.ps1 -Command up

# Применить определенное количество миграций
./migrations/migrate.ps1 -Command up -Steps 1
```

### Откат миграций

```powershell
# Откатить последнюю миграцию
./migrations/migrate.ps1 -Command down

# Откатить определенное количество миграций
./migrations/migrate.ps1 -Command down -Steps 2
```

### Создание новой миграции

```powershell
# Создать новую миграцию
./migrations/migrate.ps1 -Command create -Name add_new_column_to_cars
```

### Проверка текущей версии миграций

```powershell
./migrations/migrate.ps1 -Command version
```

### Принудительная установка версии

```powershell
./migrations/migrate.ps1 -Command force -Version 1
```

## Работа с Atlas

Atlas используется для визуализации и управления схемой базы данных.

### Проверка схемы

```powershell
atlas schema inspect -u "postgres://postgres:3iop4r459u8988@localhost:5432/carsdb?sslmode=disable"
```

### Применение миграций через Atlas

```powershell
atlas migrate apply --url "postgres://postgres:3iop4r459u8988@localhost:5432/carsdb?sslmode=disable" --dir "file://./migrations"
```

### Генерация миграций на основе изменений схемы

```powershell
atlas migrate diff --to "file://./migrations/schema.hcl" --dir "file://./migrations" --format golang-migrate
```

## Интеграция с GORM

В проекте настроена интеграция GORM с миграциями:

1. Модели определены в пакете `internal/domain`
2. Репозитории используют GORM для работы с базой данных
3. Для автоматической миграции в разработке можно использовать `database.AutoMigrate()`
4. Для продакшена рекомендуется использовать миграции через golang-migrate

## Рекомендации

1. Всегда тестируйте миграции в тестовой среде перед применением в продакшене
2. Создавайте миграции для каждого изменения схемы базы данных
3. Убедитесь, что миграции можно откатить (down-скрипты корректны)
4. Используйте транзакции в миграциях для обеспечения атомарности изменений
