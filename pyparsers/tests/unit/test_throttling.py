"""
Юнит-тесты для модуля throttling.
"""

import pytest
import asyncio
import time
from unittest import mock
from api.throttling import RateLimiter, ConcurrencyLimiter, ResourceManager, throttle


class TestRateLimiter:
    """Тесты для класса RateLimiter."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Тест инициализации RateLimiter."""
        limiter = RateLimiter(rate=10.0, burst=20, per_endpoint=True)
        assert limiter.rate == 10.0
        assert limiter.burst == 20
        assert limiter.per_endpoint is True
        assert limiter.tokens == 20
        assert limiter.endpoint_states == {}

    @pytest.mark.asyncio
    async def test_acquire_no_wait(self):
        """Тест метода acquire без ожидания."""
        limiter = RateLimiter(rate=10.0, burst=20)

        # Первый запрос должен быть выполнен немедленно
        wait_time = await limiter.acquire()
        assert wait_time == 0.0
        assert limiter.tokens == 19

    @pytest.mark.asyncio
    async def test_acquire_with_wait(self):
        """Тест метода acquire с ожиданием."""
        limiter = RateLimiter(rate=10.0, burst=1)

        # Первый запрос должен быть выполнен немедленно
        wait_time = await limiter.acquire()
        assert wait_time == 0.0
        assert limiter.tokens == 0

        # Второй запрос должен ждать
        start_time = time.time()
        wait_time = await limiter.acquire()
        elapsed = time.time() - start_time

        # Проверяем, что ожидание было примерно 0.1 секунды (1/10 секунды)
        assert 0.05 <= wait_time <= 0.15
        assert 0.05 <= elapsed <= 0.15

    @pytest.mark.asyncio
    async def test_acquire_per_endpoint(self):
        """Тест метода acquire с разделением по эндпоинтам."""
        limiter = RateLimiter(rate=10.0, burst=1, per_endpoint=True)

        # Первый запрос для endpoint1 должен быть выполнен немедленно
        wait_time = await limiter.acquire("endpoint1")
        assert wait_time == 0.0
        assert limiter.endpoint_states["endpoint1"]["tokens"] == 0

        # Первый запрос для endpoint2 также должен быть выполнен немедленно
        wait_time = await limiter.acquire("endpoint2")
        assert wait_time == 0.0
        assert limiter.endpoint_states["endpoint2"]["tokens"] == 0

        # Второй запрос для endpoint1 должен ждать
        start_time = time.time()
        wait_time = await limiter.acquire("endpoint1")
        elapsed = time.time() - start_time

        # Проверяем, что ожидание было примерно 0.1 секунды (1/10 секунды)
        assert 0.05 <= wait_time <= 0.15
        assert 0.05 <= elapsed <= 0.15

    @pytest.mark.asyncio
    async def test_refill_tokens(self):
        """Тест пополнения токенов."""
        limiter = RateLimiter(rate=10.0, burst=20)

        # Используем все токены
        for _ in range(20):
            await limiter.acquire()

        assert limiter.tokens < 1

        # Ждем пополнения токенов
        await asyncio.sleep(0.2)

        # Проверяем, что токены пополнились
        state = {'tokens': limiter.tokens, 'last_refill_time': limiter.last_refill_time}
        limiter._refill_tokens(state)

        # Должно быть примерно 2 токена (0.2 секунды * 10 токенов/секунду)
        assert 1.5 <= state['tokens'] <= 2.5


class TestConcurrencyLimiter:
    """Тесты для класса ConcurrencyLimiter."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Тест инициализации ConcurrencyLimiter."""
        limiter = ConcurrencyLimiter(max_concurrency=10, per_endpoint=True)
        assert limiter.max_concurrency == 10
        assert limiter.per_endpoint is True
        assert limiter.active_requests == 0
        assert limiter.endpoint_active_requests == {}

    @pytest.mark.asyncio
    async def test_acquire_release(self):
        """Тест методов acquire и release."""
        limiter = ConcurrencyLimiter(max_concurrency=10)

        # Запрашиваем ресурс
        await limiter.acquire()
        assert limiter.active_requests == 1

        # Освобождаем ресурс
        limiter.release()
        assert limiter.active_requests == 0

    @pytest.mark.asyncio
    async def test_acquire_release_per_endpoint(self):
        """Тест методов acquire и release с разделением по эндпоинтам."""
        limiter = ConcurrencyLimiter(max_concurrency=10, per_endpoint=True)

        # Запрашиваем ресурс для endpoint1
        await limiter.acquire("endpoint1")
        assert limiter.active_requests == 1
        assert limiter.endpoint_active_requests["endpoint1"] == 1

        # Запрашиваем ресурс для endpoint2
        await limiter.acquire("endpoint2")
        assert limiter.active_requests == 2
        assert limiter.endpoint_active_requests["endpoint2"] == 1

        # Освобождаем ресурс для endpoint1
        limiter.release("endpoint1")
        assert limiter.active_requests == 1
        assert limiter.endpoint_active_requests["endpoint1"] == 0

        # Освобождаем ресурс для endpoint2
        limiter.release("endpoint2")
        assert limiter.active_requests == 0
        assert limiter.endpoint_active_requests["endpoint2"] == 0

    @pytest.mark.asyncio
    async def test_max_concurrency(self):
        """Тест ограничения количества одновременных запросов."""
        limiter = ConcurrencyLimiter(max_concurrency=2)

        # Запрашиваем ресурсы
        await limiter.acquire()
        await limiter.acquire()

        # Третий запрос должен заблокироваться
        # Создаем задачу для третьего запроса
        task = asyncio.create_task(limiter.acquire())

        # Ждем немного, чтобы задача успела запуститься
        await asyncio.sleep(0.1)

        # Проверяем, что задача не завершилась
        assert not task.done()

        # Освобождаем ресурс
        limiter.release()

        # Ждем немного, чтобы задача успела завершиться
        await asyncio.sleep(0.1)

        # Проверяем, что задача завершилась
        assert task.done()

        # Освобождаем оставшиеся ресурсы
        limiter.release()
        limiter.release()


