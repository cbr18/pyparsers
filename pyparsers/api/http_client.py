"""
Асинхронный HTTP-клиент для выполнения запросов к API.
"""

import aiohttp
import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, Union, List, Tuple
import requests
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from .throttling import ResourceManager, throttle
from .logging_utils import StructuredLogger, ErrorHandler, ErrorCategory, log_async_function, log_function

# Настройка структурированного логирования
structured_logger = StructuredLogger(name="http_client", json_format=True)
error_handler = ErrorHandler(logger=structured_logger)

# Регистрируем обработчики для различных категорий ошибок
def handle_network_error(error, context):
    """Обработчик для сетевых ошибок."""
    structured_logger.warning(
        message=f"Network error: {str(error)}",
        error=error,
        error_category=ErrorCategory.NETWORK_ERROR,
        context=context
    )

def handle_timeout_error(error, context):
    """Обработчик для ошибок таймаута."""
    structured_logger.warning(
        message=f"Timeout error: {str(error)}",
        error=error,
        error_category=ErrorCategory.TIMEOUT_ERROR,
        context=context
    )

def handle_http_error(error, context):
    """Обработчик для HTTP ошибок."""
    structured_logger.warning(
        message=f"HTTP error: {str(error)}",
        error=error,
        error_category=ErrorCategory.HTTP_SERVER_ERROR if context.get("status_code", 0) >= 500 else ErrorCategory.HTTP_CLIENT_ERROR,
        context=context
    )

# Регистрируем обработчики
error_handler.register_error_handler(ErrorCategory.NETWORK_ERROR, handle_network_error)
error_handler.register_error_handler(ErrorCategory.CONNECTION_ERROR, handle_network_error)
error_handler.register_error_handler(ErrorCategory.TIMEOUT_ERROR, handle_timeout_error)
error_handler.register_error_handler(ErrorCategory.HTTP_CLIENT_ERROR, handle_http_error)
error_handler.register_error_handler(ErrorCategory.HTTP_SERVER_ERROR, handle_http_error)

# Для обратной совместимости
logger = logging.getLogger(__name__)

