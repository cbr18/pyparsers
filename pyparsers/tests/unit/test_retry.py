"""
Юнит-тесты для модуля retry.
"""

import pytest
import asyncio
import time
from unittest import mock
from api.retry import RetryStrategy, CircuitBreaker, async_retry, sync_retry, CircuitState


class TestRetryStrategy:
    """Тесты для класса RetryStrategy."""

    def test_init(self):
        """Тест инициализации RetryStrategy."""
        strategy = RetryStrategy(
            max_retries=5,
            retry_delay=2.0,
            backoff_factor=3.0,
            jitter=False,
            retry_on_status_codes=[500, 501],
            retry_on_exceptions=[ValueError, TypeError]
        )

        assert strategy.max_retries == 5
        assert strategy.retry_delay == 2.0
        assert strategy.backoff_factor == 3.0
        assert strategy.jitter is False
        assert strategy.retry_on_status_codes == [500, 501]
        assert ValueError in strategy.retry_on_exceptions
        assert TypeError in strategy.retry_on_exceptions

    def test_should_retry(self):
        """Тест метода should_retry."""
        strategy = RetryStrategy(
            max_retries=3,
            retry_on_status_codes=[500, 502],
            retry_on_exceptions=[ValueError, TypeError]
        )

        # Проверяем, что повторная попытка выполняется при указанных кодах состояния
        assert strategy.should_retry(0, status_code=500) is True
        assert strategy.should_retry(0, status_code=502) is True
        assert strategy.should_retry(0, status_code=404) is False

        # Проверяем, что повторная попытка выполняется при указанных исключениях
        assert strategy.should_retry(0, exception=ValueError()) is True
        assert strategy.should_retry(0, exception=TypeError()) is True
        assert strategy.should_retry(0, exception=KeyError()) is False

        # Проверяем, что повторная попытка не выполняется, если превышено максимальное количество попыток
        assert strategy.should_retry(3, status_code=500) is False
        assert strategy.should_retry(3, exception=ValueError()) is False

    def test_get_delay(self):
        """Тест метода get_delay."""
        # Тест без jitter
        strategy = RetryStrategy(
            retry_delay=1.0,
            backoff_factor=2.0,
            jitter=False
        )

        assert strategy.get_delay(0) == 1.0
        assert strategy.get_delay(1) == 2.0
        assert strategy.get_delay(2) == 4.0

        # Тест с jitter
        strategy = RetryStrategy(
            retry_delay=1.0,
            backoff_factor=2.0,
            jitter=True
        )

        # С jitter задержка должна быть в пределах ±25% от базовой
        delay = strategy.get_delay(0)
        assert 0.75 <= delay <= 1.25

        delay = strategy.get_delay(1)
        assert 1.5 <= delay <= 2.5


