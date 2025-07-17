"""
Модуль для управления повторными попытками и реализации паттерна Circuit Breaker.
"""

import asyncio
import logging
import time
import random
from enum import Enum
from typing import Callable, TypeVar, Any, Optional, Dict, List, Tuple
from functools import wraps

# Настройка структурированного логирования
from .logging_utils import StructuredLogger, ErrorHandler, ErrorCategory, log_async_function, log_function

structured_logger = StructuredLogger(name="retry", json_format=True)
error_handler = ErrorHandler(logger=structured_logger)

# Для обратной совместимости
logger = logging.getLogger(__name__)

# Типы для аннотаций
T = TypeVar('T')
AsyncFunc = Callable[..., Any]
SyncFunc = Callable[..., Any]

class CircuitState(Enum):
    """Состояния для паттерна Circuit Breaker."""
    CLOSED = 'closed'  # Нормальное состояние, запросы выполняются
    OPEN = 'open'      # Состояние ошибки, запросы не выполняются
    HALF_OPEN = 'half_open'  # Пробное состояние, выполняется ограниченное количество запросов


class CircuitBreaker:
    """
    Реализация паттерна Circuit Breaker для предотвращения каскадных отказов.

    Circuit Breaker отслеживает количество ошибок и, при превышении порога,
    переходит в состояние OPEN, в котором запросы не выполняются в течение
    определенного времени. После этого переходит в состояние HALF_OPEN,
    в котором выполняется ограниченное количество запросов для проверки
    доступности сервиса.
    """

    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 30.0,
                 half_open_max_calls: int = 3,
                 reset_timeout: float = 60.0):
        """
        Инициализирует Circuit Breaker.

        Args:
            failure_threshold: Порог количества ошибок для перехода в состояние OPEN
            recovery_timeout: Время в секундах, через которое происходит переход из OPEN в HALF_OPEN
            half_open_max_calls: Максимальное количество запросов в состоянии HALF_OPEN
            reset_timeout: Время в секундах, через которое сбрасывается счетчик ошибок
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.reset_timeout = reset_timeout

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0
        self.last_success_time = time.time()
        self.half_open_calls = 0

        # Словарь для хранения состояний для разных эндпоинтов
        self.endpoints: Dict[str, Dict[str, Any]] = {}

        structured_logger.info(
            message=f"Circuit Breaker initialized",
            context={
                "failure_threshold": failure_threshold,
                "recovery_timeout": recovery_timeout,
                "half_open_max_calls": half_open_max_calls,
                "reset_timeout": reset_timeout
            }
        )

    def get_endpoint_state(self, endpoint: str) -> Dict[str, Any]:
        """
        Возвращает состояние для указанного эндпоинта.

        Args:
            endpoint: Эндпоинт, для которого нужно получить состояние

        Returns:
            Dict[str, Any]: Состояние эндпоинта
        """
        if endpoint not in self.endpoints:
            self.endpoints[endpoint] = {
                'state': CircuitState.CLOSED,
                'failures': 0,
                'last_failure_time': 0,
                'last_success_time': time.time(),
                'half_open_calls': 0
            }

        return self.endpoints[endpoint]

    def record_success(self, endpoint: str):
        """
        Регистрирует успешное выполнение запроса.

        Args:
            endpoint: Эндпоинт, для которого регистрируется успех
        """
        state = self.get_endpoint_state(endpoint)

        if state['state'] == CircuitState.HALF_OPEN:
            state['half_open_calls'] += 1

            if state['half_open_calls'] >= self.half_open_max_calls:
                state['state'] = CircuitState.CLOSED
                state['failures'] = 0
                state['half_open_calls'] = 0
                structured_logger.info(
                    message=f"Circuit Breaker transitioned from HALF_OPEN to CLOSED",
                    context={
                        "endpoint": endpoint,
                        "state": "CLOSED",
                        "failures": 0
                    }
                )

        state['last_success_time'] = time.time()

        # Сбрасываем счетчик ошибок, если прошло достаточно времени с последней ошибки
        if (time.time() - state['last_failure_time']) > self.reset_timeout:
            state['failures'] = 0

    def record_failure(self, endpoint: str):
        """
        Регистрирует ошибку выполнения запроса.

        Args:
            endpoint: Эндпоинт, для которого регистрируется ошибка
        """
        state = self.get_endpoint_state(endpoint)

        state['failures'] += 1
        state['last_failure_time'] = time.time()

        if state['state'] == CircuitState.CLOSED and state['failures'] >= self.failure_threshold:
            state['state'] = CircuitState.OPEN
            structured_logger.warning(
                message=f"Circuit Breaker transitioned from CLOSED to OPEN",
                context={
                    "endpoint": endpoint,
                    "state": "OPEN",
                    "failures": state['failures']
                }
            )

        if state['state'] == CircuitState.HALF_OPEN:
            state['state'] = CircuitState.OPEN
            state['half_open_calls'] = 0
            structured_logger.warning(
                message=f"Circuit Breaker transitioned from HALF_OPEN to OPEN after failure during testing",
                context={
                    "endpoint": endpoint,
                    "state": "OPEN",
                    "failures": state['failures']
                }
            )

    def allow_request(self, endpoint: str) -> bool:
        """
        Проверяет, можно ли выполнить запрос.

        Args:
            endpoint: Эндпоинт, для которого проверяется возможность выполнения запроса

        Returns:
            bool: True, если запрос можно выполнить, False в противном случае
        """
        state = self.get_endpoint_state(endpoint)

        if state['state'] == CircuitState.CLOSED:
            return True

        if state['state'] == CircuitState.OPEN:
            # Проверяем, прошло ли достаточно времени для перехода в HALF_OPEN
            if (time.time() - state['last_failure_time']) > self.recovery_timeout:
                state['state'] = CircuitState.HALF_OPEN
                state['half_open_calls'] = 0
                structured_logger.info(
                    message=f"Circuit Breaker transitioned from OPEN to HALF_OPEN",
                    context={
                        "endpoint": endpoint,
                        "state": "HALF_OPEN",
                        "recovery_timeout": self.recovery_timeout
                    }
                )
                return True
            return False

        if state['state'] == CircuitState.HALF_OPEN:
            # В состоянии HALF_OPEN разрешаем ограниченное количество запросов
            return state['half_open_calls'] < self.half_open_max_calls

        return True


class RetryStrategy:
    """
    Стратегия повторных попыток для HTTP-запросов.
    """

    def __init__(self,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 backoff_factor: float = 2.0,
                 jitter: bool = True,
                 retry_on_status_codes: List[int] = None,
                 retry_on_exceptions: List[Exception] = None):
        """
        Инициализирует стратегию повторных попыток.

        Args:
            max_retries: Максимальное количество повторных попыток
            retry_delay: Начальная задержка между попытками в секундах
            backoff_factor: Множитель для экспоненциальной задержки
            jitter: Добавлять случайное отклонение к задержке
            retry_on_status_codes: Список кодов состояния HTTP, при которых нужно повторять запрос
            retry_on_exceptions: Список исключений, при которых нужно повторять запрос
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on_status_codes = retry_on_status_codes or [500, 502, 503, 504]
        self.retry_on_exceptions = retry_on_exceptions or []

        structured_logger.info(
            message=f"Retry strategy initialized",
            context={
                "max_retries": max_retries,
                "retry_delay": retry_delay,
                "backoff_factor": backoff_factor,
                "jitter": jitter,
                "retry_on_status_codes": self.retry_on_status_codes,
                "retry_on_exceptions": [exc.__name__ for exc in self.retry_on_exceptions]
            }
        )

    def should_retry(self, attempt: int, status_code: Optional[int] = None, exception: Optional[Exception] = None) -> bool:
        """
        Проверяет, нужно ли повторить попытку.

        Args:
            attempt: Номер текущей попытки (начиная с 0)
            status_code: Код состояния HTTP
            exception: Исключение, если произошло

        Returns:
            bool: True, если нужно повторить попытку, False в противном случае
        """
        # Проверяем, не превышено ли максимальное количество попыток
        if attempt >= self.max_retries:
            return False

        # Проверяем код состояния
        if status_code is not None and status_code in self.retry_on_status_codes:
            return True

        # Проверяем исключение
        if exception is not None:
            for exc_type in self.retry_on_exceptions:
                if isinstance(exception, exc_type):
                    return True

        return False

    def get_delay(self, attempt: int) -> float:
        """
        Возвращает задержку перед следующей попыткой.

        Args:
            attempt: Номер текущей попытки (начиная с 0)

        Returns:
            float: Задержка в секундах
        """
        delay = self.retry_delay * (self.backoff_factor ** attempt)

        if self.jitter:
            # Добавляем случайное отклонение ±25%
            jitter_factor = 1.0 + random.uniform(-0.25, 0.25)
            delay *= jitter_factor

        return delay


