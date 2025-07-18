"""
Модуль для структурированного логирования и категоризации ошибок.
"""

import logging
import json
import sys
import traceback
import time
import os
import uuid
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Callable
from functools import wraps
import asyncio

# Настройка логирования
logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Категории ошибок для более точной классификации."""

    # Сетевые ошибки
    NETWORK_ERROR = "network_error"                # Общие ошибки сети
    CONNECTION_ERROR = "connection_error"          # Ошибки соединения
    TIMEOUT_ERROR = "timeout_error"                # Ошибки таймаута
    DNS_ERROR = "dns_error"                        # Ошибки DNS

    # Ошибки HTTP
    HTTP_CLIENT_ERROR = "http_client_error"        # Ошибки клиента HTTP (4xx)
    HTTP_SERVER_ERROR = "http_server_error"        # Ошибки сервера HTTP (5xx)
    HTTP_REDIRECT_ERROR = "http_redirect_error"    # Ошибки перенаправления HTTP (3xx)

    # Ошибки парсинга
    PARSING_ERROR = "parsing_error"                # Общие ошибки парсинга
    JSON_PARSING_ERROR = "json_parsing_error"      # Ошибки парсинга JSON
    HTML_PARSING_ERROR = "html_parsing_error"      # Ошибки парсинга HTML

    # Ошибки базы данных
    DB_CONNECTION_ERROR = "db_connection_error"    # Ошибки соединения с БД
    DB_QUERY_ERROR = "db_query_error"              # Ошибки запросов к БД
    DB_TRANSACTION_ERROR = "db_transaction_error"  # Ошибки транзакций БД

    # Ошибки валидации
    VALIDATION_ERROR = "validation_error"          # Ошибки валидации данных

    # Ошибки бизнес-логики
    BUSINESS_LOGIC_ERROR = "business_logic_error"  # Ошибки бизнес-логики

    # Системные ошибки
    SYSTEM_ERROR = "system_error"                  # Общие системные ошибки
    RESOURCE_ERROR = "resource_error"              # Ошибки ресурсов (память, диск и т.д.)

    # Неизвестные ошибки
    UNKNOWN_ERROR = "unknown_error"                # Неизвестные ошибки


class StructuredLogger:
    """
    Класс для структурированного логирования.

    Позволяет логировать сообщения в структурированном формате (JSON),
    что упрощает их анализ и обработку.
    """

    def __init__(self,
                 name: str = None,
                 level: int = logging.INFO,
                 add_console_handler: bool = True,
                 add_file_handler: bool = False,
                 file_path: str = None,
                 json_format: bool = True):
        """
        Инициализирует структурированный логгер.

        Args:
            name: Имя логгера
            level: Уровень логирования
            add_console_handler: Добавлять ли обработчик для вывода в консоль
            add_file_handler: Добавлять ли обработчик для записи в файл
            file_path: Путь к файлу для записи логов
            json_format: Использовать ли формат JSON для логов
        """
        self.name = name or __name__
        self.level = level
        self.json_format = json_format

        # Создаем логгер
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(self.level)

        # Удаляем существующие обработчики
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Добавляем обработчик для вывода в консоль
        if add_console_handler:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)

            if self.json_format:
                formatter = logging.Formatter('%(message)s')
            else:
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # Добавляем обработчик для записи в файл
        if add_file_handler and file_path:
            file_handler = logging.FileHandler(file_path)
            file_handler.setLevel(self.level)

            if self.json_format:
                formatter = logging.Formatter('%(message)s')
            else:
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _format_message(self,
                       level: str,
                       message: str,
                       error: Optional[Exception] = None,
                       error_category: Optional[ErrorCategory] = None,
                       context: Optional[Dict[str, Any]] = None,
                       **kwargs) -> str:
        """
        Форматирует сообщение для логирования.

        Args:
            level: Уровень логирования
            message: Сообщение для логирования
            error: Исключение, если есть
            error_category: Категория ошибки
            context: Контекст для логирования
            **kwargs: Дополнительные параметры для логирования

        Returns:
            str: Отформатированное сообщение
        """
        if not self.json_format:
            # Если не используем JSON, просто возвращаем сообщение
            if error:
                return f"{message}: {str(error)}"
            else:
                return message

        # Создаем структуру для JSON
        # Форматируем timestamp с микросекундами (time.strftime не поддерживает %f)
        current_time = time.time()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(current_time))
        microseconds = int((current_time - int(current_time)) * 1000000)
        timestamp = f"{timestamp}.{microseconds:06d}Z"

        log_data = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
            "logger": self.name,
            "process_id": os.getpid(),
            "thread_id": threading.get_ident() if not asyncio.get_event_loop().is_running() else asyncio.current_task().get_name() if asyncio.current_task() else "unknown",
            "log_id": str(uuid.uuid4())
        }

        # Добавляем информацию об ошибке, если есть
        if error:
            log_data["error"] = {
                "type": error.__class__.__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
                "category": error_category.value if error_category else ErrorCategory.UNKNOWN_ERROR.value
            }

        # Добавляем контекст, если есть
        if context:
            log_data["context"] = context

        # Добавляем дополнительные параметры
        for key, value in kwargs.items():
            log_data[key] = value

        # Преобразуем в JSON
        return json.dumps(log_data)

    def debug(self,
             message: str,
             error: Optional[Exception] = None,
             error_category: Optional[ErrorCategory] = None,
             context: Optional[Dict[str, Any]] = None,
             **kwargs) -> None:
        """
        Логирует сообщение с уровнем DEBUG.

        Args:
            message: Сообщение для логирования
            error: Исключение, если есть
            error_category: Категория ошибки
            context: Контекст для логирования
            **kwargs: Дополнительные параметры для логирования
        """
        formatted_message = self._format_message(
            level="DEBUG",
            message=message,
            error=error,
            error_category=error_category,
            context=context,
            **kwargs
        )

        self.logger.debug(formatted_message)

    def info(self,
            message: str,
            context: Optional[Dict[str, Any]] = None,
            **kwargs) -> None:
        """
        Логирует сообщение с уровнем INFO.

        Args:
            message: Сообщение для логирования
            context: Контекст для логирования
            **kwargs: Дополнительные параметры для логирования
        """
        formatted_message = self._format_message(
            level="INFO",
            message=message,
            context=context,
            **kwargs
        )

        self.logger.info(formatted_message)

    def warning(self,
               message: str,
               error: Optional[Exception] = None,
               error_category: Optional[ErrorCategory] = None,
               context: Optional[Dict[str, Any]] = None,
               **kwargs) -> None:
        """
        Логирует сообщение с уровнем WARNING.

        Args:
            message: Сообщение для логирования
            error: Исключение, если есть
            error_category: Категория ошибки
            context: Контекст для логирования
            **kwargs: Дополнительные параметры для логирования
        """
        formatted_message = self._format_message(
            level="WARNING",
            message=message,
            error=error,
            error_category=error_category,
            context=context,
            **kwargs
        )

        self.logger.warning(formatted_message)

    def error(self,
             message: str,
             error: Optional[Exception] = None,
             error_category: Optional[ErrorCategory] = None,
             context: Optional[Dict[str, Any]] = None,
             **kwargs) -> None:
        """
        Логирует сообщение с уровнем ERROR.

        Args:
            message: Сообщение для логирования
            error: Исключение, если есть
            error_category: Категория ошибки
            context: Контекст для логирования
            **kwargs: Дополнительные параметры для логирования
        """
        formatted_message = self._format_message(
            level="ERROR",
            message=message,
            error=error,
            error_category=error_category,
            context=context,
            **kwargs
        )

        self.logger.error(formatted_message)

    def critical(self,
                message: str,
                error: Optional[Exception] = None,
                error_category: Optional[ErrorCategory] = None,
                context: Optional[Dict[str, Any]] = None,
                **kwargs) -> None:
        """
        Логирует сообщение с уровнем CRITICAL.

        Args:
            message: Сообщение для логирования
            error: Исключение, если есть
            error_category: Категория ошибки
            context: Контекст для логирования
            **kwargs: Дополнительные параметры для логирования
        """
        formatted_message = self._format_message(
            level="CRITICAL",
            message=message,
            error=error,
            error_category=error_category,
            context=context,
            **kwargs
        )

        self.logger.critical(formatted_message)


class ErrorHandler:
    """
    Класс для обработки ошибок.

    Позволяет категоризировать ошибки и выполнять соответствующие действия
    в зависимости от категории ошибки.
    """

    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Инициализирует обработчик ошибок.

        Args:
            logger: Структурированный логгер
        """
        self.logger = logger or StructuredLogger(name="error_handler")

        # Словарь для сопоставления типов исключений с категориями ошибок
        self.error_categories = {
            # Сетевые ошибки
            "ConnectionError": ErrorCategory.CONNECTION_ERROR,
            "TimeoutError": ErrorCategory.TIMEOUT_ERROR,
            "socket.gaierror": ErrorCategory.DNS_ERROR,

            # Ошибки HTTP
            "HTTPClientError": ErrorCategory.HTTP_CLIENT_ERROR,
            "HTTPServerError": ErrorCategory.HTTP_SERVER_ERROR,
            "TooManyRedirects": ErrorCategory.HTTP_REDIRECT_ERROR,

            # Ошибки парсинга
            "JSONDecodeError": ErrorCategory.JSON_PARSING_ERROR,
            "ParserError": ErrorCategory.PARSING_ERROR,

            # Ошибки базы данных
            "OperationalError": ErrorCategory.DB_CONNECTION_ERROR,
            "ProgrammingError": ErrorCategory.DB_QUERY_ERROR,
            "IntegrityError": ErrorCategory.DB_TRANSACTION_ERROR,

            # Ошибки валидации
            "ValidationError": ErrorCategory.VALIDATION_ERROR,

            # Системные ошибки
            "MemoryError": ErrorCategory.RESOURCE_ERROR,
            "DiskError": ErrorCategory.RESOURCE_ERROR
        }

        # Словарь для сопоставления категорий ошибок с обработчиками
        self.error_handlers = {}

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Категоризирует ошибку.

        Args:
            error: Исключение

        Returns:
            ErrorCategory: Категория ошибки
        """
        error_type = error.__class__.__name__

        # Проверяем, есть ли категория для данного типа ошибки
        if error_type in self.error_categories:
            return self.error_categories[error_type]

        # Проверяем родительские классы
        for base in error.__class__.__mro__:
            if base.__name__ in self.error_categories:
                return self.error_categories[base.__name__]

        # Если категория не найдена, возвращаем UNKNOWN_ERROR
        return ErrorCategory.UNKNOWN_ERROR

    def register_error_handler(self,
                              category: ErrorCategory,
                              handler: Callable[[Exception, Dict[str, Any]], None]) -> None:
        """
        Регистрирует обработчик для категории ошибок.

        Args:
            category: Категория ошибки
            handler: Функция-обработчик
        """
        self.error_handlers[category] = handler

    def handle_error(self,
                    error: Exception,
                    context: Optional[Dict[str, Any]] = None,
                    log_level: str = "ERROR") -> None:
        """
        Обрабатывает ошибку.

        Args:
            error: Исключение
            context: Контекст для логирования
            log_level: Уровень логирования
        """
        # Категоризируем ошибку
        category = self.categorize_error(error)

        # Логируем ошибку
        if log_level == "DEBUG":
            self.logger.debug(
                message=f"Error: {str(error)}",
                error=error,
                error_category=category,
                context=context
            )
        elif log_level == "INFO":
            self.logger.info(
                message=f"Error: {str(error)}",
                error=error,
                error_category=category,
                context=context
            )
        elif log_level == "WARNING":
            self.logger.warning(
                message=f"Error: {str(error)}",
                error=error,
                error_category=category,
                context=context
            )
        elif log_level == "CRITICAL":
            self.logger.critical(
                message=f"Error: {str(error)}",
                error=error,
                error_category=category,
                context=context
            )
        else:
            self.logger.error(
                message=f"Error: {str(error)}",
                error=error,
                error_category=category,
                context=context
            )

        # Вызываем обработчик для данной категории ошибок, если он зарегистрирован
        if category in self.error_handlers:
            self.error_handlers[category](error, context or {})


# Создаем глобальные экземпляры для использования в приложении
import threading
default_logger = StructuredLogger(name="pyparsers")
default_error_handler = ErrorHandler(logger=default_logger)


# Декораторы для логирования и обработки ошибок

def log_function(logger: Optional[StructuredLogger] = None,
                error_handler: Optional[ErrorHandler] = None):
    """
    Декоратор для логирования вызовов функций.

    Args:
        logger: Структурированный логгер
        error_handler: Обработчик ошибок

    Returns:
        Callable: Декорированная функция
    """
    logger = logger or default_logger
    error_handler = error_handler or default_error_handler

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Логируем начало выполнения функции
            logger.debug(
                message=f"Calling {func.__name__}",
                context={"args": str(args), "kwargs": str(kwargs)}
            )

            start_time = time.time()

            try:
                # Выполняем функцию
                result = func(*args, **kwargs)

                # Логируем успешное выполнение функции
                elapsed = time.time() - start_time
                logger.debug(
                    message=f"Called {func.__name__}",
                    context={"elapsed": elapsed}
                )

                return result
            except Exception as e:
                # Обрабатываем ошибку
                elapsed = time.time() - start_time
                error_handler.handle_error(
                    error=e,
                    context={
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs),
                        "elapsed": elapsed
                    }
                )

                # Пробрасываем исключение дальше
                raise

        return wrapper

    return decorator


def log_async_function(logger: Optional[StructuredLogger] = None,
                      error_handler: Optional[ErrorHandler] = None):
    """
    Декоратор для логирования вызовов асинхронных функций.

    Args:
        logger: Структурированный логгер
        error_handler: Обработчик ошибок

    Returns:
        Callable: Декорированная функция
    """
    logger = logger or default_logger
    error_handler = error_handler or default_error_handler

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Логируем начало выполнения функции
            logger.debug(
                message=f"Calling {func.__name__}",
                context={"args": str(args), "kwargs": str(kwargs)}
            )

            start_time = time.time()

            try:
                # Выполняем функцию
                result = await func(*args, **kwargs)

                # Логируем успешное выполнение функции
                elapsed = time.time() - start_time
                logger.debug(
                    message=f"Called {func.__name__}",
                    context={"elapsed": elapsed}
                )

                return result
            except Exception as e:
                # Обрабатываем ошибку
                elapsed = time.time() - start_time
                error_handler.handle_error(
                    error=e,
                    context={
                        "function": func.__name__,
                        "args": str(args),
                        "kwargs": str(kwargs),
                        "elapsed": elapsed
                    }
                )

                # Пробрасываем исключение дальше
                raise

        return wrapper

    return decorator
