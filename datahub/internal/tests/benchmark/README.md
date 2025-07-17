# Тесты производительности для datahub

Этот пакет содержит тесты производительности для операций с базой данных в datahub.

## Запуск тестов

### Запуск всех тестов производительности

```bash
cd datahub
go test -bench=. ./internal/tests/benchmark -benchmem
```

### Запуск конкретного теста производительности

```bash
cd datahub
go test -bench=BenchmarkCreateSingleCar ./internal/tests/benchmark -benchmem
```

### Запуск тестов использования памяти и CPU

```bash
cd datahub
go test -run=TestMemoryUsage ./internal/tests/benchmark -v
go test -run=TestCPUUsage ./internal/tests/benchmark -v
```

### Запуск сравнения SQL и GORM

```bash
cd datahub
go test -run=TestSQLvsGORMPerformance ./internal/tests/benchmark -v
```

### Запуск тестов пула соединений

```bash
cd datahub
go test -run=TestConnectionPooling ./internal/tests/benchmark -v
```

## Интерпретация результатов

Результаты тестов производительности выводятся в следующем формате:

```
BenchmarkCreateSingleCar-8            100           15000000 ns/op          12345 B/op         123 allocs/op
```

Где:
- `BenchmarkCreateSingleCar-8`: Название теста и количество используемых процессоров
- `100`: Количество итераций, выполненных во время теста
- `15000000 ns/op`: Среднее время выполнения одной операции в наносекундах
- `12345 B/op`: Среднее количество байт, выделенных на одну операцию
- `123 allocs/op`: Среднее количество выделений памяти на одну операцию

## Примечания

- Перед запуском тестов убедитесь, что база данных настроена и доступна
- Тесты создают и удаляют тестовые данные с источником "benchmark"
- Для корректной работы тестов необходимо наличие файла .env в корне проекта datahub с настройками подключения к базе данных
