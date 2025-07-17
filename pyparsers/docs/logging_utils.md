# Структурированное логирование и обработка ошибок

В этом документе описывается механизм структурированного логирования и обработки ошибок, реализованный в модуле `logging_utils.py`.

## Обзор

Механизм структурированного логирования и обработки ошибок позволяет:
- Логировать сообщения в структурированном формате (JSON)
- Категоризировать ошибки для более точной классификации
- Регистрировать обработчики для различных категорий ошибок
- Логировать вызовы функций и обрабатывать возникающие ошибки

Это помогает упростить анализ логов и обработку ошибок, а также обеспечивает более единообразный подход к логированию и обработке ошибок в приложении.

## Основные компоненты

### ErrorCategory

Перечисление `ErrorCategory` определяет категории ошибок для более точной классификации:

```python
from api.logging_utils import ErrorCategory

# Примеры категорий ошибок
ErrorCategory.NETWORK_ERROR        # Общие ошибки сети
ErrorCategory.CONNECTION_ERROR     # Ошибки соединения
ErrorCategory.TIMEOUT_ERROR        # Ошибки таймаута
ErrorCategory.HTTP_CLIENT_ERROR    # Ошибки клиента HTTP (4xx)
ErrorCategory.HTTP_SERVER_ERROR    # Ошибки сервера HTTP (5xx)
ErrorCategory.JSON_PARSING_ERROR   # Ошибки парсинга JSON
ErrorCategory.DB_CONNECTION_ERROR  # Ошибки соединения с БД
ErrorCategory.VALIDATION_ERROR     # Ошибки валидации данных
ErrorCategory.UNKNOWN_ERROR        # Неизвестные ошибки
```

### StructuredLogger

Класс `StructuredLogger` позволяет логировать сообщения в структурированном формате (JSON):

```python
from api.logging_utils import StructuredLogger, ErrorCategory

# Создаем структурированный логгер
logger = StructuredLogger(
    name="my_logger",
    level=logging.INFO,
    add_console_handler=True,
    add_file_handler=True,
    file_path="logs/my_logger.log",
    json_format=True
)

# Логируем сообщения
logger.debug("Debug message", context={"key": "value"})
logger.info("Info message", context={"key": "value"})
logger.warning("Warning message", error=ValueError("Test error"), error_category=ErrorCategory.VALIDATION_ERROR)
logger.error("Error message", error=ValueError("Test error"), error_category=ErrorCategory.VALIDATION_ERROR)
logger.critical("Critical message", error=ValueError("Test error"), error_category=ErrorCategory.VALIDATION_ERROR)
```

### ErrorHandler

Класс `ErrorHandler` позволяет категоризировать ошибки и выполнять соответствующие действия в зависимости от категории ошибки:

```python
from api.logging_utils import ErrorHandler, ErrorCategory, StructuredLogger

# Создаем структурированный логгер
logger = StructuredLogger(name="my_logger")

# Создаем обработчик ошибок
error_handler = ErrorHandler(logger=logger)

# Регистрируем обработчик для категории ошибок
def handle_validation_error(error, context):
    print(f"Validation error: {str(error)}")
    print(f"Context: {context}")

error_handler.register_error_handler(ErrorCategory.VALIDATION_ERROR, handle_validation_error)

# Обрабатываем ошибку
try:
    # Код, который может вызвать исключение
    raise ValueError("Invalid value")
except Exception as e:
    error_handler.handle_error(
        error=e,
        context={"key": "value"},
        log_level="ERROR"
    )
```

### Декораторы

Модуль `logging_utils.py` предоставляет два декоратора для логирования вызовов функций и обработки ошибок:

- `log_function` - для синхронных функций
- `log_async_function` - для асинхронных функций

```python
from api.logging_utils import log_function, log_async_function, StructuredLogger, ErrorHandler

# Создаем структурированный логгер и обработчик ошибок
logger = StructuredLogger(name="my_logger")
error_handler = ErrorHandler(logger=logger)

# Для синхронных функций
@log_function(logger=logger, error_handler=error_handler)
def my_function(arg1, arg2=None):
    # Функция будет логироваться и ошибки будут обрабатываться
    return arg1 + (arg2 or 0)

# Для асинхронных функций
@log_async_function(logger=logger, error_handler=error_handler)
async def my_async_function(arg1, arg2=None):
    # Функция будет логироваться и ошибки будут обрабатываться
    await asyncio.sleep(0.1)
    return arg1 + (arg2 or 0)
```

## Глобальные экземпляры

Модуль `logging_utils.py` предоставляет глобальные экземпляры для использования в приложении:

