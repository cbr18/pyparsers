"""
Модуль для ограничения ресурсов и регулирования нагрузки.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, TypeVar, Awaitable, List, Set
from functools import wraps

# Настройка логирования
logger = logging.getLogger(__name__)

# Типы для аннотаций
T = TypeVar('T')
AsyncFunc = Callable[..., Awaitable[T]]


class RateLimiter:
    """
    Класс для ограничения скорости запросов (rate limiting).

    Реализует алгоритм "token bucket" для ограничения скорости запросов.
    """

    def __init__(self,
                 rate: float = 10.0,
                 burst: int = 20,
                 per_endpoint: bool = False):
        """
        Инициализирует ограничитель скорости запросов.

        Args:
            rate: Максимальное количество запросов в секунду
            burst: Максимальное количество запросов, которые можно выполнить сразу
            per_endpoint: Применять ограничения отдельно для каждого эндпоинта
        """
        self.rate = rate
        self.burst = burst
        self.per_endpoint = per_endpoint

        # Состояние для глобального ограничителя
        self.tokens = burst
        self.last_refill_time = time.time()

        # Состояние для ограничителей по эндпоинтам
        self.endpoint_states: Dict[str, Dict[str, Any]] = {}

        logger.info(f"Rate limiter initialized with rate={rate} requests/s, burst={burst}")

    def _get_endpoint_state(self, endpoint: str) -> Dict[str, Any]:
        """
        Возвращает состояние для указанного эндпоинта.

        Args:
            endpoint: Эндпоинт, для которого нужно получить состояние

        Returns:
            Dict[str, Any]: Состояние эндпоинта
        """
        if endpoint not in self.endpoint_states:
            self.endpoint_states[endpoint] = {
                'tokens': self.burst,
                'last_refill_time': time.time()
            }

        return self.endpoint_states[endpoint]

    def _refill_tokens(self, state: Dict[str, Any]) -> None:
        """
        Пополняет токены в соответствии с прошедшим временем.

        Args:
            state: Состояние ограничителя
        """
        now = time.time()
        elapsed = now - state['last_refill_time']

        # Вычисляем количество новых токенов
        new_tokens = elapsed * self.rate

        # Обновляем состояние
        state['tokens'] = min(state['tokens'] + new_tokens, self.burst)
        state['last_refill_time'] = now

    async def acquire(self, endpoint: Optional[str] = None) -> float:
        """
        Запрашивает разрешение на выполнение запроса.

        Args:
            endpoint: Эндпоинт, для которого запрашивается разрешение

        Returns:
            float: Время ожидания в секундах
        """
        # Определяем состояние ограничителя
        state = self._get_endpoint_state(endpoint) if self.per_endpoint and endpoint else {
            'tokens': self.tokens,
            'last_refill_time': self.last_refill_time
        }

        # Пополняем токены
        self._refill_tokens(state)

        # Если токенов достаточно, разрешаем запрос немедленно
        if state['tokens'] >= 1:
            state['tokens'] -= 1

            # Обновляем глобальное состояние, если не используем per_endpoint
            if not self.per_endpoint or not endpoint:
                self.tokens = state['tokens']
                self.last_refill_time = state['last_refill_time']

            return 0.0

        # Вычисляем время ожидания до появления токена
        wait_time = (1 - state['tokens']) / self.rate

        # Обновляем состояние
        state['tokens'] = 0

        # Обновляем глобальное состояние, если не используем per_endpoint
        if not self.per_endpoint or not endpoint:
            self.tokens = state['tokens']
            self.last_refill_time = state['last_refill_time']

        logger.debug(f"Rate limit exceeded for {endpoint or 'global'}. Waiting {wait_time:.2f}s")

        # Ждем появления токена
        await asyncio.sleep(wait_time)

        # Повторно пополняем токены после ожидания
        self._refill_tokens(state)

        # Используем токен
        state['tokens'] -= 1

        # Обновляем глобальное состояние, если не используем per_endpoint
        if not self.per_endpoint or not endpoint:
            self.tokens = state['tokens']
            self.last_refill_time = state['last_refill_time']

        return wait_time


class ConcurrencyLimiter:
    """
    Класс для ограничения количества одновременных запросов.
    """

    def __init__(self,
                 max_concurrency: int = 10,
                 per_endpoint: bool = False):
        """
        Инициализирует ограничитель количества одновременных запросов.

        Args:
            max_concurrency: Максимальное количество одновременных запросов
            per_endpoint: Применять ограничения отдельно для каждого эндпоинта
        """
        self.max_concurrency = max_concurrency
        self.per_endpoint = per_endpoint

        # Глобальный семафор
        self.semaphore = asyncio.Semaphore(max_concurrency)

        # Семафоры для эндпоинтов
        self.endpoint_semaphores: Dict[str, asyncio.Semaphore] = {}

        # Счетчики активных запросов
        self.active_requests = 0
        self.endpoint_active_requests: Dict[str, int] = {}

        logger.info(f"Concurrency limiter initialized with max_concurrency={max_concurrency}")

    def _get_endpoint_semaphore(self, endpoint: str) -> asyncio.Semaphore:
        """
        Возвращает семафор для указанного эндпоинта.

        Args:
            endpoint: Эндпоинт, для которого нужно получить семафор

        Returns:
            asyncio.Semaphore: Семафор для эндпоинта
        """
        if endpoint not in self.endpoint_semaphores:
            self.endpoint_semaphores[endpoint] = asyncio.Semaphore(self.max_concurrency)
            self.endpoint_active_requests[endpoint] = 0

        return self.endpoint_semaphores[endpoint]

    async def acquire(self, endpoint: Optional[str] = None) -> None:
        """
        Запрашивает разрешение на выполнение запроса.

        Args:
            endpoint: Эндпоинт, для которого запрашивается разрешение
        """
        # Определяем семафор
        semaphore = self._get_endpoint_semaphore(endpoint) if self.per_endpoint and endpoint else self.semaphore

        # Ждем разрешения
        await semaphore.acquire()

        # Увеличиваем счетчик активных запросов
        self.active_requests += 1
        if self.per_endpoint and endpoint:
            self.endpoint_active_requests[endpoint] += 1

    def release(self, endpoint: Optional[str] = None) -> None:
        """
        Освобождает ресурс после выполнения запроса.

        Args:
            endpoint: Эндпоинт, для которого освобождается ресурс
        """
        # Определяем семафор
        semaphore = self._get_endpoint_semaphore(endpoint) if self.per_endpoint and endpoint else self.semaphore

        # Освобождаем ресурс
        semaphore.release()

        # Уменьшаем счетчик активных запросов
        self.active_requests -= 1
        if self.per_endpoint and endpoint:
            self.endpoint_active_requests[endpoint] -= 1

    def get_active_requests(self, endpoint: Optional[str] = None) -> int:
        """
        Возвращает количество активных запросов.

        Args:
            endpoint: Эндпоинт, для которого нужно получить количество активных запросов

        Returns:
            int: Количество активных запросов
        """
        if self.per_endpoint and endpoint:
            return self.endpoint_active_requests.get(endpoint, 0)
        else:
            return self.active_requests


class ResourceManager:
    """
    Класс для управления ресурсами и регулирования нагрузки.
    """

    def __init__(self,
                 rate_limit: float = 10.0,
                 burst: int = 20,
                 max_concurrency: int = 10,
                 per_endpoint: bool = True):
        """
        Инициализирует менеджер ресурсов.

        Args:
            rate_limit: Максимальное количество запросов в секунду
            burst: Максимальное количество запросов, которые можно выполнить сразу
            max_concurrency: Максимальное количество одновременных запросов
            per_endpoint: Применять ограничения отдельно для каждого эндпоинта
        """
        self.rate_limiter = RateLimiter(rate=rate_limit, burst=burst, per_endpoint=per_endpoint)
        self.concurrency_limiter = ConcurrencyLimiter(max_concurrency=max_concurrency, per_endpoint=per_endpoint)
        self.per_endpoint = per_endpoint

        logger.info(f"Resource manager initialized with rate_limit={rate_limit} requests/s, "
                   f"burst={burst}, max_concurrency={max_concurrency}, per_endpoint={per_endpoint}")

    async def acquire(self, endpoint: Optional[str] = None) -> float:
        """
        Запрашивает разрешение на выполнение запроса.

        Args:
            endpoint: Эндпоинт, для которого запрашивается разрешение

        Returns:
            float: Время ожидания в секундах
        """
        # Ограничиваем количество одновременных запросов
        await self.concurrency_limiter.acquire(endpoint)

        try:
            # Ограничиваем скорость запросов
            wait_time = await self.rate_limiter.acquire(endpoint)
            return wait_time
        except Exception as e:
            # В случае ошибки освобождаем ресурс
            self.concurrency_limiter.release(endpoint)
            raise e

    def release(self, endpoint: Optional[str] = None) -> None:
        """
        Освобождает ресурс после выполнения запроса.

        Args:
            endpoint: Эндпоинт, для которого освобождается ресурс
        """
        self.concurrency_limiter.release(endpoint)

    def get_active_requests(self, endpoint: Optional[str] = None) -> int:
        """
        Возвращает количество активных запросов.

        Args:
            endpoint: Эндпоинт, для которого нужно получить количество активных запросов

        Returns:
            int: Количество активных запросов
        """
        return self.concurrency_limiter.get_active_requests(endpoint)


# Декоратор для ограничения ресурсов
def throttle(resource_manager: Optional[ResourceManager] = None,
             endpoint: Optional[str] = None):
    """
    Декоратор для ограничения ресурсов и регулирования нагрузки.

    Args:
        resource_manager: Менеджер ресурсов
        endpoint: Эндпоинт, для которого применяется ограничение

    Returns:
        Callable: Декорированная функция
    """
    # Создаем глобальный менеджер ресурсов, если не указан
    if resource_manager is None:
        resource_manager = default_resource_manager

    def decorator(func: AsyncFunc[T]) -> AsyncFunc[T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Определяем эндпоинт
            endpoint_name = endpoint or func.__name__

            # Запрашиваем разрешение на выполнение запроса
            wait_time = await resource_manager.acquire(endpoint_name)

            if wait_time > 0:
                logger.debug(f"Throttled {endpoint_name}: waited {wait_time:.2f}s")

            try:
                # Выполняем функцию
                return await func(*args, **kwargs)
            finally:
                # Освобождаем ресурс
                resource_manager.release(endpoint_name)

        return wrapper

    return decorator


# Создаем глобальный менеджер ресурсов
default_resource_manager = ResourceManager()