# Декораторы для повторных попыток

def async_retry(retry_strategy: Optional[RetryStrategy] = None,
                circuit_breaker: Optional[CircuitBreaker] = None,
                endpoint: Optional[str] = None):
    """
    Декоратор для асинхронных функций с повторными попытками.

    Args:
        retry_strategy: Стратегия повторных попыток
        circuit_breaker: Circuit Breaker для предотвращения каскадных отказов
        endpoint: Эндпоинт для Circuit Breaker

    Returns:
        Callable: Декорированная функция
    """
    retry_strategy = retry_strategy or RetryStrategy()

    def decorator(func: AsyncFunc) -> AsyncFunc:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Определяем эндпоинт для Circuit Breaker
            cb_endpoint = endpoint or func.__name__

            # Проверяем, можно ли выполнить запрос
            if circuit_breaker and not circuit_breaker.allow_request(cb_endpoint):
                structured_logger.warning(
                    message=f"Circuit Breaker prevented request",
                    context={
                        "endpoint": cb_endpoint,
                        "state": "OPEN"
                    }
                )
                raise Exception(f"Circuit Breaker is OPEN for {cb_endpoint}")

            attempt = 0
            last_exception = None
            last_status_code = None

            while True:
                try:
                    result = await func(*args, **kwargs)

                    # Если функция возвращает кортеж (status_code, response, text),
                    # проверяем код состояния
                    if isinstance(result, tuple) and len(result) >= 1 and isinstance(result[0], int):
                        status_code = result[0]

                        if retry_strategy.should_retry(attempt, status_code=status_code):
                            last_status_code = status_code
                            attempt += 1
                            delay = retry_strategy.get_delay(attempt)

                            structured_logger.warning(
                                message=f"Retrying due to status code",
                                context={
                                    "function": func.__name__,
                                    "attempt": attempt,
                                    "max_retries": retry_strategy.max_retries,
                                    "delay": delay,
                                    "status_code": status_code
                                }
                            )

                            await asyncio.sleep(delay)
                            continue

                    # Регистрируем успех в Circuit Breaker
                    if circuit_breaker:
                        circuit_breaker.record_success(cb_endpoint)

                    return result

                except Exception as e:
                    last_exception = e

                    if retry_strategy.should_retry(attempt, exception=e):
                        attempt += 1
                        delay = retry_strategy.get_delay(attempt)

                        structured_logger.warning(
                            message=f"Retrying due to exception",
                            context={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_retries": retry_strategy.max_retries,
                                "delay": delay,
                                "error": str(e),
                                "error_type": e.__class__.__name__
                            }
                        )

                        await asyncio.sleep(delay)
                    else:
                        # Регистрируем ошибку в Circuit Breaker
                        if circuit_breaker:
                            circuit_breaker.record_failure(cb_endpoint)

                        raise

            # Этот код не должен выполняться, но на всякий случай
            if last_exception:
                raise last_exception
            elif last_status_code:
                return (last_status_code, {}, "")
            else:
                return None

        return wrapper

    return decorator


