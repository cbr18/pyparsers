# CarCatch API Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Service Details](#service-details)
   - [pyparsers-dongchedi (Python FastAPI)](#pyparsers-dongchedi-python-fastapi)
   - [pyparsers-che168 (Python FastAPI)](#pyparsers-che168-python-fastapi)
   - [datahub (Go Gin)](#datahub-go-gin)
   - [telegrambot (Node.js Express)](#telegrambot-nodejs-express)
   - [telegramapp (React)](#telegramapp-react)
   - [telegramngapp (Angular)](#telegramngapp-angular)
4. [Common Data Models](#common-data-models)
5. [Error Handling](#error-handling)

## System Overview

CarCatch - это микросервисная система для парсинга, хранения и отображения информации об автомобилях с китайских сайтов dongchedi.com и che168.com. Система состоит из нескольких взаимосвязанных сервисов, каждый из которых выполняет свою специфическую функцию.

### Key Features
- Асинхронный парсинг автомобилей с внешних источников
- Централизованное хранение данных в PostgreSQL
- REST API для управления данными
- Веб-интерфейсы для просмотра автомобилей
- Telegram бот для обработки заявок
- Система фильтрации и поиска

## Architecture

### Service Dependencies

```
nginx (80/443)
├── pyparsers-dongchedi (5001) - Парсинг dongchedi
├── pyparsers-che168 (5002) - Парсинг che168
├── datahub (8080) - Управление данными
├── telegrambot (3001) - Telegram бот
├── telegramapp (3002) - React веб-приложение
└── telegramngapp - Angular веб-приложение

postgres (5432) - База данных
```

### Technology Stack
- **Backend:** Python (FastAPI), Go (Gin), Node.js (Express)
- **Frontend:** React, Angular
- **Database:** PostgreSQL
- **Infrastructure:** Docker, nginx
- **Message Queue:** Telegram Bot API

## Service Details

### pyparsers-dongchedi (Python FastAPI)

**Port:** 5001  
**Technology:** Python 3.x, FastAPI, asyncio  
**Purpose:** Асинхронный парсинг автомобилей с dongchedi.com

#### Root Endpoints

##### GET /
Корневой эндпоинт API с информацией о доступных маршрутах.

**Response:**
```json
{
  "data": {
    "name": "Async Car Parsers API",
    "version": "1.0.0",
    "description": "Асинхронный API для парсинга информации о машинах с различных источников",
    "endpoints": {
      "dongchedi": "/cars/dongchedi",
      "dongchedi_page": "/cars/dongchedi/page/{page}",
      "dongchedi_all": "/cars/dongchedi/all",
      "dongchedi_incremental": "/cars/dongchedi/incremental",
      "dongchedi_car": "/cars/dongchedi/car/{car_id}",
      "dongchedi_cars": "/cars/dongchedi/cars",
      "health": "/health",
      "docs": "/docs",
      "redoc": "/redoc"
    }
  },
  "message": "Welcome to Async Car Parsers API",
  "status": 200
}
```

##### GET /health
Проверка работоспособности API.

**Response:**
```json
{
  "data": {
    "status": "ok",
    "timestamp": "2025-01-09T10:30:00.000Z",
    "services": {
      "dongchedi_parser": "available",
      "che168_parser": "available"
    }
  },
  "message": "Service is healthy",
  "status": 200
}
```

#### Dongchedi Endpoints

##### GET /cars/dongchedi
Получает первую страницу автомобилей с dongchedi (фильтр по году >= 2017).

**Response:**
```json
{
  "data": {
    "has_more": true,
    "search_sh_sku_info_list": [
      {
        "car_id": "123456",
        "brand_name": "BMW",
        "car_name": "X5",
        "year": "2020",
        "city": "北京",
        "sh_price": "450000",
        "sort_number": 100,
        "source": "dongchedi",
        "link": "https://dongchedi.com/car/123456"
      }
    ],
    "total": 1500
  },
  "message": "Success",
  "status": 200
}
```

##### GET /cars/dongchedi/page/{page}
Получает конкретную страницу автомобилей с dongchedi.

**Parameters:**
- `page` (path, required): Номер страницы (начиная с 1)

**Response:** Аналогично `/cars/dongchedi` с добавлением `current_page`

##### GET /cars/dongchedi/all
Получает все автомобили со всех страниц dongchedi с оптимизацией памяти.

**Response:**
```json
{
  "data": {
    "search_sh_sku_info_list": [...],
    "total": 15000
  },
  "message": "Загружено 15000 машин со всех страниц.",
  "status": 200
}
```

##### POST /cars/dongchedi/incremental
Получает только новые автомобили до первого совпадения с существующими.

**Request Body:**
```json
{
  "existing_cars": [
    {
      "car_id": "123456",
      "source": "dongchedi"
    }
  ]
}
```

**Response:**
```json
{
  "data": {
    "search_sh_sku_info_list": [...],
    "total": 50,
    "pages_checked": 3
  },
  "message": "Найдено 50 новых машин на 3 страницах.",
  "status": 200
}
```

##### GET /cars/dongchedi/car/{car_id}
Получает детальную информацию о конкретном автомобиле.

**Parameters:**
- `car_id` (path, required): ID автомобиля

**Response:**
```json
{
  "data": {
    "car_id": "123456",
    "brand_name": "BMW",
    "car_name": "X5",
    "detailed_info": "...",
    "is_available": true,
    "source": "dongchedi"
  },
  "message": "Success",
  "status": 200
}
```

##### POST /cars/dongchedi/cars
Получает детальную информацию о нескольких автомобилях (максимум 20).

**Request Body:**
```json
{
  "car_ids": ["123456", "789012", "345678"]
}
```

**Response:**
```json
{
  "data": {
    "cars": [
      {
        "car": {...},
        "meta": {...},
        "status": 200
      }
    ],
    "total": 3,
    "successful": 3
  },
  "message": "Получена информация о машинах",
  "status": 200
}
```

##### GET /cars/dongchedi/stats
Получает статистику по автомобилям с dongchedi.

**Response:**
```json
{
  "data": {
    "total_cars": 15000,
    "has_more_pages": true,
    "cars_on_first_page": 20,
    "top_brands": {
      "BMW": 1200,
      "Mercedes-Benz": 1100,
      "Audi": 950
    },
    "timestamp": "2025-01-09T10:30:00.000Z"
  },
  "message": "Статистика по машинам с dongchedi",
  "status": 200
}
```

#### Che168 Endpoints

##### GET /cars/che168
Получает первую страницу автомобилей с che168 (фильтр по году >= 2017).

**Response:** Аналогично dongchedi, но с `source: "che168"`

##### GET /cars/che168/page/{page}
Получает конкретную страницу автомобилей с che168.

**Parameters:**
- `page` (path, required): Номер страницы (начиная с 1)

##### GET /cars/che168/all
Получает все автомобили со всех страниц che168 (максимум 100 страниц).

##### POST /cars/che168/incremental
Инкрементальное обновление для che168.

**Request Body:** Аналогично dongchedi

##### POST /cars/che168/car
Получает детальную информацию об автомобиле che168 по URL.

**Request Body:**
```json
{
  "car_url": "https://che168.com/car/123456"
}
```

#### Update Endpoints

##### GET /update/dongchedi/full
Полное обновление данных dongchedi (используется Go-приложением).

**Response:**
```json
{
  "count": 15000,
  "status": "ok"
}
```

##### GET /update/che168/full
Полное обновление данных che168 (используется Go-приложением).

**Response:**
```json
{
  "count": 8000,
  "status": "ok"
}
```

## Common Data Models

### Car Entity
```json
{
  "uuid": "string",
  "car_id": "string|number",
  "brand_name": "string",
  "car_name": "string", 
  "series_name": "string",
  "year": "string",
  "city": "string",
  "price": "string",
  "sh_price": "string",
  "mileage": "string",
  "source": "dongchedi|che168",
  "sort_number": "number",
  "link": "string",
  "image": "string",
  "car_source_city_name": "string",
  "car_source_type": "string",
  "transfer_cnt": "string"
}
```

### Filter Parameters
```json
{
  "page": "number (default: 1)",
  "limit": "number (default: 20)",
  "source": "string (dongchedi|che168)",
  "brand": "string",
  "city": "string", 
  "year": "string",
  "search": "string"
}
```

### Brand Entity
```json
{
  "id": "number",
  "name": "string",
  "count": "number"
}
```

## Error Handling

### Standard Error Response Format
```json
{
  "error": "string",
  "message": "string", 
  "status": "number"
}
```

### Success Response Format
```json
{
  "data": "object|array",
  "message": "string",
  "status": "number",
  "performance": {
    "execution_time_ms": "number",
    "memory_usage_mb": "number",
    "request_timestamp": "string",
    "response_timestamp": "string"
  }
}
```

### Common HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found
- `500` - Internal Server Error

### datahub (Go Gin)

**Port:** 8080  
**Technology:** Go 1.24, Gin, GORM, PostgreSQL  
**Purpose:** Центральный API для управления данными автомобилей, фильтрации и поиска

#### Cars Management

##### GET /cars
Получает список автомобилей с фильтрами и пагинацией.

**Query Parameters:**
- `page` (optional): Номер страницы (default: 1)
- `limit` (optional): Размер страницы (default: 20)
- `source` (optional): Источник (dongchedi|che168)
- `brand` (optional): Бренд автомобиля
- `city` (optional): Город
- `year` (optional): Год выпуска
- `search` (optional): Поисковый запрос

**Example Request:**
```
GET /cars?page=1&limit=10&source=dongchedi&brand=BMW&city=北京
```

**Response:**
```json
{
  "data": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "car_id": "123456",
      "brand_name": "BMW",
      "car_name": "X5",
      "series_name": "X系列",
      "year": "2020",
      "city": "北京",
      "price": "450000",
      "source": "dongchedi",
      "sort_number": 100,
      "link": "https://dongchedi.com/car/123456"
    }
  ],
  "total": 1500
}
```

##### POST /checkcar
Проверяет наличие и получает детали автомобиля по источнику и ID/URL.

**Request Body:**
```json
{
  "source": "dongchedi",
  "car_id": "123456",
  "car_url": "https://che168.com/car/123456"
}
```

**Note:** Для dongchedi используется `car_id`, для che168 - `car_url`

**Response:**
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "car_id": "123456",
  "brand_name": "BMW",
  "car_name": "X5",
  "is_available": true,
  "source": "dongchedi",
  "detailed_info": "..."
}
```

#### Update Operations

##### GET /update/{source}/full
Запускает полное обновление данных для источника.

**Parameters:**
- `source` (path, required): Источник (dongchedi|che168)

**Example Request:**
```
GET /update/dongchedi/full
```

**Response:**
```json
{
  "status": "ok",
  "count": 15000
}
```

**Error Response:**
```json
{
  "error": "unknown source"
}
```

##### POST /update/{source}
Запускает инкрементальное обновление последних N записей.

**Parameters:**
- `source` (path, required): Источник (dongchedi|che168)

**Request Body:**
```json
{
  "last_n": 5
}
```

**Response:**
```json
{
  "status": "ok"
}
```

**Warning Response (duplicate records):**
```json
{
  "status": "warning",
  "message": "Некоторые записи уже существуют в базе данных",
  "error": "Обнаружены дубликаты записей",
  "details": "duplicate key value violates unique constraint..."
}
```

#### Brands Management

##### GET /brands
Получает список всех брендов автомобилей.

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "BMW",
      "count": 1200
    },
    {
      "id": 2,
      "name": "Mercedes-Benz", 
      "count": 1100
    },
    {
      "id": 3,
      "name": "Audi",
      "count": 950
    }
  ]
}
```

#### Documentation

##### GET /swagger/*
Swagger UI документация для API.

**Example:** `GET /swagger/index.html`
### telegrambot (Node.js Express)

**Port:** 3001  
**Technology:** Node.js, Express, Telegraf  
**Purpose:** Telegram бот для обработки заявок на автомобили и webhook интеграция

#### Telegram Bot Commands

##### /start
Приветственное сообщение с кнопкой для открытия веб-приложения.

**Response:**
```
Бот для заявок CarCatch активен!

Открыть веб-приложение:
[🚗 Открыть подбор авто] -> https://car-catch.ru/podbortg
```

#### API Endpoints

##### POST /lead
Принимает заявки на автомобили от фронтенда и отправляет их в Telegram.

**Request Body:**
```json
{
  "car": {
    "brand_name": "BMW",
    "car_name": "X5",
    "year": "2020",
    "city": "北京",
    "price": "450000",
    "link": "https://dongchedi.com/car/123456"
  },
  "user": "Иван Иванов (опционально)"
}
```

**Success Response:**
```json
{
  "ok": true
}
```

**Error Response:**
```json
{
  "error": "No car data provided"
}
```

**Telegram Message Format:**
```
🚗 Новая заявка с сайта
Пользователь: Иван Иванов
Бренд: BMW
Модель: X5
Год: 2020
Город: 北京
Цена: 450000
Ссылка: https://dongchedi.com/car/123456
```

##### POST /bot
Webhook эндпоинт для получения обновлений от Telegram Bot API.

**Note:** Используется автоматически Telegram для отправки обновлений боту.

#### Configuration

**Environment Variables:**
- `TELEGRAM_BOT_TOKEN` - Токен Telegram бота
- `LEAD_TARGET_CHAT` - ID чата или username для отправки заявок (default: @Maksim_CarCatch)
- `PORT` - Порт сервера (default: 3001)
### telegramapp (React)

**Port:** 3002 (через nginx на 80)  
**Technology:** React, JavaScript  
**Purpose:** Веб-интерфейс для просмотра, фильтрации и поиска автомобилей

#### Main Components

##### App Component
Основной компонент приложения, управляющий состоянием и данными.

**State Management:**
- `cars` - Список автомобилей
- `loading` - Состояние загрузки
- `error` - Ошибки
- `page`, `limit` - Пагинация
- `filters` - Фильтры поиска
- `brands` - Список брендов

##### CarCard Component
Компонент для отображения карточки автомобиля.

**Props:**
- `car` - Объект автомобиля

##### Filters Component
Компонент фильтров для поиска автомобилей.

**Props:**
- `tempFilters` - Временные фильтры
- `setTempFilters` - Функция обновления фильтров
- `applyFilters` - Применение фильтров
- `resetFilters` - Сброс фильтров
- `sources` - Доступные источники
- `brands` - Список брендов

##### Pagination Component
Компонент пагинации.

**Props:**
- `page` - Текущая страница
- `limit` - Размер страницы
- `total` - Общее количество
- `handlePageChange` - Обработчик смены страницы

#### API Integration

##### fetchCars(page, limit, filters)
Получает список автомобилей с сервера.

**API Call:** `GET /cars?page={page}&limit={limit}&source={source}&brand={brand}&city={city}&year={year}&search={search}`

##### fetchBrands()
Получает список брендов.

**API Call:** `GET /brands`

##### sendLeadRequest(car, user)
Отправляет заявку на автомобиль.

**API Call:** `POST /lead`

#### Features
- Фильтрация по источнику, бренду, городу, году
- Поиск по тексту
- Пагинация (5, 10, 20, 50 на странице)
- Отправка заявок через Telegram бот
- Адаптивный дизайн
- Обработка ошибок

### telegramngapp (Angular)

**Port:** Not specified (через nginx)  
**Technology:** Angular, TypeScript  
**Purpose:** Альтернативный веб-интерфейс на Angular для просмотра автомобилей

#### Main Components

##### App Component
Корневой компонент приложения.

**Imports:**
- `RouterOutlet` - Маршрутизация
- `HttpClientModule` - HTTP клиент
- `CarList` - Компонент списка автомобилей

##### CarList Component
Компонент для отображения списка автомобилей.

**Properties:**
- `cars: Car[]` - Массив автомобилей
- `loading: boolean` - Состояние загрузки
- `placeholder: string` - Заглушка для изображений

**Methods:**
- `ngOnInit()` - Инициализация, загрузка данных
- `onImgError(event)` - Обработка ошибок загрузки изображений

#### Car Interface
```typescript
interface Car {
  image?: string;
  title?: string;
  sh_price?: string;
  car_year?: string;
  car_mileage?: string;
  car_source_city_name?: string;
  brand_name?: string;
  series_name?: string;
  car_name?: string;
  car_source_type?: string;
  transfer_cnt?: string;
}
```

#### API Integration

##### GET /cars
Загружает список автомобилей при инициализации компонента.

**Implementation:**
```typescript
this.http.get<any>('/cars').subscribe({
  next: (data) => {
    this.cars = data?.data?.search_sh_sku_info_list ?? [];
    this.loading = false;
  },
  error: () => {
    this.loading = false;
    alert('Ошибка загрузки данных');
  }
});
```

#### Features
- Отображение списка автомобилей
- Обработка ошибок загрузки изображений
- Индикатор загрузки
- Обработка ошибок API
- TypeScript типизация
---

## Additional Information

### Service Ports Summary
- **nginx:** 80, 443 (HTTP/HTTPS)
- **pyparsers-dongchedi:** 5001 (Python FastAPI)
- **pyparsers-che168:** 5002 (Python FastAPI)
- **datahub:** 8080 (Go Gin)
- **telegrambot:** 3001 (Node.js Express)
- **telegramapp:** 3002 (React, served via nginx)
- **postgres:** 5432 (Database)

### API Documentation URLs
- **pyparsers-dongchedi:** `http://localhost:5001/docs`
- **pyparsers-che168:** `http://localhost:5002/docs`
- **datahub:** `http://localhost:8080/swagger/index.html` (Swagger)

### Data Flow
1. **Parsing:** pyparsers-dongchedi / pyparsers-che168 → External sources
2. **Storage:** parser services → datahub → PostgreSQL
3. **Frontend:** telegramapp/telegramngapp → datahub → PostgreSQL
4. **Notifications:** telegramapp → telegrambot → Telegram API

### Common Use Cases

#### 1. Get Cars with Filters
```bash
# Get BMW cars from dongchedi in Beijing
curl "http://localhost:8080/cars?source=dongchedi&brand=BMW&city=北京&page=1&limit=10"
```

#### 2. Submit Lead Request
```bash
curl -X POST http://localhost:3001/lead \
  -H "Content-Type: application/json" \
  -d '{
    "car": {
      "brand_name": "BMW",
      "car_name": "X5",
      "year": "2020",
      "city": "北京",
      "price": "450000"
    },
    "user": "John Doe"
  }'
```

#### 3. Update Car Data
```bash
# Full update from dongchedi
curl http://localhost:8080/update/dongchedi/full

# Incremental update
curl -X POST http://localhost:8080/update/dongchedi \
  -H "Content-Type: application/json" \
  -d '{"last_n": 10}'
```

### Performance Features
- **Async Processing:** the parser services use asyncio for concurrent parsing
- **Memory Optimization:** Duplicate detection using sets for memory efficiency
- **Performance Monitoring:** parser responses include execution time and memory usage where supported
- **Incremental Updates:** Only fetch new cars to minimize processing time

### Error Handling Best Practices
- All services return consistent error response formats
- HTTP status codes follow REST conventions
- Detailed error messages for debugging
- Graceful degradation for missing data

---

*Last updated: January 2025*  
*Generated for CarCatch API Documentation*
