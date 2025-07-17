# Юнит-тесты для pyparsers

Этот пакет содержит юнит-тесты для компонентов pyparsers.

## Установка зависимостей

Перед запуском тестов необходимо установить зависимости:

```bash
cd pyparsers
pip install -e ".[dev]"
```

## Запуск тестов

### Запуск всех юнит-тестов

```bash
cd pyparsers
pytest tests/unit -v
```

### Запуск конкретного теста

```bash
cd pyparsers
pytest tests/unit/test_dongchedi_parser.py -v
```

### Запуск тестов с покрытием

```bash
cd pyparsers
pytest tests/unit -v --cov=api
```

### Генерация отчета о покрытии

```bash
cd pyparsers
pytest tests/unit --cov=api --cov-report=html
```

## Примечания

- Тесты используют библиотеку `responses` для мокирования HTTP-запросов
- Тесты не выполняют реальных запросов к внешним API
- Для тестирования API сервера используется `TestClient` из FastAPI