def sync_retry(retry_strategy: Optional[RetryStrategy] = None,
               circuit_breaker: Optional[CircuitBreaker] = None,
               endpoint: Optional[str] = None):
    """
    Декоратор для синхронных функций с повторными попытками.

    Args:
        retry_strategy: Стратегия повторных попыток
        circuit_breaker: Circuit Breaker для предотвращения каскадных отказов
        endpoint: Эндпоинт для Circuit Breaker

    Returns:
        Callable: Декорированная функция
    """
    retry_strategy = retry_strategy or RetryStrategy()

    def decorator(func: SyncFunc) -> SyncFunc:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Определяем эндпоинт для Circuit Breaker
            cb_endpoint = endpoint or func.__name__

            # Проверяем, можно ли выполнить запрос
            if circuit_breaker and not circuit_breaker.allow_request(cb_endpoint):
                structured_logger.warning(
                    message=f"Circuit Breaker prevented request",
                    context={
                        "endpoint": cb_endpoint,
                        "state": "OPEN"
                    }
                )
                raise Exception(f"Circuit Breaker is OPEN for {cb_endpoint}")

            attempt = 0
            last_exception = None

            while True:
                try:
                    result = func(*args, **kwargs)

                    # Регистрируем успех в Circuit Breaker
                    if circuit_breaker:
                        circuit_breaker.record_success(cb_endpoint)

                    return result

                except Exception as e:
                    last_exception = e

                    if retry_strategy.should_retry(attempt, exception=e):
                        attempt += 1
                        delay = retry_strategy.get_delay(attempt)

                        structured_logger.warning(
                            message=f"Retrying due to exception",
                            context={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_retries": retry_strategy.max_retries,
                                "delay": delay,
                                "error": str(e),
                                "error_type": e.__class__.__name__
                            }
                        )

                        time.sleep(delay)
                    else:
                        # Регистрируем ошибку в Circuit Breaker
                        if circuit_breaker:
                            circuit_breaker.record_failure(cb_endpoint)

                        raise

            # Этот код не должен выполняться, но на всякий случай
            if last_exception:
                raise last_exception
            else:
                return None

        return wrapper

    return decorator


# Создаем глобальные экземпляры для использования в приложении
default_retry_strategy = RetryStrategy()
default_circuit_breaker = CircuitBreaker()
