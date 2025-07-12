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
├── interfaces/
│   ├── parser.go          # Интерфейс для парсеров
│   ├── car_repository.go  # Интерфейс для работы с БД
│   └── sync_service.go    # Интерфейс для синхронизации
├── services/
│   ├── car_service.go      # Бизнес-логика работы с машинами
│   ├── sync_service.go     # Сервис синхронизации
│   └── parser_factory.go   # Фабрика для создания парсеров
├── parsers/
│   ├── dongchedi.go       # Реализация парсера Dongchedi
│   ├── che168.go          # Реализация парсера Che168
│   └── base.go            # Базовая структура парсера
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
  - **Расширяемость**: Легкое добавление новых парсеров через интерфейсы
- **Поле источника**: В БД сохраняется источник данных (dongchedi/che168/...) в зависимости от используемого парсера
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
CREATE INDEX idx_cars_city ON cars(car_source_city_name);
CREATE INDEX idx_cars_series ON cars(series_name);

-- Индексы для поиска
CREATE INDEX idx_cars_title_gin ON cars USING gin(to_tsvector('russian', title));
CREATE INDEX idx_cars_car_name_gin ON cars USING gin(to_tsvector('russian', car_name));
CREATE INDEX idx_cars_brand_name_gin ON cars USING gin(to_tsvector('russian', brand_name));
CREATE INDEX idx_cars_series_name_gin ON cars USING gin(to_tsvector('russian', series_name));

-- Составные индексы для фильтров
CREATE INDEX idx_cars_brand_year ON cars(brand_name, car_year);
CREATE INDEX idx_cars_brand_price ON cars(brand_name, sh_price);
CREATE INDEX idx_cars_city_price ON cars(car_source_city_name, sh_price);
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

**GET /api/cars/search**
- Поиск машин по текстовому запросу
- Параметры запроса:
  - `q` (string, required) - поисковый запрос
  - `page` (int, default: 1) - номер страницы
  - `limit` (int, default: 20, max: 100) - количество машин на странице
  - `source` (string) - фильтр по источнику
  - `sort_by` (string) - поле для сортировки
  - `sort_order` (string) - порядок сортировки
- Поиск осуществляется по полям: title, car_name, brand_name, series_name

**GET /api/cars/filters**
- Получение доступных фильтров и их значений
- Возвращает:
  - Список брендов с количеством машин
  - Список городов с количеством машин
  - Диапазон цен (min/max)
  - Диапазон лет (min/max)
  - Список источников с количеством машин

**GET /api/cars/{id}**
- Получение детальной информации о машине по ID

**GET /api/cars/sources**
- Получение статистики по источникам данных
- Возвращает:
  - Количество машин по каждому источнику
  - Список всех доступных источников
  - Статус каждого источника (active/inactive)

**GET /api/cars/brands**
- Получение списка всех брендов с количеством машин
- Параметры:
  - `search` (string) - поиск по названию бренда
  - `limit` (int, default: 50) - количество результатов

**GET /api/cars/cities**
- Получение списка всех городов с количеством машин
- Параметры:
  - `search` (string) - поиск по названию города
  - `limit` (int, default: 50) - количество результатов

**GET /api/cars/series**
- Получение списка всех серий с количеством машин
- Параметры:
  - `brand` (string) - фильтр по бренду
  - `search` (string) - поиск по названию серии
  - `limit` (int, default: 50) - количество результатов

**GET /api/cars/price-range**
- Получение статистики по ценам
- Возвращает:
  - Минимальную и максимальную цену
  - Медианную цену
  - Среднюю цену
  - Количество машин в разных ценовых диапазонах

**GET /api/cars/year-range**
- Получение статистики по годам
- Возвращает:
  - Минимальный и максимальный год
  - Количество машин по годам
  - Популярные годы

#### Endpoints для управления синхронизацией

**POST /api/sync/{source}**
- Принудительная синхронизация данных с указанным источником
- Параметры:
  - `source` (string) - источник данных (dongchedi, che168, ...)
  - `full_sync` (bool, default: false) - полная синхронизация или инкрементальная
  - `force` (bool, default: false) - принудительный запуск даже если уже выполняется

**POST /api/sync/all**
- Синхронизация всех доступных источников
- Параметры:
  - `full_sync` (bool, default: false) - полная синхронизация или инкрементальная
  - `parallel` (bool, default: true) - параллельная или последовательная синхронизация

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
- Время ответа API поиска: < 300ms
- Время ответа API фильтров: < 100ms
- Поддержка до 1000 одновременных запросов
- Эффективное использование памяти
- Полная синхронизация: может занимать до 6 часов
- Инкрементальная синхронизация: < 5 минут

#### Оптимизации
- Использование connection pool для БД
- Кэширование часто запрашиваемых данных (фильтры, статистика)
- Оптимизированные SQL запросы с индексами
- Full-text поиск с использованием PostgreSQL GIN индексов
- Асинхронная обработка синхронизации
- Batch операции для массовой вставки/обновления данных
- Параллельная обработка страниц при полной синхронизации
- Graceful shutdown для длительных операций
- Кэширование результатов поиска и фильтров

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

## Архитектурные принципы

### Интерфейсы и расширяемость
- **Интерфейс Parser**: Единый интерфейс для всех парсеров
- **Интерфейс CarRepository**: Абстракция для работы с БД
- **Интерфейс SyncService**: Абстракция для синхронизации
- **Фабрика парсеров**: Динамическое создание парсеров по имени
- **Dependency Injection**: Внедрение зависимостей через интерфейсы

### Добавление нового парсера
1. Реализовать интерфейс `Parser`
2. Добавить конфигурацию в `config.go`
3. Зарегистрировать в фабрике парсеров
4. Добавить в планировщик (опционально)

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
    github.com/google/wire v0.5.0            // Dependency injection
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
2. Определение интерфейсов (Parser, CarRepository, SyncService)
3. Конфигурация и подключение к БД
4. Модели данных
5. Базовые миграции
6. Фабрика парсеров

### Этап 2: API и сервисы
1. HTTP API с пагинацией
2. Сервисы для работы с данными (через интерфейсы)
3. Реализация парсеров (Dongchedi, Che168)
4. Интеграция с Python API
5. Обработка ошибок и валидация
6. Dependency injection

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