class TestCircuitBreaker:
    """Тесты для класса CircuitBreaker."""

    def test_init(self):
        """Тест инициализации CircuitBreaker."""
        cb = CircuitBreaker(
            failure_threshold=10,
            recovery_timeout=60.0,
            half_open_max_calls=5,
            reset_timeout=120.0
        )

        assert cb.failure_threshold == 10
        assert cb.recovery_timeout == 60.0
        assert cb.half_open_max_calls == 5
        assert cb.reset_timeout == 120.0
        assert cb.state == CircuitState.CLOSED
        assert cb.failures == 0

    def test_get_endpoint_state(self):
        """Тест метода get_endpoint_state."""
        cb = CircuitBreaker()

        # Проверяем, что для нового эндпоинта создается состояние
        state = cb.get_endpoint_state("test_endpoint")
        assert state["state"] == CircuitState.CLOSED
        assert state["failures"] == 0

        # Проверяем, что для существующего эндпоинта возвращается его состояние
        cb.endpoints["test_endpoint"]["failures"] = 3
        state = cb.get_endpoint_state("test_endpoint")
        assert state["failures"] == 3

    def test_record_success(self):
        """Тест метода record_success."""
        cb = CircuitBreaker(half_open_max_calls=3)
        endpoint = "test_endpoint"

        # Проверяем, что при успешном выполнении запроса в состоянии CLOSED
        # обновляется время последнего успеха
        cb.record_success(endpoint)
        assert cb.get_endpoint_state(endpoint)["state"] == CircuitState.CLOSED

        # Проверяем, что при успешном выполнении запроса в состоянии HALF_OPEN
        # увеличивается счетчик успешных запросов
        cb.get_endpoint_state(endpoint)["state"] = CircuitState.HALF_OPEN
        cb.record_success(endpoint)
        assert cb.get_endpoint_state(endpoint)["half_open_calls"] == 1

        # Проверяем, что при достижении порога успешных запросов в состоянии HALF_OPEN
        # происходит переход в состояние CLOSED
        cb.record_success(endpoint)
        cb.record_success(endpoint)
        assert cb.get_endpoint_state(endpoint)["state"] == CircuitState.CLOSED
        assert cb.get_endpoint_state(endpoint)["failures"] == 0
        assert cb.get_endpoint_state(endpoint)["half_open_calls"] == 0

    def test_record_failure(self):
        """Тест метода record_failure."""
        cb = CircuitBreaker(failure_threshold=3)
        endpoint = "test_endpoint"

        # Проверяем, что при ошибке выполнения запроса в состоянии CLOSED
        # увеличивается счетчик ошибок
        cb.record_failure(endpoint)
        assert cb.get_endpoint_state(endpoint)["failures"] == 1
        assert cb.get_endpoint_state(endpoint)["state"] == CircuitState.CLOSED

        # Проверяем, что при достижении порога ошибок в состоянии CLOSED
        # происходит переход в состояние OPEN
        cb.record_failure(endpoint)
        cb.record_failure(endpoint)
        assert cb.get_endpoint_state(endpoint)["failures"] == 3
        assert cb.get_endpoint_state(endpoint)["state"] == CircuitState.OPEN

        # Проверяем, что при ошибке выполнения запроса в состоянии HALF_OPEN
        # происходит переход в состояние OPEN
        cb.get_endpoint_state(endpoint)["state"] = CircuitState.HALF_OPEN
        cb.get_endpoint_state(endpoint)["half_open_calls"] = 1
        cb.record_failure(endpoint)
        assert cb.get_endpoint_state(endpoint)["state"] == CircuitState.OPEN
        assert cb.get_endpoint_state(endpoint)["half_open_calls"] == 0

    def test_allow_request(self):
        """Тест метода allow_request."""
        cb = CircuitBreaker(recovery_timeout=0.1)
        endpoint = "test_endpoint"

        # Проверяем, что в состоянии CLOSED запросы разрешены
        assert cb.allow_request(endpoint) is True

        # Проверяем, что в состоянии OPEN запросы запрещены
        cb.get_endpoint_state(endpoint)["state"] = CircuitState.OPEN
        assert cb.allow_request(endpoint) is False

        # Проверяем, что после истечения recovery_timeout в состоянии OPEN
        # происходит переход в состояние HALF_OPEN и запросы разрешены
        time.sleep(0.2)
        assert cb.allow_request(endpoint) is True
        assert cb.get_endpoint_state(endpoint)["state"] == CircuitState.HALF_OPEN

        # Проверяем, что в состоянии HALF_OPEN разрешено ограниченное количество запросов
        cb.get_endpoint_state(endpoint)["half_open_calls"] = cb.half_open_max_calls - 1
        assert cb.allow_request(endpoint) is True

        cb.get_endpoint_state(endpoint)["half_open_calls"] = cb.half_open_max_calls
        assert cb.allow_request(endpoint) is False


class TestAsyncRetry:
    """Тесты для декоратора async_retry."""

    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        """Тест успешного выполнения функции с декоратором async_retry."""
        retry_strategy = RetryStrategy(max_retries=3)

        @async_retry(retry_strategy=retry_strategy)
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_retry_with_exception(self):
        """Тест повторных попыток при исключении."""
        retry_strategy = RetryStrategy(
            max_retries=3,
            retry_delay=0.1,
            retry_on_exceptions=[ValueError]
        )

        mock_func = mock.AsyncMock(side_effect=[ValueError("error"), ValueError("error"), "success"])

        @async_retry(retry_strategy=retry_strategy)
        async def test_func():
            return await mock_func()

        result = await test_func()
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_with_status_code(self):
        """Тест повторных попыток при определенных кодах состояния."""
        retry_strategy = RetryStrategy(
            max_retries=3,
            retry_delay=0.1,
            retry_on_status_codes=[500]
        )

        mock_func = mock.AsyncMock(side_effect=[(500, {}, "error"), (500, {}, "error"), (200, {"key": "value"}, "success")])

        @async_retry(retry_strategy=retry_strategy)
        async def test_func():
            return await mock_func()

        status, data, text = await test_func()
        assert status == 200
        assert data == {"key": "value"}
        assert text == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_max_retries_exceeded(self):
        """Тест превышения максимального количества попыток."""
        retry_strategy = RetryStrategy(
            max_retries=2,
            retry_delay=0.1,
            retry_on_exceptions=[ValueError]
        )

        mock_func = mock.AsyncMock(side_effect=[ValueError("error"), ValueError("error"), ValueError("error")])

        @async_retry(retry_strategy=retry_strategy)
        async def test_func():
            return await mock_func()

        with pytest.raises(ValueError):
            await test_func()

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_with_circuit_breaker(self):
        """Тест взаимодействия с Circuit Breaker."""
        retry_strategy = RetryStrategy(
            max_retries=2,
            retry_delay=0.1,
            retry_on_exceptions=[ValueError]
        )

        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1
        )

        mock_func = mock.AsyncMock(side_effect=[ValueError("error"), ValueError("error")])

        @async_retry(retry_strategy=retry_strategy, circuit_breaker=circuit_breaker, endpoint="test_endpoint")
        async def test_func():
            return await mock_func()

        # Первый вызов должен вызвать исключение и зарегистрировать ошибку в Circuit Breaker
        with pytest.raises(ValueError):
            await test_func()

        assert mock_func.call_count == 3
        assert circuit_breaker.get_endpoint_state("test_endpoint")["failures"] == 1

        # Второй вызов должен вызвать исключение и перевести Circuit Breaker в состояние OPEN
        mock_func.reset_mock()
        mock_func.side_effect = [ValueError("error"), ValueError("error")]

        with pytest.raises(ValueError):
            await test_func()

        assert circuit_breaker.get_endpoint_state("test_endpoint")["state"] == CircuitState.OPEN

        # Третий вызов должен быть запрещен Circuit Breaker
        mock_func.reset_mock()

        with pytest.raises(Exception) as excinfo:
            await test_func()

        assert "Circuit Breaker is OPEN" in str(excinfo.value)
        assert mock_func.call_count == 0

        # После истечения recovery_timeout Circuit Breaker должен перейти в состояние HALF_OPEN
        time.sleep(0.2)
        mock_func.reset_mock()
        mock_func.side_effect = ["success"]

        result = await test_func()
        assert result == "success"
        assert circuit_breaker.get_endpoint_state("test_endpoint")["state"] == CircuitState.HALF_OPEN
        assert circuit_breaker.get_endpoint_state("test_endpoint")["half_open_calls"] == 1


