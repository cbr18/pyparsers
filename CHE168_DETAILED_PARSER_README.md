# Che168 Detailed Parser

Реализация парсера детальной информации о машинах с сайта che168.com для проекта CarsParser.

## Обзор

Этот модуль добавляет возможность парсинга детальной информации о машинах с che168.com, включая технические характеристики, изображения, историю владения и другие детали. **Структура полностью соответствует dongchedi** для максимальной модульности.

## Структура

### Python (pyparsers)
- `pyparsers/api/che168/models/detailed_car.py` - Модель данных для детальной информации
- `pyparsers/api/che168/detailed_parser.py` - Парсер детальной информации
- `pyparsers/api/che168/detailed_api.py` - FastAPI эндпоинты

### Go (datahub) - Единая структура с dongchedi
- `datahub/internal/infrastructure/external/che168.go` - Che168Client с методами EnhanceCar и BatchEnhanceCars
- `datahub/internal/usecase/enhancement_service.go` - EnhancementService (поддерживает dongchedi и che168)
- `datahub/internal/usecase/enhancement_worker.go` - EnhancementWorker (поддерживает dongchedi и che168)

## API Эндпоинты

### Python API (pyparsers)
- `POST /che168/detailed/parse` - Парсинг детальной информации одной машины
- `POST /che168/detailed/parse-batch` - Пакетный парсинг детальной информации
- `GET /che168/detailed/health` - Проверка здоровья сервиса

### Go API (datahub) - Единые эндпоинты для всех источников
- `GET /enhancement/status` - Статус воркера улучшения
- `POST /enhancement/start` - Запуск воркера улучшения
- `POST /enhancement/stop` - Остановка воркера улучшения
- `POST /enhancement/config` - Конфигурация воркера улучшения

## Использование

### 1. Запуск Python API

```bash
cd pyparsers
python async_api_server.py
```

### 2. Запуск Go API

```bash
cd datahub
go run cmd/main.go
```

### 3. Воркер запускается автоматически

Воркер улучшения машин запускается автоматически при старте datahub и работает в фоновом режиме для всех источников (dongchedi и che168).

### 4. Переменные окружения

```bash
# Для datahub
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=carsdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
API_BASE_URL=http://localhost:8000

# Для воркера
WORKER_ENABLED=true
WORKER_BATCH_SIZE=50
WORKER_RATE_LIMIT=1s
WORKER_RETRY_ATTEMPTS=3
WORKER_RETRY_DELAY=5s
```

## Примеры использования

### Парсинг детальной информации одной машины

```bash
curl -X POST "http://localhost:8000/che168/detailed/parse" \
  -H "Content-Type: application/json" \
  -d '{"car_id": 56481576, "force_update": true}'
```

### Пакетный парсинг

```bash
curl -X POST "http://localhost:8000/che168/detailed/parse-batch" \
  -H "Content-Type: application/json" \
  -d '{"car_ids": [56481576, 12345678], "force_update": true}'
```

### Управление воркером улучшения

```bash
# Проверить статус воркера
curl -X GET "http://localhost:8080/enhancement/status"

# Запустить воркер (если остановлен)
curl -X POST "http://localhost:8080/enhancement/start"

# Остановить воркер
curl -X POST "http://localhost:8080/enhancement/stop"
```

## Конфигурация

### Настройки парсера
- `headless=True` - Запуск браузера в headless режиме
- Rate limiting - 1 запрос в секунду по умолчанию
- Retry attempts - 3 попытки по умолчанию

### Настройки воркера
- `WORKER_BATCH_SIZE` - Размер батча для обработки (по умолчанию 50)
- `WORKER_RATE_LIMIT` - Задержка между запросами (по умолчанию 1s)
- `WORKER_RETRY_ATTEMPTS` - Количество попыток повтора (по умолчанию 3)
- `WORKER_RETRY_DELAY` - Задержка между попытками (по умолчанию 5s)

## Мониторинг

### Логи
Все операции логируются с уровнем INFO и выше. Логи включают:
- Начало и завершение парсинга
- Количество обработанных машин
- Ошибки парсинга
- Статистику воркера

### Метрики
- Количество успешно обработанных машин
- Количество ошибок
- Время выполнения операций

## Обработка ошибок

### Типы ошибок
1. **Ошибки парсинга** - проблемы с извлечением данных с сайта
2. **Ошибки сети** - проблемы с подключением к pyparsers API
3. **Ошибки базы данных** - проблемы с сохранением данных
4. **Ошибки валидации** - некорректные данные

### Стратегия retry
- Автоматические повторы для сетевых ошибок
- Экспоненциальная задержка между попытками
- Максимальное количество попыток настраивается

## Производительность

### Оптимизации
- Headless режим браузера
- Блокировка загрузки изображений
- Батчевая обработка
- Rate limiting

### Рекомендации
- Используйте батчи для массовой обработки
- Настройте rate limiting в зависимости от нагрузки
- Мониторьте использование памяти браузером

## Безопасность

### Защита от блокировок
- Ротация User-Agent
- Случайные задержки
- Headless режим
- Блокировка изображений и медиа

### Ограничения
- Максимум 100 машин в одном батче
- Таймаут 30 секунд на запрос
- Максимум 3 попытки повтора

## Разработка

### Добавление новых полей
1. Обновите `Che168DetailedCar` модель
2. Добавьте извлечение в `Che168DetailedParser`
3. Обновите `updateCarFields` в `CarDetailService`

### Тестирование
```bash
# Тест парсера
python -m pytest pyparsers/tests/test_che168_detailed.py

# Тест API
curl -X GET "http://localhost:8000/che168/detailed/health"
```

## Troubleshooting

### Частые проблемы

1. **Selenium не установлен**
   ```bash
   pip install selenium
   ```

2. **ChromeDriver не найден**
   ```bash
   # Установите ChromeDriver или используйте webdriver-manager
   pip install webdriver-manager
   ```

3. **Ошибки подключения к БД**
   - Проверьте переменные окружения
   - Убедитесь, что PostgreSQL запущен
   - Проверьте миграции

4. **Ошибки парсинга**
   - Проверьте доступность сайта che168.com
   - Убедитесь, что car_id существует
   - Проверьте логи на детали ошибки

### Логи
```bash
# Логи Python API
tail -f pyparsers/logs/che168_detailed.log

# Логи Go API
tail -f datahub/logs/datahub.log

# Логи воркера
tail -f datahub/logs/worker.log
```
