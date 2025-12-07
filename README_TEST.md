# Тестирование парсинга dongchedi

## Запуск тестового контейнера

1. Соберите образ:
```bash
docker compose -f test-docker-compose.yml build
```

2. Запустите тест с car_id:
```bash
docker compose -f test-docker-compose.yml run --rm test-dongchedi python test_dongchedi_parsing.py <car_id>
```

Пример:
```bash
docker compose -f test-docker-compose.yml run --rm test-dongchedi python test_dongchedi_parsing.py 123456
```

## Что тестируется

1. **Requests парсинг** - попытка получить данные через простые HTTP запросы
2. **Selenium stealth** - парсинг через Selenium с улучшенным stealth режимом
3. **Playwright** - парсинг через Playwright (лучше обходит детекцию)
4. **Network interception** - перехват API запросов для поиска endpoints

## Результаты

Результаты сохраняются в `test_results/test_results_dongchedi_{car_id}.json`

