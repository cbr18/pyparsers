"""
Юнит-тесты для модуля асинхронной обработки данных.
"""

import pytest
import asyncio
from unittest import mock
from api.async_processor import (
    process_batch_concurrent,
    process_stream_concurrent,
    async_filter,
    async_map,
    async_reduce,
    process_json_data,
    extract_fields
)


class TestAsyncProcessor:
    """Тесты для модуля асинхронной обработки данных."""

    @pytest.mark.asyncio
    async def test_process_batch_concurrent(self):
        """Тест функции process_batch_concurrent."""
        # Создаем тестовые данные
        items = list(range(10))

        # Создаем асинхронную функцию для обработки элемента
        async def process_func(item):
            await asyncio.sleep(0.01)
            return item * 2

        # Вызываем функцию
        results = await process_batch_concurrent(items, process_func, batch_size=3, max_concurrency=2)

        # Проверяем результат
        assert len(results) == 10
        assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

    @pytest.mark.asyncio
    async def test_process_batch_concurrent_with_exception(self):
        """Тест функции process_batch_concurrent с исключением."""
        # Создаем тестовые данные
        items = list(range(10))

        # Создаем асинхронную функцию для обработки элемента с исключением
        async def process_func(item):
            await asyncio.sleep(0.01)
            if item == 5:
                raise ValueError("Test exception")
            return item * 2

        # Вызываем функцию
        results = await process_batch_concurrent(items, process_func, batch_size=3, max_concurrency=2)

        # Проверяем результат
        assert len(results) == 9
        assert 10 not in results  # Элемент 5 * 2 = 10 должен отсутствовать

    @pytest.mark.asyncio
    async def test_process_stream_concurrent(self):
        """Тест функции process_stream_concurrent."""
        # Создаем тестовые данные
        items = list(range(10))

        # Создаем асинхронную функцию для обработки элемента
        async def process_func(item):
            await asyncio.sleep(0.01)
            return item * 2

        # Вызываем функцию
        results = await process_stream_concurrent(items, process_func, max_concurrency=3)

        # Проверяем результат
        assert len(results) == 10
        assert sorted(results) == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

    @pytest.mark.asyncio
    async def test_async_filter(self):
        """Тест функции async_filter."""
        # Создаем тестовые данные
        items = list(range(10))

        # Создаем асинхронную функцию-предикат
        async def filter_func(item):
            await asyncio.sleep(0.01)
            return item % 2 == 0

        # Вызываем функцию
        results = await async_filter(items, filter_func)

        # Проверяем результат
        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_async_map(self):
        """Тест функции async_map."""
        # Создаем тестовые данные
        items = list(range(5))

        # Создаем асинхронную функцию для отображения
        async def map_func(item):
            await asyncio.sleep(0.01)
            return item * 2

        # Вызываем функцию
        results = await async_map(items, map_func, max_concurrency=2)

        # Проверяем результат
        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_async_reduce(self):
        """Тест функции async_reduce."""
        # Создаем тестовые данные
        items = list(range(1, 6))  # [1, 2, 3, 4, 5]

        # Создаем асинхронную функцию для свертки
        async def reduce_func(acc, item):
            await asyncio.sleep(0.01)
            return acc + item

        # Вызываем функцию
        result = await async_reduce(items, reduce_func, 0)

        # Проверяем результат
        assert result == 15  # 0 + 1 + 2 + 3 + 4 + 5 = 15

    @pytest.mark.asyncio
    async def test_process_json_data(self):
        """Тест функции process_json_data."""
        # Создаем тестовые данные
        data = {
            "user": {
                "name": "John",
                "age": 30,
                "address": {
                    "city": "New York",
                    "zip": "10001"
                },
                "phones": [
                    {"type": "home", "number": "123-456-7890"},
                    {"type": "work", "number": "098-765-4321"}
                ]
            }
        }

        # Тест простого пути
        result = await process_json_data(data, "user.name")
        assert result == "John"

        # Тест пути с индексом
        result = await process_json_data(data, "user.phones[0].number")
        assert result == "123-456-7890"

        # Тест несуществующего пути
        result = await process_json_data(data, "user.email", "default@example.com")
        assert result == "default@example.com"

        # Тест несуществующего индекса
        result = await process_json_data(data, "user.phones[2].number", "N/A")
        assert result == "N/A"

    @pytest.mark.asyncio
    async def test_extract_fields(self):
        """Тест функции extract_fields."""
        # Создаем тестовые данные
        data = {
            "user": {
                "name": "John",
                "age": 30,
                "address": {
                    "city": "New York",
                    "zip": "10001"
                },
                "phones": [
                    {"type": "home", "number": "123-456-7890"},
                    {"type": "work", "number": "098-765-4321"}
                ]
            }
        }

        # Создаем отображение полей
        field_mappings = {
            "name": "user.name",
            "age": "user.age",
            "city": "user.address.city",
            "home_phone": ("user.phones[0].number", "N/A"),
            "work_phone": ("user.phones[1].number", "N/A"),
            "email": ("user.email", "default@example.com")
        }

        # Создаем функции преобразования
        transform_funcs = {
            "age": lambda x: x + 1,
            "name": lambda x: x.upper()
        }

        # Вызываем функцию
        result = await extract_fields(data, field_mappings, transform_funcs)

        # Проверяем результат
        assert result["name"] == "JOHN"
        assert result["age"] == 31
        assert result["city"] == "New York"
        assert result["home_phone"] == "123-456-7890"
        assert result["work_phone"] == "098-765-4321"
        assert result["email"] == "default@example.com"