```python
from api.logging_utils import default_logger, default_error_handler, log_function, log_async_function

# Использование глобального логгера
default_logger.info("Info message", context={"key": "value"})

# Использование глобального обработчика ошибок
try:
    # Код, который может вызвать исключение
    raise ValueError("Invalid value")
except Exception as e:
    default_error_handler.handle_error(
        error=e,
        context={"key": "value"},
        log_level="ERROR"
    )

# Использование глобальных экземпляров с декораторами
@log_function()  # Используются глобальные экземпляры по умолчанию
def my_function(arg1, arg2=None):
    return arg1 + (arg2 or 0)

@log_async_function()  # Используются глобальные экземпляры по умолчанию
async def my_async_function(arg1, arg2=None):
    await asyncio.sleep(0.1)
    return arg1 + (arg2 or 0)
```

## Настройка логирования

Механизм структурированного логирования использует стандартный модуль `logging` для логирования информации:

```python
import logging
from api.logging_utils import StructuredLogger

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем структурированный логгер
logger = StructuredLogger(
    name="my_logger",
    level=logging.DEBUG,
    add_console_handler=True,
    add_file_handler=True,
    file_path="logs/my_logger.log",
    json_format=True
)
```

## Примеры

### Пример 1: Структурированное логирование

```python
import logging
from api.logging_utils import StructuredLogger, ErrorCategory

# Создаем структурированный логгер
logger = StructuredLogger(
    name="my_logger",
    level=logging.INFO,
    add_console_handler=True,
    json_format=True
)

# Логируем информационное сообщение
logger.info(
    message="User logged in",
    context={
        "user_id": 123,
        "username": "john_doe",
        "ip_address": "192.168.1.1"
    }
)

# Логируем ошибку
try:
    # Код, который может вызвать исключение
    result = 1 / 0
except Exception as e:
    logger.error(
        message="Error dividing by zero",
        error=e,
        error_category=ErrorCategory.VALIDATION_ERROR,
        context={
            "operation": "division",
            "numerator": 1,
            "denominator": 0
        }
    )
```

### Пример 2: Обработка ошибок

```python
from api.logging_utils import ErrorHandler, ErrorCategory, StructuredLogger

# Создаем структурированный логгер
logger = StructuredLogger(name="my_logger")

# Создаем обработчик ошибок
error_handler = ErrorHandler(logger=logger)

# Регистрируем обработчики для различных категорий ошибок
def handle_network_error(error, context):
    print(f"Network error: {str(error)}")
    print(f"Context: {context}")
    # Выполняем действия для обработки сетевой ошибки
    # Например, переподключаемся к сети

def handle_validation_error(error, context):
    print(f"Validation error: {str(error)}")
    print(f"Context: {context}")
    # Выполняем действия для обработки ошибки валидации
    # Например, запрашиваем корректные данные

error_handler.register_error_handler(ErrorCategory.NETWORK_ERROR, handle_network_error)
error_handler.register_error_handler(ErrorCategory.CONNECTION_ERROR, handle_network_error)
error_handler.register_error_handler(ErrorCategory.TIMEOUT_ERROR, handle_network_error)
error_handler.register_error_handler(ErrorCategory.VALIDATION_ERROR, handle_validation_error)

# Обрабатываем ошибки
try:
    # Код, который может вызвать исключение
    raise ConnectionError("Connection refused")
except Exception as e:
    error_handler.handle_error(
        error=e,
        context={"host": "example.com", "port": 80},
        log_level="ERROR"
    )

try:
    # Код, который может вызвать исключение
    raise ValueError("Invalid value")
except Exception as e:
    error_handler.handle_error(
        error=e,
        context={"field": "username", "value": ""},
        log_level="WARNING"
    )
```

### Пример 3: Декораторы для логирования и обработки ошибок

```python
import asyncio
from api.logging_utils import log_function, log_async_function, StructuredLogger, ErrorHandler

# Создаем структурированный логгер и обработчик ошибок
logger = StructuredLogger(name="my_logger")
error_handler = ErrorHandler(logger=logger)

# Для синхронных функций
@log_function(logger=logger, error_handler=error_handler)
def divide(a, b):
    return a / b

# Для асинхронных функций
@log_async_function(logger=logger, error_handler=error_handler)
async def fetch_data(url):
    await asyncio.sleep(0.1)
    if url == "https://example.com":
        return {"status": "ok", "data": [1, 2, 3]}
    else:
        raise ValueError(f"Invalid URL: {url}")

# Вызываем функции
try:
    result = divide(10, 2)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {str(e)}")

try:
    result = divide(10, 0)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {str(e)}")

async def main():
    try:
        result = await fetch_data("https://example.com")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    try:
        result = await fetch_data("invalid_url")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {str(e)}")

# Запускаем асинхронную функцию
asyncio.run(main())
```

## Заключение

Механизм структурированного логирования и обработки ошибок помогает упростить анализ логов и обработку ошибок, а также обеспечивает более единообразный подход к логированию и обработке ошибок в приложении. Он может быть использован как напрямую, так и через декораторы для логирования вызовов функций и обработки ошибок.
