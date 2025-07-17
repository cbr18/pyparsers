"""
Тесты производительности для асинхронного HTTP-клиента.
"""

import pytest
import asyncio
import time
import aiohttp
import requests
import psutil
import os
from api.http_client import HTTPClient


class TestHTTPClientBenchmark:
    """Тесты производительности для асинхронного HTTP-клиента."""

    @pytest.fixture
    def http_client(self):
        """Фикстура для создания экземпляра HTTPClient."""
        client = HTTPClient(
            timeout=5.0,
            max_retries=1,
            retry_delay=0.1,
            pool_size=100
        )
        yield client
        # Закрываем сессию после теста
        loop = asyncio.get_event_loop()
        if client._session and not client._session.closed:
            loop.run_until_complete(client.close())

    def test_sync_vs_async_get(self, http_client, benchmark):
        """
        Сравнение производительности синхронных и асинхронных GET-запросов.

        Этот тест сравнивает время выполнения синхронных и асинхронных GET-запросов.
        """
        url = "https://httpbin.org/get"

        # Тест синхронного запроса
        def sync_request():
            try:
                response = http_client.sync_get(url)
                return response.status_code
            except Exception:
                return None

        # Запускаем бенчмарк для синхронного запроса
        sync_result = benchmark(sync_request)

        # Проверяем, что запрос выполнился успешно
        if sync_result is not None:
            assert sync_result == 200
        else:
            pytest.skip("Sync HTTP request failed, skipping benchmark")

        # Тест асинхронного запроса
        async def async_request():
            try:
                status, _, _ = await http_client.get(url)
                return status
            except Exception:
                return None

        # Запускаем бенчмарк для асинхронного запроса
        loop = asyncio.get_event_loop()
        async_result = benchmark(lambda: loop.run_until_complete(async_request()))

        # Проверяем, что запрос выполнился успешно
        if async_result is not None:
            assert async_result == 200
        else:
            pytest.skip("Async HTTP request failed, skipping benchmark")

    def test_concurrent_requests(self, http_client):
        """
        Тест производительности конкурентных запросов.

        Этот тест измеряет время выполнения нескольких конкурентных запросов.
        """
        url = "https://httpbin.org/get"
        num_requests = 10

        # Функция для выполнения асинхронных запросов
        async def run_concurrent_requests():
            tasks = [http_client.get(url) for _ in range(num_requests)]
            results = await asyncio.gather(*tasks)
            return results

        # Измеряем время выполнения асинхронных запросов
        loop = asyncio.get_event_loop()
        start_time = time.time()
        results = loop.run_until_complete(run_concurrent_requests())
        async_time = time.time() - start_time

        # Проверяем результаты
        success_count = sum(1 for status, _, _ in results if status == 200)
        print(f"\nAsync: {num_requests} concurrent requests took {async_time:.2f} seconds")
        print(f"Async: Average time per request: {async_time / num_requests:.2f} seconds")
        print(f"Async: Success rate: {success_count / num_requests * 100:.2f}%")

        # Функция для выполнения синхронных запросов
        def run_sequential_requests():
            results = []
            for _ in range(num_requests):
                try:
                    response = http_client.sync_get(url)
                    results.append(response.status_code)
                except Exception:
                    results.append(None)
            return results

        # Измеряем время выполнения синхронных запросов
        start_time = time.time()
        sync_results = run_sequential_requests()
        sync_time = time.time() - start_time

        # Проверяем результаты
        sync_success_count = sum(1 for status in sync_results if status == 200)
        print(f"Sync: {num_requests} sequential requests took {sync_time:.2f} seconds")
        print(f"Sync: Average time per request: {sync_time / num_requests:.2f} seconds")
        print(f"Sync: Success rate: {sync_success_count / num_requests * 100:.2f}%")

        # Сравниваем производительность
        speedup = sync_time / async_time
        print(f"Speedup: {speedup:.2f}x")

        # Проверяем, что асинхронные запросы быстрее синхронных
        assert speedup > 1.0, f"Async requests should be faster than sync requests, but speedup is {speedup:.2f}x"

    def test_memory_usage(self, http_client):
        """
        Тест использования памяти при выполнении запросов.

        Этот тест измеряет объем памяти, используемой при выполнении
        синхронных и асинхронных запросов.
        """
        url = "https://httpbin.org/get"
        num_requests = 10

        # Получаем процесс
        process = psutil.Process(os.getpid())

        # Измеряем использование памяти до запросов
        memory_before = process.memory_info().rss

        # Функция для выполнения асинхронных запросов
        async def run_concurrent_requests():
            tasks = [http_client.get(url) for _ in range(num_requests)]
            results = await asyncio.gather(*tasks)
            return results

        # Выполняем асинхронные запросы
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_concurrent_requests())

        # Измеряем использование памяти после асинхронных запросов
        memory_after_async = process.memory_info().rss
        memory_used_async = memory_after_async - memory_before

        # Выводим результаты
        print(f"\nMemory before: {memory_before / 1024 / 1024:.2f} MB")
        print(f"Memory after async requests: {memory_after_async / 1024 / 1024:.2f} MB")
        print(f"Memory used by async requests: {memory_used_async / 1024 / 1024:.2f} MB")

        # Выполняем синхронные запросы
        for _ in range(num_requests):
            try:
                http_client.sync_get(url)
            except Exception:
                pass

        # Измеряем использование памяти после синхронных запросов
        memory_after_sync = process.memory_info().rss
        memory_used_sync = memory_after_sync - memory_after_async

        # Выводим результаты
        print(f"Memory after sync requests: {memory_after_sync / 1024 / 1024:.2f} MB")
        print(f"Memory used by sync requests: {memory_used_sync / 1024 / 1024:.2f} MB")

        # Сравниваем использование памяти
        print(f"Memory efficiency: {memory_used_sync / memory_used_async:.2f}x")

    def test_connection_pooling(self, http_client):
        """
        Тест влияния размера пула соединений на производительность.

        Этот тест измеряет время выполнения запросов с разными размерами пула соединений.
        """
        url = "https://httpbin.org/get"
        num_requests = 20

        # Тестируем разные размеры пула соединений
        pool_sizes = [1, 5, 10, 20, 50]

        for pool_size in pool_sizes:
            # Создаем клиент с указанным размером пула
            client = HTTPClient(
                timeout=5.0,
                max_retries=1,
                retry_delay=0.1,
                pool_size=pool_size
            )

            # Функция для выполнения асинхронных запросов
            async def run_concurrent_requests():
                tasks = [client.get(url) for _ in range(num_requests)]
                results = await asyncio.gather(*tasks)
                return results

            # Измеряем время выполнения асинхронных запросов
            loop = asyncio.get_event_loop()
            start_time = time.time()
            try:
                results = loop.run_until_complete(run_concurrent_requests())
                async_time = time.time() - start_time

                # Проверяем результаты
                success_count = sum(1 for status, _, _ in results if status == 200)
                print(f"\nPool size {pool_size}: {num_requests} concurrent requests took {async_time:.2f} seconds")
                print(f"Pool size {pool_size}: Average time per request: {async_time / num_requests:.2f} seconds")
                print(f"Pool size {pool_size}: Success rate: {success_count / num_requests * 100:.2f}%")
            except Exception as e:
                print(f"\nPool size {pool_size}: Error - {str(e)}")
            finally:
                # Закрываем сессию
                if client._session and not client._session.closed:
                    loop.run_until_complete(client.close())
