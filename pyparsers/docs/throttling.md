# Ограничение ресурсов и регулирование нагрузки

В этом документе описывается механизм ограничения ресурсов и регулирования нагрузки, реализованный в модуле `throttling.py`.

## Обзор

Механизм ограничения ресурсов и регулирования нагрузки позволяет:
- Ограничивать количество одновременных запросов (concurrency limiting)
- Ограничивать скорость запросов (rate limiting)
- Применять ограничения глобально или отдельно для каждого эндпоинта

Это помогает предотвратить перегрузку внешних сервисов и собственного приложения, а также обеспечивает более равномерное распределение нагрузки.

## Основные компоненты

### RateLimiter

Класс `RateLimiter` реализует алгоритм "token bucket" для ограничения скорости запросов:

```python
from api.throttling import RateLimiter

rate_limiter = RateLimiter(
    rate=10.0,                # Максимальное количество запросов в секунду
    burst=20,                 # Максимальное количество запросов, которые можно выполнить сразу
    per_endpoint=True         # Применять ограничения отдельно для каждого эндпоинта
)

# Запрашиваем разрешение на выполнение запроса
wait_time = await rate_limiter.acquire("my_endpoint")
```

### ConcurrencyLimiter

Класс `ConcurrencyLimiter` ограничивает количество одновременных запросов:

```python
from api.throttling import ConcurrencyLimiter

concurrency_limiter = ConcurrencyLimiter(
    max_concurrency=10,       # Максимальное количество одновременных запросов
    per_endpoint=True         # Применять ограничения отдельно для каждого эндпоинта
)

# Запрашиваем разрешение на выполнение запроса
await concurrency_limiter.acquire("my_endpoint")

try:
    # Выполняем запрос
    result = await do_request()
finally:
    # Освобождаем ресурс
    concurrency_limiter.release("my_endpoint")
```

### ResourceManager

Класс `ResourceManager` объединяет `RateLimiter` и `ConcurrencyLimiter` для комплексного управления ресурсами:

```python
from api.throttling import ResourceManager

resource_manager = ResourceManager(
    rate_limit=10.0,          # Максимальное количество запросов в секунду
    burst=20,                 # Максимальное количество запросов, которые можно выполнить сразу
    max_concurrency=10,       # Максимальное количество одновременных запросов
    per_endpoint=True         # Применять ограничения отдельно для каждого эндпоинта
)

# Запрашиваем разрешение на выполнение запроса
wait_time = await resource_manager.acquire("my_endpoint")

try:
    # Выполняем запрос
    result = await do_request()
finally:
    # Освобождаем ресурс
    resource_manager.release("my_endpoint")
```

### Декоратор throttle

Декоратор `throttle` упрощает использование `ResourceManager` для асинхронных функций:

```python
from api.throttling import throttle, ResourceManager

resource_manager = ResourceManager(
    rate_limit=10.0,
    burst=20,
    max_concurrency=10,
    per_endpoint=True
)

@throttle(resource_manager=resource_manager, endpoint="my_endpoint")
async def my_function():
    # Функция будет выполняться с ограничением ресурсов
    return await do_request()
```

## Использование с HTTP-клиентом

HTTP-клиент (`HTTPClient`) автоматически использует механизм ограничения ресурсов для всех запросов:

```python
from api.http_client import HTTPClient

# Создаем HTTP-клиент с настраиваемыми ограничениями ресурсов
client = HTTPClient(
    base_url="https://example.com",
    rate_limit=10.0,          # Максимальное количество запросов в секунду
    burst=20,                 # Максимальное количество запросов, которые можно выполнить сразу
    max_concurrency=10,       # Максимальное количество одновременных запросов
    per_endpoint=True         # Применять ограничения отдельно для каждого эндпоинта
)

# Асинхронные запросы
status, data, text = await client.get("/api/v1/resource")
status, data, text = await client.post("/api/v1/resource", json_data={"key": "value"})
```

## Глобальные экземпляры

