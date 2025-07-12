# DataHub - Go приложение для работы с данными автомобилей

## Обзор
Go приложение для синхронизации данных автомобилей из Python API (pyparsers) в PostgreSQL базу данных и предоставления API для фронтенд приложений.

## Архитектура

### Структура проекта
```
datahub/
├── main.go                 # Точка входа
├── go.mod                  # Зависимости
├── config/
│   └── config.go          # Конфигурация (DB, API endpoints)
├── models/
│   └── car.go             # Модели данных для PostgreSQL
├── database/
│   ├── connection.go       # Подключение к PostgreSQL
│   └── migrations/         # SQL миграции
├── services/
│   ├── car_service.go      # Бизнес-логика работы с машинами
│   └── parser_service.go   # Интеграция с Python API
├── handlers/
│   └── api.go             # HTTP API endpoints
├── scheduler/
│   └── scheduler.go       # Планировщик обновления данных
└── REQUIREMENTS.md        # Этот файл
```

## Функциональные требования

### 1. Синхронизация данных
- **Полная синхронизация**: Ежедневная полная синхронизация данных (перезапись всей БД)
  - Время выполнения: может занимать несколько часов
  - Расписание: каждый день в 02:00 (когда нагрузка минимальна)
  - Стратегия: полный проход по всем страницам парсера
- **Инкрементальная синхронизация**: Каждые 30 минут проверка новых машин
  - Быстрая проверка только новых данных
  - Остановка при первом совпадении с существующими записями
- **Источники данных**: 
  - Dongchedi (dongchedi.com) - endpoint `/cars/dongchedi/*`
  - Che168 (che168.com) - endpoint `/cars/che168/*`
- **Поле источника**: В БД сохраняется источник данных (dongchedi/che168) в зависимости от используемого endpoint
- **Обработка ошибок**: Retry логика при сбоях API с экспоненциальной задержкой
- **Логирование**: Детальное логирование всех операций синхронизации с временными метками
- **Мониторинг прогресса**: Отслеживание прогресса длительных операций синхронизации

### 2. База данных PostgreSQL