class TestSyncRetry:
    """Тесты для декоратора sync_retry."""

    def test_sync_retry_success(self):
        """Тест успешного выполнения функции с декоратором sync_retry."""
        retry_strategy = RetryStrategy(max_retries=3)

        @sync_retry(retry_strategy=retry_strategy)
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_sync_retry_with_exception(self):
        """Тест повторных попыток при исключении."""
        retry_strategy = RetryStrategy(
            max_retries=3,
            retry_delay=0.1,
            retry_on_exceptions=[ValueError]
        )

        mock_func = mock.Mock(side_effect=[ValueError("error"), ValueError("error"), "success"])

        @sync_retry(retry_strategy=retry_strategy)
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_sync_retry_max_retries_exceeded(self):
        """Тест превышения максимального количества попыток."""
        retry_strategy = RetryStrategy(
            max_retries=2,
            retry_delay=0.1,
            retry_on_exceptions=[ValueError]
        )

        mock_func = mock.Mock(side_effect=[ValueError("error"), ValueError("error"), ValueError("error")])

        @sync_retry(retry_strategy=retry_strategy)
        def test_func():
            return mock_func()

        with pytest.raises(ValueError):
            test_func()

        assert mock_func.call_count == 3

    def test_sync_retry_with_circuit_breaker(self):
        """Тест взаимодействия с Circuit Breaker."""
        retry_strategy = RetryStrategy(
            max_retries=2,
            retry_delay=0.1,
            retry_on_exceptions=[ValueError]
        )

        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1
        )

        mock_func = mock.Mock(side_effect=[ValueError("error"), ValueError("error")])

        @sync_retry(retry_strategy=retry_strategy, circuit_breaker=circuit_breaker, endpoint="test_endpoint")
        def test_func():
            return mock_func()

        # Первый вызов должен вызвать исключение и зарегистрировать ошибку в Circuit Breaker
        with pytest.raises(ValueError):
            test_func()

        assert mock_func.call_count == 3
        assert circuit_breaker.get_endpoint_state("test_endpoint")["failures"] == 1

        # Второй вызов должен вызвать исключение и перевести Circuit Breaker в состояние OPEN
        mock_func.reset_mock()
        mock_func.side_effect = [ValueError("error"), ValueError("error")]

        with pytest.raises(ValueError):
            test_func()

        assert circuit_breaker.get_endpoint_state("test_endpoint")["state"] == CircuitState.OPEN

        # Третий вызов должен быть запрещен Circuit Breaker
        mock_func.reset_mock()

        with pytest.raises(Exception) as excinfo:
            test_func()

        assert "Circuit Breaker is OPEN" in str(excinfo.value)
        assert mock_func.call_count == 0

        # После истечения recovery_timeout Circuit Breaker должен перейти в состояние HALF_OPEN
        time.sleep(0.2)
        mock_func.reset_mock()
        mock_func.side_effect = ["success"]

        result = test_func()
        assert result == "success"
        assert circuit_breaker.get_endpoint_state("test_endpoint")["state"] == CircuitState.HALF_OPEN
        assert circuit_breaker.get_endpoint_state("test_endpoint")["half_open_calls"] == 1
