# Юнит-тесты для datahub

Этот пакет содержит юнит-тесты для компонентов datahub.

## Запуск тестов

### Запуск всех юнит-тестов

```bash
cd datahub
go test ./internal/tests/unit -v
```

### Запуск конкретного теста

```bash
cd datahub
go test ./internal/tests/unit -v -run=TestCarRepositoryCreate
```

### Запуск тестов с покрытием

```bash
cd datahub
go test ./internal/tests/unit -v -cover
```

### Генерация отчета о покрытии

```bash
cd datahub
go test ./internal/tests/unit -coverprofile=coverage.out
go tool cover -html=coverage.out -o coverage.html
```

## Примечания

- Перед запуском тестов убедитесь, что база данных настроена и доступна
- Тесты создают и удаляют тестовые данные с источником "test"
- Для корректной работы тестов необходимо наличие файла .env в корне проекта datahub с настройками подключения к базе данных
