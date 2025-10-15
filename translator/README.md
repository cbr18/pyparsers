# Translator Service

Асинхронный сервис перевода автомобильных данных с кэшированием в Redis.

## 🚀 Возможности

- **Перевод одиночного текста** - `POST /translate/text`
- **Перевод JSON объектов** - `POST /translate/json`
- **Батчевый перевод базы данных** - `POST /translate/db`
- **Кэширование в Redis** - автоматическое кэширование переводов
- **Retry/Backoff** - автоматические повторы при ошибках API
- **Асинхронная архитектура** - FastAPI + httpx + redis

## 📦 Технологии

- **Python 3.13**
- **FastAPI** - веб-фреймворк
- **httpx** - HTTP клиент
- **redis** - Redis клиент
- **uvicorn** - ASGI сервер
- **Docker** - контейнеризация

## 🛠 Установка и запуск

### 1. Настройка переменных окружения

Убедитесь, что в файле `CarsParser/.env` есть необходимые переменные:

```env
YANDEX_API_KEY=your_api_key_here
YANDEX_FOLDER_ID=your_folder_id_here
REDIS_HOST=redis
REDIS_PORT=6379
```

Сервис переводчика автоматически использует основной `.env` файл из корня проекта.

### 2. Запуск через Docker Compose

```bash
# Из корня проекта CarsParser - запуск всех сервисов
docker compose up --build

# Из корня проекта CarsParser - запуск только переводчика
docker compose up translator redis --build

# Из папки translator - запуск только переводчика
cd translator
docker compose up --build
```

### 3. Локальная разработка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск Redis (отдельный терминал)
docker run -d -p 6379:6379 redis:7.2-alpine

# Запуск сервиса
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 API Документация

После запуска сервиса доступна документация:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔧 API Эндпоинты

### 1. Перевод текста

```bash
curl -X POST "http://localhost:8000/translate/text" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "极狐阿尔法S",
    "source_lang": "zh",
    "target_lang": "ru"
  }'
```

### 2. Перевод JSON

```bash
curl -X POST "http://localhost:8000/translate/json" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "brand": "极狐",
      "model": "阿尔法S",
      "city": "北京"
    },
    "source_lang": "zh",
    "target_lang": "ru"
  }'
```

### 3. Перевод базы данных

```bash
curl -X POST "http://localhost:8000/translate/db" \
  -H "Content-Type: application/json" \
  -d '{
    "records": [
      {
        "title": "极狐阿尔法S",
        "brand_name": "极狐",
        "city": "北京"
      }
    ],
    "source_lang": "zh",
    "target_lang": "ru"
  }'
```

### 4. Статистика

```bash
# Статистика переводов
curl "http://localhost:8000/translate/stats"

# Статистика кэша
curl "http://localhost:8000/translate/cache/stats"

# Очистка кэша
curl -X POST "http://localhost:8000/translate/cache/clear"
```

## 🏗 Архитектура

```
app/
├── main.py              # Основной файл приложения
├── api/
│   └── translate.py     # API эндпоинты
├── services/
│   ├── translator.py    # Сервис перевода
│   └── cache.py         # Сервис кэширования
└── utils/
    └── batcher.py       # Утилиты для батчинга
```

## 🔄 Интеграция с DataHub

Сервис интегрирован с DataHub для автоматического перевода данных автомобилей:

1. **Автоматический перевод** - все данные переводятся перед сохранением в БД
2. **Кэширование** - повторные переводы берутся из кэша
3. **Fallback** - при недоступности сервиса используются исходные данные
4. **Батчевая обработка** - эффективная обработка больших объемов данных

## 📊 Мониторинг

- **Health Check**: `GET /translate/health`
- **Логирование** - подробные логи всех операций
- **Метрики** - статистика переводов и кэша
- **Retry логика** - автоматические повторы при ошибках

## 🚨 Обработка ошибок

- **Rate Limiting** - автоматические повторы с экспоненциальной задержкой
- **Таймауты** - настраиваемые таймауты для HTTP запросов
- **Fallback** - использование исходных данных при ошибках перевода
- **Логирование** - детальное логирование всех ошибок

## 🔧 Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `YANDEX_API_KEY` | API ключ Yandex Cloud | - |
| `YANDEX_FOLDER_ID` | ID папки Yandex Cloud | - |
| `REDIS_HOST` | Хост Redis | `redis` |
| `REDIS_PORT` | Порт Redis | `6379` |

### Настройки перевода

- **Языки**: китайский (zh) → русский (ru)
- **Батч размер**: 10 элементов
- **Retry**: 3 попытки с экспоненциальной задержкой
- **Таймаут**: 30 секунд

## 📈 Производительность

- **Асинхронность** - обработка множественных запросов
- **Кэширование** - снижение нагрузки на API
- **Батчинг** - эффективная обработка групп данных
- **Connection Pooling** - переиспользование HTTP соединений

## 🧪 Тестирование

```bash
# Запуск тестовых данных
python test_data.py

# Тестирование API
curl -X POST "http://localhost:8000/translate/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "极狐", "source_lang": "zh", "target_lang": "ru"}'
```

## 📝 Логи

Сервис ведет подробные логи:
- Подключение к Redis
- Обращения к Yandex API
- Использование кэша
- Ошибки и retry
- Статистика переводов

## 🚀 Быстрый запуск

```bash
# Вариант 1: Из корня проекта CarsParser (рекомендуется)
cd /home/alex/CarsParser
docker compose up translator redis --build

# Вариант 2: Из папки translator
cd /home/alex/CarsParser/translator
./start.sh

# Вариант 3: Через docker-compose в папке translator
cd /home/alex/CarsParser/translator
docker compose up --build
```

**Примечание:** Убедитесь, что в файле `CarsParser/.env` настроены переменные `YANDEX_API_KEY` и `YANDEX_FOLDER_ID`.