#### Структура таблицы cars
```sql
CREATE TABLE cars (
    id SERIAL PRIMARY KEY,
    source VARCHAR(20) NOT NULL, -- 'dongchedi' или 'che168'
    car_id VARCHAR(100) UNIQUE NOT NULL,
    title TEXT,
    sh_price DECIMAL(10,2),
    image_url TEXT,
    link TEXT,
    car_name VARCHAR(255),
    car_year INTEGER,
    car_mileage VARCHAR(100),
    car_source_city_name VARCHAR(100),
    brand_name VARCHAR(100),
    series_name VARCHAR(100),
    brand_id INTEGER,
    series_id INTEGER,
    shop_id VARCHAR(100),
    tags_v2 TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Индексы
```sql
CREATE INDEX idx_cars_source ON cars(source);
CREATE INDEX idx_cars_brand ON cars(brand_name);
CREATE INDEX idx_cars_year ON cars(car_year);
CREATE INDEX idx_cars_price ON cars(sh_price);
CREATE INDEX idx_cars_car_id ON cars(car_id);
CREATE INDEX idx_cars_created_at ON cars(created_at);
```

### 3. REST API

#### Endpoints для получения данных

**GET /api/cars**
- Получение списка машин с пагинацией и фильтрацией
- Параметры запроса:
  - `page` (int, default: 1) - номер страницы
  - `limit` (int, default: 20, max: 100) - количество машин на странице
  - `source` (string) - фильтр по источнику ('dongchedi', 'che168')
  - `brand` (string) - фильтр по бренду
  - `year_from` (int) - минимальный год
  - `year_to` (int) - максимальный год
  - `price_from` (decimal) - минимальная цена
  - `price_to` (decimal) - максимальная цена
  - `city` (string) - фильтр по городу
  - `sort_by` (string) - поле для сортировки ('price', 'year', 'created_at')
  - `sort_order` (string) - порядок сортировки ('asc', 'desc')

**GET /api/cars/{id}**
- Получение детальной информации о машине по ID

**GET /api/cars/sources**
- Получение статистики по источникам данных
- Возвращает количество машин по каждому источнику

**GET /api/cars/brands**
- Получение списка всех брендов с количеством машин

**GET /api/cars/cities**
- Получение списка всех городов с количеством машин

#### Endpoints для управления синхронизацией

**POST /api/sync/dongchedi**
- Принудительная синхронизация данных с Dongchedi
- Параметры:
  - `full_sync` (bool, default: false) - полная синхронизация или инкрементальная
  - `force` (bool, default: false) - принудительный запуск даже если уже выполняется

**POST /api/sync/che168**
- Принудительная синхронизация данных с Che168
- Параметры:
  - `full_sync` (bool, default: false) - полная синхронизация или инкрементальная
  - `force` (bool, default: false) - принудительный запуск даже если уже выполняется

**GET /api/sync/status**
- Получение статуса синхронизации
- Возвращает:
  - Время последней полной и инкрементальной синхронизации
  - Текущий статус (idle/running/failed)
  - Прогресс текущей операции (для длительных операций)
  - Количество новых машин в последней синхронизации
  - Ошибки последней синхронизации
  - Время выполнения последней операции

**GET /api/sync/progress**
- Получение прогресса текущей синхронизации (для длительных операций)
- Возвращает:
  - Текущую страницу
  - Общее количество страниц
  - Процент выполнения
  - Оценку оставшегося времени
  - Количество обработанных машин

### 4. Пагинация

#### Формат ответа с пагинацией
```json
{
  "data": [
    {
      "id": 1,
      "source": "dongchedi",
      "car_id": "12345",
      "title": "BMW X5 2020",
      "sh_price": 2500000.00,
      "image_url": "https://...",
      "link": "https://...",
      "car_name": "BMW X5",
      "car_year": 2020,
      "car_mileage": "50000 км",
      "car_source_city_name": "Москва",
      "brand_name": "BMW",
      "series_name": "X5",
      "brand_id": 1,
      "series_id": 5,
      "shop_id": "shop123",
      "tags_v2": "premium, suv",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1500,
    "total_pages": 75,
    "has_next": true,
    "has_prev": false
  }
}
```

#### Валидация параметров пагинации
- `page`: минимальное значение 1
- `limit`: минимальное значение 1, максимальное 100
- При превышении лимитов возвращать ошибку 400 Bad Request

### 5. Конфигурация

#### Переменные окружения
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cars_db
DB_USER=cars_user
DB_PASSWORD=cars_password
DB_SSL_MODE=disable

# Python API
PYTHON_API_URL=http://localhost:8000

# Server
SERVER_PORT=8080
SERVER_HOST=0.0.0.0

# Scheduler
FULL_SYNC_SCHEDULE="0 2 * * *"  # Каждый день в 02:00
INCREMENTAL_SYNC_INTERVAL_MINUTES=30
SYNC_TIMEOUT_HOURS=6  # Таймаут для полной синхронизации

# Logging
LOG_LEVEL=info
LOG_FORMAT=json

# CORS
CORS_ALLOW_ORIGINS=*
```

### 6. Обработка ошибок

#### HTTP статус коды
- `200` - успешный запрос
- `400` - неверные параметры запроса
- `404` - ресурс не найден
- `500` - внутренняя ошибка сервера
- `503` - сервис временно недоступен

#### Формат ошибки
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid pagination parameters",
    "details": {
      "page": "must be greater than 0",
      "limit": "must be between 1 and 100"
    }
  }
}
```

### 7. Логирование

#### Уровни логирования
- `DEBUG` - детальная отладочная информация
- `INFO` - общая информация о работе приложения
- `WARN` - предупреждения
- `ERROR` - ошибки

#### Структурированное логирование
```json
{
  "level": "info",
  "timestamp": "2024-01-15T10:30:00Z",
  "message": "Sync completed",
  "source": "dongchedi",
  "new_cars": 15,
  "duration_ms": 2500
}
```

### 8. Производительность

#### Требования
- Время ответа API: < 200ms для простых запросов
- Время ответа API с пагинацией: < 500ms
- Поддержка до 1000 одновременных запросов
- Эффективное использование памяти
- Полная синхронизация: может занимать до 6 часов
- Инкрементальная синхронизация: < 5 минут

#### Оптимизации
- Использование connection pool для БД
- Кэширование часто запрашиваемых данных
- Оптимизированные SQL запросы с индексами
- Асинхронная обработка синхронизации
- Batch операции для массовой вставки/обновления данных
- Параллельная обработка страниц при полной синхронизации
- Graceful shutdown для длительных операций

### 9. Безопасность

#### Меры безопасности
- Валидация всех входных параметров
- Защита от SQL инъекций
- Ограничение размера запросов
- CORS настройки
- Логирование подозрительной активности

### 10. Мониторинг

#### Метрики для отслеживания
- Количество запросов к API
- Время ответа API
- Количество ошибок
- Статус синхронизации (полная/инкрементальная)
- Время выполнения синхронизации
- Прогресс длительных операций
- Количество машин по источникам
- Использование ресурсов (CPU, память, БД)

#### Health check endpoint
**GET /health**
- Проверка состояния приложения
- Проверка подключения к БД
- Проверка доступности Python API

## Технические требования

### Зависимости
```go
require (
    github.com/gin-gonic/gin v1.9.1          // HTTP framework
    github.com/lib/pq v1.10.9                // PostgreSQL driver
    github.com/jmoiron/sqlx v1.3.5           // SQL utilities
    github.com/robfig/cron/v3 v3.0.1         // Scheduler
    github.com/spf13/viper v1.16.0           // Configuration
    github.com/sirupsen/logrus v1.9.3        // Logging
    github.com/gin-contrib/cors v1.4.0       // CORS middleware
    github.com/go-playground/validator/v10 v10.14.0 // Validation
)
```

### Версии
- Go 1.24.5+
- PostgreSQL 12+
- Gin framework для HTTP API
- SQLx для работы с БД

## План разработки

### Этап 1: Базовая структура
1. Настройка проекта и зависимостей
2. Конфигурация и подключение к БД
3. Модели данных
4. Базовые миграции

### Этап 2: API и сервисы
1. HTTP API с пагинацией
2. Сервисы для работы с данными
3. Интеграция с Python API
4. Обработка ошибок и валидация

### Этап 3: Синхронизация
1. Планировщик задач (полная и инкрементальная синхронизация)
2. Логика синхронизации с поддержкой длительных операций
3. Мониторинг прогресса синхронизации
4. Обработка ошибок и retry с экспоненциальной задержкой
5. Логирование с временными метками
6. Graceful shutdown для длительных операций

### Этап 4: Оптимизация и тестирование
1. Оптимизация производительности
2. Написание тестов
3. Документация API
4. Развертывание 