class HTTPClient:
    """
    Класс для выполнения HTTP-запросов с поддержкой как синхронных, так и асинхронных операций.
    Обеспечивает обратную совместимость с существующим кодом, использующим requests.
    """

    def __init__(self,
                 base_url: str = "",
                 headers: Optional[Dict[str, str]] = None,
                 timeout: float = 3600.0,  # Увеличиваем таймаут до часа по умолчанию
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 backoff_factor: float = 2.0,
                 jitter: bool = True,
                 retry_on_status_codes: Optional[List[int]] = None,
                 retry_on_exceptions: Optional[List[Exception]] = None,
                 pool_size: int = 100,
                 rate_limit: float = 10.0,
                 burst: int = 20,
                 max_concurrency: int = 10,
                 per_endpoint: bool = True):
        """
        Инициализирует HTTP-клиент.

        Args:
            base_url: Базовый URL для запросов
            headers: Заголовки по умолчанию для всех запросов
            timeout: Таймаут для запросов в секундах
            max_retries: Максимальное количество повторных попыток при ошибках
            retry_delay: Начальная задержка между повторными попытками в секундах
            backoff_factor: Множитель для экспоненциальной задержки
            jitter: Добавлять случайное отклонение к задержке
            retry_on_status_codes: Список кодов состояния HTTP, при которых нужно повторять запрос
            retry_on_exceptions: Список исключений, при которых нужно повторять запрос
            pool_size: Размер пула соединений
            rate_limit: Максимальное количество запросов в секунду
            burst: Максимальное количество запросов, которые можно выполнить сразу
            max_concurrency: Максимальное количество одновременных запросов
            per_endpoint: Применять ограничения отдельно для каждого эндпоинта
        """
        self.base_url = base_url
        self.headers = headers or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on_status_codes = retry_on_status_codes or [500, 502, 503, 504]
        self.retry_on_exceptions = retry_on_exceptions or [
            aiohttp.ClientError,
            asyncio.TimeoutError,
            requests.RequestException
        ]
        self.pool_size = pool_size
        self._session = None
        self._connector = None

        # Создаем стратегию повторных попыток
        from .retry import RetryStrategy
        self.retry_strategy = RetryStrategy(
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            backoff_factor=self.backoff_factor,
            jitter=self.jitter,
            retry_on_status_codes=self.retry_on_status_codes,
            retry_on_exceptions=self.retry_on_exceptions
        )

        # Создаем менеджер ресурсов для ограничения запросов
        self.resource_manager = ResourceManager(
            rate_limit=rate_limit,
            burst=burst,
            max_concurrency=max_concurrency,
            per_endpoint=per_endpoint
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Возвращает сессию aiohttp, создавая ее при необходимости.

        Returns:
            aiohttp.ClientSession: Сессия aiohttp
        """
        if self._session is None or self._session.closed:
            if self._connector is None or self._connector.closed:
                self._connector = aiohttp.TCPConnector(limit=self.pool_size)

            self._session = aiohttp.ClientSession(
                connector=self._connector,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

        return self._session

    async def close(self):
        """
        Закрывает сессию aiohttp.
        """
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

        if self._connector and not self._connector.closed:
            await self._connector.close()
            self._connector = None

    def _build_url(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Строит полный URL для запроса.

        Args:
            url: URL или путь
            params: Параметры запроса

        Returns:
            str: Полный URL для запроса
        """
        # Если URL не содержит схему, добавляем базовый URL
        if not url.startswith(('http://', 'https://')):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"

        # Если есть параметры, добавляем их к URL
        if params:
            # Разбираем URL
            parsed_url = urlparse(url)
            # Получаем существующие параметры
            query_params = dict(parse_qsl(parsed_url.query))
            # Добавляем новые параметры
            query_params.update(params)
            # Собираем URL обратно
            url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                urlencode(query_params),
                parsed_url.fragment
            ))

        return url

    async def _request(self,
                      method: str,
                      url: str,
                      params: Optional[Dict[str, Any]] = None,
                      data: Optional[Any] = None,
                      json_data: Optional[Dict[str, Any]] = None,
                      headers: Optional[Dict[str, str]] = None,
                      timeout: Optional[float] = None,
                      **kwargs) -> Tuple[int, Dict[str, Any], str]:
        """
        Выполняет HTTP-запрос асинхронно.

        Args:
            method: HTTP-метод (GET, POST, PUT, DELETE)
            url: URL для запроса
            params: Параметры запроса
            data: Данные для отправки в теле запроса
            json_data: JSON-данные для отправки в теле запроса
            headers: Заголовки запроса
            timeout: Таймаут для запроса в секундах
            **kwargs: Дополнительные параметры для aiohttp.ClientSession.request

        Returns:
            Tuple[int, Dict[str, Any], str]: Статус-код, JSON-ответ (или пустой словарь), текст ответа
        """
        from .retry import async_retry, default_circuit_breaker

        full_url = self._build_url(url, params)
        request_headers = {**self.headers, **(headers or {})}
        timeout_value = aiohttp.ClientTimeout(total=timeout or self.timeout)

        # Создаем эндпоинт для Circuit Breaker и throttling на основе URL
        endpoint = f"{method}:{urlparse(full_url).netloc}"

        # Определяем внутреннюю функцию для выполнения запроса
        @throttle(resource_manager=self.resource_manager, endpoint=endpoint)
        @async_retry(retry_strategy=self.retry_strategy, circuit_breaker=default_circuit_breaker, endpoint=endpoint)
        async def _execute_request() -> Tuple[int, Dict[str, Any], str]:
            session = await self._get_session()
            start_time = time.time()

            try:
                async with session.request(
                    method=method,
                    url=full_url,
                    data=data,
                    json=json_data,
                    headers=request_headers,
                    timeout=timeout_value,
                    **kwargs
                ) as response:
                    elapsed = time.time() - start_time

                    # Логируем информацию о запросе с использованием структурированного логирования
                    structured_logger.debug(
                        message=f"{method} request completed",
                        context={
                            "method": method,
                            "url": full_url,
                            "status": response.status,
                            "elapsed": elapsed,
                            "headers": dict(response.headers)
                        }
                    )

                    # Читаем текст ответа
                    text = await response.text()

                    # Пытаемся распарсить JSON
                    try:
                        json_response = await response.json()
                    except (json.JSONDecodeError, aiohttp.ContentTypeError):
                        json_response = {}

                    return response.status, json_response, text

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                elapsed = time.time() - start_time

                # Определяем категорию ошибки
                error_category = ErrorCategory.TIMEOUT_ERROR if isinstance(e, asyncio.TimeoutError) else ErrorCategory.CONNECTION_ERROR

                # Обрабатываем ошибку с использованием структурированного логирования
                error_handler.handle_error(
                    error=e,
                    context={
                        "method": method,
                        "url": full_url,
                        "elapsed": elapsed,
                        "headers": request_headers
                    },
                    log_level="WARNING"
                )

                # Преобразуем исключение в результат с кодом ошибки
                return 0, {}, str(e)

        # Выполняем запрос с механизмом повторных попыток
        return await _execute_request()

    async def get(self,
                 url: str,
                 params: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None,
                 timeout: Optional[float] = None,
                 **kwargs) -> Tuple[int, Dict[str, Any], str]:
        """
        Выполняет GET-запрос асинхронно.

        Args:
            url: URL для запроса
            params: Параметры запроса
            headers: Заголовки запроса
            timeout: Таймаут для запроса в секундах
            **kwargs: Дополнительные параметры для aiohttp.ClientSession.request

        Returns:
            Tuple[int, Dict[str, Any], str]: Статус-код, JSON-ответ (или пустой словарь), текст ответа
        """
        return await self._request("GET", url, params=params, headers=headers, timeout=timeout, **kwargs)

    async def post(self,
                  url: str,
                  data: Optional[Any] = None,
                  json_data: Optional[Dict[str, Any]] = None,
                  params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None,
                  timeout: Optional[float] = None,
                  **kwargs) -> Tuple[int, Dict[str, Any], str]:
        """
        Выполняет POST-запрос асинхронно.

        Args:
            url: URL для запроса
            data: Данные для отправки в теле запроса
            json_data: JSON-данные для отправки в теле запроса
            params: Параметры запроса
            headers: Заголовки запроса
            timeout: Таймаут для запроса в секундах
            **kwargs: Дополнительные параметры для aiohttp.ClientSession.request

        Returns:
            Tuple[int, Dict[str, Any], str]: Статус-код, JSON-ответ (или пустой словарь), текст ответа
        """
        return await self._request("POST", url, data=data, json=json_data, params=params, headers=headers, timeout=timeout, **kwargs)

    async def put(self,
                 url: str,
                 data: Optional[Any] = None,
                 json_data: Optional[Dict[str, Any]] = None,
                 params: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None,
                 timeout: Optional[float] = None,
                 **kwargs) -> Tuple[int, Dict[str, Any], str]:
        """
        Выполняет PUT-запрос асинхронно.

        Args:
            url: URL для запроса
            data: Данные для отправки в теле запроса
            json_data: JSON-данные для отправки в теле запроса
            params: Параметры запроса
            headers: Заголовки запроса
            timeout: Таймаут для запроса в секундах
            **kwargs: Дополнительные параметры для aiohttp.ClientSession.request

        Returns:
            Tuple[int, Dict[str, Any], str]: Статус-код, JSON-ответ (или пустой словарь), текст ответа
        """
        return await self._request("PUT", url, data=data, json=json_data, params=params, headers=headers, timeout=timeout, **kwargs)

    async def delete(self,
                    url: str,
                    params: Optional[Dict[str, Any]] = None,
                    headers: Optional[Dict[str, str]] = None,
                    timeout: Optional[float] = None,
                    **kwargs) -> Tuple[int, Dict[str, Any], str]:
        """
        Выполняет DELETE-запрос асинхронно.

        Args:
            url: URL для запроса
            params: Параметры запроса
            headers: Заголовки запроса
            timeout: Таймаут для запроса в секундах
            **kwargs: Дополнительные параметры для aiohttp.ClientSession.request

        Returns:
            Tuple[int, Dict[str, Any], str]: Статус-код, JSON-ответ (или пустой словарь), текст ответа
        """
        return await self._request("DELETE", url, params=params, headers=headers, timeout=timeout, **kwargs)

    # Синхронные методы для обратной совместимости

    def sync_get(self,
                url: str,
                params: Optional[Dict[str, Any]] = None,
                headers: Optional[Dict[str, str]] = None,
                timeout: Optional[float] = None,
                **kwargs) -> requests.Response:
        """
        Выполняет GET-запрос синхронно (для обратной совместимости).

        Args:
            url: URL для запроса
            params: Параметры запроса
            headers: Заголовки запроса
            timeout: Таймаут для запроса в секундах
            **kwargs: Дополнительные параметры для requests.get

        Returns:
            requests.Response: Ответ requests
        """
        from .retry import sync_retry, default_circuit_breaker

        full_url = self._build_url(url, params)
        request_headers = {**self.headers, **(headers or {})}
        timeout_value = timeout or self.timeout

        # Создаем эндпоинт для Circuit Breaker на основе URL
        endpoint = f"GET:{urlparse(full_url).netloc}"

        # Определяем внутреннюю функцию для выполнения запроса
        @sync_retry(retry_strategy=self.retry_strategy, circuit_breaker=default_circuit_breaker, endpoint=endpoint)
        def _execute_request() -> requests.Response:
            start_time = time.time()

            response = requests.get(
                url=full_url,
                headers=request_headers,
                timeout=timeout_value,
                **kwargs
            )

            elapsed = time.time() - start_time

            # Логируем информацию о запросе с использованием структурированного логирования
            structured_logger.debug(
                message=f"GET request completed",
                context={
                    "method": "GET",
                    "url": full_url,
                    "status": response.status_code,
                    "elapsed": elapsed,
                    "headers": dict(response.headers)
                }
            )

            return response

        # Выполняем запрос с механизмом повторных попыток
        return _execute_request()

    def sync_post(self,
                 url: str,
                 data: Optional[Any] = None,
                 json: Optional[Dict[str, Any]] = None,
                 params: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None,
                 timeout: Optional[float] = None,
                 **kwargs) -> requests.Response:
        """
        Выполняет POST-запрос синхронно (для обратной совместимости).

        Args:
            url: URL для запроса
            data: Данные для отправки в теле запроса
            json: JSON-данные для отправки в теле запроса
            params: Параметры запроса
            headers: Заголовки запроса
            timeout: Таймаут для запроса в секундах
            **kwargs: Дополнительные параметры для requests.post

        Returns:
            requests.Response: Ответ requests
        """
        from .retry import sync_retry, default_circuit_breaker

        full_url = self._build_url(url, params)
        request_headers = {**self.headers, **(headers or {})}
        timeout_value = timeout or self.timeout

        # Создаем эндпоинт для Circuit Breaker на основе URL
        endpoint = f"POST:{urlparse(full_url).netloc}"

        # Определяем внутреннюю функцию для выполнения запроса
        @sync_retry(retry_strategy=self.retry_strategy, circuit_breaker=default_circuit_breaker, endpoint=endpoint)
        def _execute_request() -> requests.Response:
            start_time = time.time()

            response = requests.post(
                url=full_url,
                data=data,
                json=json,
                headers=request_headers,
                timeout=timeout_value,
                **kwargs
            )

            elapsed = time.time() - start_time

            # Логируем информацию о запросе с использованием структурированного логирования
            structured_logger.debug(
                message=f"POST request completed",
                context={
                    "method": "POST",
                    "url": full_url,
                    "status": response.status_code,
                    "elapsed": elapsed,
                    "headers": dict(response.headers)
                }
            )

            return response

        # Выполняем запрос с механизмом повторных попыток
        return _execute_request()


# Создаем глобальный экземпляр HTTP-клиента
http_client = HTTPClient()
