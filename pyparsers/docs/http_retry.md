# Механизм повторных попыток для HTTP-запросов

В этом документе описывается механизм повторных попыток для HTTP-запросов, реализованный в модулях `retry.py` и `http_client.py`.

## Обзор

Механизм повторных попыток позволяет автоматически повторять HTTP-запросы в случае временных ошибок, таких как:
- Ошибки сети (обрыв соединения, таймауты)
- Серверные ошибки (коды состояния 5xx)
- Другие временные ошибки, которые могут быть устранены при повторном запросе

Кроме того, реализован паттерн Circuit Breaker, который предотвращает каскадные отказы при недоступности внешних сервисов.

## Основные компоненты

### RetryStrategy

Класс `RetryStrategy` определяет стратегию повторных попыток:

```python
from api.retry import RetryStrategy

strategy = RetryStrategy(
    max_retries=3,                           # Максимальное количество повторных попыток
    retry_delay=1.0,                         # Начальная задержка между попытками в секундах
    backoff_factor=2.0,                      # Множитель для экспоненциальной задержки
    jitter=True,                             # Добавлять случайное отклонение к задержке
    retry_on_status_codes=[500, 502, 503, 504],  # Коды состояния HTTP для повторных попыток
    retry_on_exceptions=[ValueError, TypeError]   # Исключения для повторных попыток
)
```

### CircuitBreaker

Класс `CircuitBreaker` реализует паттерн Circuit Breaker:

```python
from api.retry import CircuitBreaker

circuit_breaker = CircuitBreaker(
    failure_threshold=5,       # Порог количества ошибок для перехода в состояние OPEN
    recovery_timeout=30.0,     # Время в секундах, через которое происходит переход из OPEN в HALF_OPEN
    half_open_max_calls=3,     # Максимальное количество запросов в состоянии HALF_OPEN
    reset_timeout=60.0         # Время в секундах, через которое сбрасывается счетчик ошибок
)
```

### Декораторы

Модуль `retry.py` предоставляет два декоратора для повторных попыток:

- `async_retry` - для асинхронных функций
- `sync_retry` - для синхронных функций

```python
from api.retry import async_retry, sync_retry, RetryStrategy, CircuitBreaker

# Для асинхронных функций
@async_retry(retry_strategy=strategy, circuit_breaker=circuit_breaker, endpoint="my_endpoint")
async def my_async_function():
    # ...

# Для синхронных функций
@sync_retry(retry_strategy=strategy, circuit_breaker=circuit_breaker, endpoint="my_endpoint")
def my_sync_function():
    # ...
```

## Использование с HTTP-клиентом

HTTP-клиент (`HTTPClient`) автоматически использует механизм повторных попыток для всех запросов:

```python
from api.http_client import HTTPClient

# Создаем HTTP-клиент с настраиваемой стратегией повторных попыток
client = HTTPClient(
    base_url="https://example.com",
    max_retries=3,
    retry_delay=1.0,
    backoff_factor=2.0,
    jitter=True,
    retry_on_status_codes=[500, 502, 503, 504],
    retry_on_exceptions=[aiohttp.ClientError, asyncio.TimeoutError]
)

# Асинхронные запросы
status, data, text = await client.get("/api/v1/resource")
status, data, text = await client.post("/api/v1/resource", json_data={"key": "value"})

# Синхронные запросы (для обратной совместимости)
response = client.sync_get("/api/v1/resource")
response = client.sync_post("/api/v1/resource", json={"key": "value"})
```

## Глобальные экземпляры

Модуль `retry.py` предоставляет глобальные экземпляры для использования в приложении:

```python
from api.retry import default_retry_strategy, default_circuit_breaker

# Использование глобальной стратегии повторных попыток
@async_retry(retry_strategy=default_retry_strategy, circuit_breaker=default_circuit_breaker, endpoint="my_endpoint")
async def my_function():
    # ...
```

## Настройка логирования

Механизм повторных попыток использует стандартный модуль `logging` для логирования информации о повторных попытках и состоянии Circuit Breaker:

```python
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api.retry")
logger.setLevel(logging.DEBUG)
```

## Примеры

### Пример 1: Асинхронный запрос с повторными попытками

```python
import asyncio
from api.http_client import http_client

async def fetch_data():
    status, data, text = await http_client.get("https://example.com/api/v1/resource")
    if status == 200:
        return data
    else:
        return None

# Выполняем запрос
result = asyncio.run(fetch_data())
```

### Пример 2: Настройка собственной стратегии повторных попыток

```python
from api.http_client import HTTPClient
import aiohttp
import asyncio

# Создаем HTTP-клиент с настраиваемой стратегией повторных попыток
client = HTTPClient(
    max_retries=5,
    retry_delay=0.5,
    backoff_factor=1.5,
    jitter=True,
    retry_on_status_codes=[429, 500, 502, 503, 504],
    retry_on_exceptions=[aiohttp.ClientError, asyncio.TimeoutError]
)

# Выполняем запрос
status, data, text = asyncio.run(client.get("https://example.com/api/v1/resource"))
```

### Пример 3: Использование декоратора async_retry напрямую

```python
import asyncio
from api.retry import async_retry, RetryStrategy, CircuitBreaker

# Создаем стратегию повторных попыток
strategy = RetryStrategy(
    max_retries=3,
    retry_delay=1.0,
    backoff_factor=2.0,
    jitter=True,
    retry_on_exceptions=[ValueError, TypeError]
)

# Создаем Circuit Breaker
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30.0,
    half_open_max_calls=3,
    reset_timeout=60.0
)

# Применяем декоратор к функции
@async_retry(retry_strategy=strategy, circuit_breaker=circuit_breaker, endpoint="my_function")
async def my_function():
    # Функция, которая может вызвать исключение
    if asyncio.random() < 0.5:
        raise ValueError("Random error")
    return "Success"

# Выполняем функцию
result = asyncio.run(my_function())
```

## Заключение

Механизм повторных попыток и паттерн Circuit Breaker повышают надежность HTTP-запросов и предотвращают каскадные отказы при недоступности внешних сервисов. Они автоматически используются HTTP-клиентом, но также могут быть использованы напрямую для других асинхронных и синхронных функций.