Модуль `throttling.py` предоставляет глобальный экземпляр `ResourceManager` для использования в приложении:

```python
from api.throttling import default_resource_manager, throttle

# Использование глобального менеджера ресурсов
@throttle(resource_manager=default_resource_manager, endpoint="my_endpoint")
async def my_function():
    # Функция будет выполняться с ограничением ресурсов
    return await do_request()
```

## Настройка логирования

Механизм ограничения ресурсов использует стандартный модуль `logging` для логирования информации:

```python
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api.throttling")
logger.setLevel(logging.DEBUG)
```

## Примеры

### Пример 1: Ограничение скорости запросов

```python
import asyncio
from api.throttling import RateLimiter

async def main():
    # Создаем ограничитель скорости запросов
    rate_limiter = RateLimiter(rate=2.0, burst=1)
    
    # Выполняем 5 запросов
    for i in range(5):
        start_time = asyncio.get_event_loop().time()
        
        # Запрашиваем разрешение на выполнение запроса
        wait_time = await rate_limiter.acquire()
        
        elapsed = asyncio.get_event_loop().time() - start_time
        print(f"Request {i+1}: waited {elapsed:.2f}s")
        
        # Имитируем выполнение запроса
        await asyncio.sleep(0.1)

# Запускаем пример
asyncio.run(main())
```

Вывод:
```
Request 1: waited 0.00s
Request 2: waited 0.50s
Request 3: waited 0.50s
Request 4: waited 0.50s
Request 5: waited 0.50s
```

### Пример 2: Ограничение количества одновременных запросов

```python
import asyncio
from api.throttling import ConcurrencyLimiter

async def request(i, limiter):
    # Запрашиваем разрешение на выполнение запроса
    await limiter.acquire()
    
    try:
        print(f"Request {i} started")
        # Имитируем выполнение запроса
        await asyncio.sleep(1.0)
        print(f"Request {i} completed")
    finally:
        # Освобождаем ресурс
        limiter.release()

async def main():
    # Создаем ограничитель количества одновременных запросов
    limiter = ConcurrencyLimiter(max_concurrency=2)
    
    # Запускаем 5 запросов одновременно
    tasks = [asyncio.create_task(request(i, limiter)) for i in range(5)]
    
    # Ждем завершения всех запросов
    await asyncio.gather(*tasks)

# Запускаем пример
asyncio.run(main())
```

Вывод:
```
Request 0 started
Request 1 started
Request 0 completed
Request 2 started
Request 1 completed
Request 3 started
Request 2 completed
Request 4 started
Request 3 completed
Request 4 completed
```

### Пример 3: Использование декоратора throttle

```python
import asyncio
from api.throttling import throttle, ResourceManager

# Создаем менеджер ресурсов
resource_manager = ResourceManager(
    rate_limit=2.0,
    burst=1,
    max_concurrency=2
)

@throttle(resource_manager=resource_manager, endpoint="my_endpoint")
async def my_request(i):
    print(f"Request {i} started")
    # Имитируем выполнение запроса
    await asyncio.sleep(1.0)
    print(f"Request {i} completed")
    return i

async def main():
    # Запускаем 5 запросов одновременно
    tasks = [asyncio.create_task(my_request(i)) for i in range(5)]
    
    # Ждем завершения всех запросов
    results = await asyncio.gather(*tasks)
    
    print(f"Results: {results}")

# Запускаем пример
asyncio.run(main())
```

Вывод:
```
Request 0 started
Request 1 started
Request 0 completed
Request 2 started
Request 1 completed
Request 3 started
Request 2 completed
Request 4 started
Request 3 completed
Request 4 completed
Results: [0, 1, 2, 3, 4]
```

## Заключение

Механизм ограничения ресурсов и регулирования нагрузки помогает предотвратить перегрузку внешних сервисов и собственного приложения, а также обеспечивает более равномерное распределение нагрузки. Он автоматически используется HTTP-клиентом, но также может быть использован напрямую для других асинхронных функций.