class TestResourceManager:
    """Тесты для класса ResourceManager."""

    @pytest.mark.asyncio
    async def test_init(self):
        """Тест инициализации ResourceManager."""
        manager = ResourceManager(rate_limit=10.0, burst=20, max_concurrency=10, per_endpoint=True)
        assert manager.rate_limiter.rate == 10.0
        assert manager.rate_limiter.burst == 20
        assert manager.rate_limiter.per_endpoint is True
        assert manager.concurrency_limiter.max_concurrency == 10
        assert manager.concurrency_limiter.per_endpoint is True

    @pytest.mark.asyncio
    async def test_acquire_release(self):
        """Тест методов acquire и release."""
        manager = ResourceManager(rate_limit=10.0, burst=20, max_concurrency=10)

        # Запрашиваем ресурс
        wait_time = await manager.acquire()
        assert wait_time == 0.0
        assert manager.concurrency_limiter.active_requests == 1

        # Освобождаем ресурс
        manager.release()
        assert manager.concurrency_limiter.active_requests == 0

    @pytest.mark.asyncio
    async def test_acquire_release_per_endpoint(self):
        """Тест методов acquire и release с разделением по эндпоинтам."""
        manager = ResourceManager(rate_limit=10.0, burst=20, max_concurrency=10, per_endpoint=True)

        # Запрашиваем ресурс для endpoint1
        wait_time = await manager.acquire("endpoint1")
        assert wait_time == 0.0
        assert manager.concurrency_limiter.active_requests == 1
        assert manager.concurrency_limiter.endpoint_active_requests["endpoint1"] == 1

        # Запрашиваем ресурс для endpoint2
        wait_time = await manager.acquire("endpoint2")
        assert wait_time == 0.0
        assert manager.concurrency_limiter.active_requests == 2
        assert manager.concurrency_limiter.endpoint_active_requests["endpoint2"] == 1

        # Освобождаем ресурс для endpoint1
        manager.release("endpoint1")
        assert manager.concurrency_limiter.active_requests == 1
        assert manager.concurrency_limiter.endpoint_active_requests["endpoint1"] == 0

        # Освобождаем ресурс для endpoint2
        manager.release("endpoint2")
        assert manager.concurrency_limiter.active_requests == 0
        assert manager.concurrency_limiter.endpoint_active_requests["endpoint2"] == 0


class TestThrottleDecorator:
    """Тесты для декоратора throttle."""

    @pytest.mark.asyncio
    async def test_throttle_decorator(self):
        """Тест декоратора throttle."""
        # Создаем менеджер ресурсов
        manager = ResourceManager(rate_limit=10.0, burst=1, max_concurrency=10)

        # Создаем декорированную функцию
        @throttle(resource_manager=manager)
        async def test_func():
            return "success"

        # Первый вызов должен быть выполнен немедленно
        start_time = time.time()
        result = await test_func()
        elapsed = time.time() - start_time

        assert result == "success"
        assert elapsed < 0.1

        # Второй вызов должен быть ограничен по скорости
        start_time = time.time()
        result = await test_func()
        elapsed = time.time() - start_time

        assert result == "success"
        assert 0.05 <= elapsed <= 0.15

    @pytest.mark.asyncio
    async def test_throttle_decorator_with_endpoint(self):
        """Тест декоратора throttle с указанием эндпоинта."""
        # Создаем менеджер ресурсов
        manager = ResourceManager(rate_limit=10.0, burst=1, max_concurrency=10, per_endpoint=True)

        # Создаем декорированные функции
        @throttle(resource_manager=manager, endpoint="endpoint1")
        async def test_func1():
            return "success1"

        @throttle(resource_manager=manager, endpoint="endpoint2")
        async def test_func2():
            return "success2"

        # Первый вызов каждой функции должен быть выполнен немедленно
        result1 = await test_func1()
        result2 = await test_func2()

        assert result1 == "success1"
        assert result2 == "success2"

        # Второй вызов первой функции должен быть ограничен по скорости
        start_time = time.time()
        result1 = await test_func1()
        elapsed = time.time() - start_time

        assert result1 == "success1"
        assert 0.05 <= elapsed <= 0.15

        # Второй вызов второй функции также должен быть ограничен по скорости
        start_time = time.time()
        result2 = await test_func2()
        elapsed = time.time() - start_time

        assert result2 == "success2"
        assert 0.05 <= elapsed <= 0.15

    @pytest.mark.asyncio
    async def test_throttle_decorator_with_exception(self):
        """Тест декоратора throttle при возникновении исключения."""
        # Создаем менеджер ресурсов
        manager = ResourceManager(rate_limit=10.0, burst=1, max_concurrency=10)

        # Создаем декорированную функцию, которая вызывает исключение
        @throttle(resource_manager=manager)
        async def test_func():
            raise ValueError("Test error")

        # Проверяем, что исключение пробрасывается
        with pytest.raises(ValueError, match="Test error"):
            await test_func()

        # Проверяем, что ресурс был освобожден
        assert manager.concurrency_limiter.active_requests == 0
