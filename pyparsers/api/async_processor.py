"""
Модуль для асинхронной обработки данных.
"""

import asyncio
import json
import re
import gc
import logging
from typing import List, Dict, Any, TypeVar, Callable, Awaitable, Optional, Union, Tuple, AsyncIterator, Iterator

# Импортируем оптимизированные классы для работы с памятью
from .memory_optimized import AsyncBatchProcessor, StreamProcessor, AsyncStreamProcessor, MemoryOptimizedList

# Настройка логирования
logger = logging.getLogger(__name__)

# Типы для аннотаций
T = TypeVar('T')
U = TypeVar('U')
ProcessFunc = Callable[[T], Awaitable[U]]
FilterFunc = Callable[[T], Awaitable[bool]]
MapFunc = Callable[[T], Awaitable[U]]
ReduceFunc = Callable[[U, T], Awaitable[U]]


async def process_batch_concurrent(
    items: List[T],
    process_func: ProcessFunc[T, U],
    batch_size: int = 10,
    max_concurrency: int = 5
) -> List[U]:
    """
    Асинхронно обрабатывает список элементов с ограничением на количество одновременных задач.
    Использует оптимизированный по памяти AsyncBatchProcessor.

    Args:
        items: Список элементов для обработки
        process_func: Асинхронная функция для обработки элемента
        batch_size: Размер пакета для обработки
        max_concurrency: Максимальное количество одновременных задач

    Returns:
        List[U]: Список результатов обработки
    """
    # Используем оптимизированный по памяти AsyncBatchProcessor
    processor = AsyncBatchProcessor(batch_size=batch_size, max_concurrency=max_concurrency)

    # Создаем оптимизированный список для результатов
    results = MemoryOptimizedList()

    # Обрабатываем элементы асинхронно с оптимизацией памяти
    async for result in processor.process_items(items, process_func):
        results.append(result)

    # Освобождаем память
    gc.collect()

    return list(results)


async def process_stream_concurrent(
    items: List[T],
    process_func: ProcessFunc[T, U],
    max_concurrency: int = 5
) -> List[U]:
    """
    Асинхронно обрабатывает поток элементов с ограничением на количество одновременных задач.
    В отличие от process_batch_concurrent, этот метод запускает обработку всех элементов сразу,
    но ограничивает количество одновременно выполняемых задач.
    Использует оптимизированный по памяти AsyncBatchProcessor.

    Args:
        items: Список элементов для обработки
        process_func: Асинхронная функция для обработки элемента
        max_concurrency: Максимальное количество одновременных задач

    Returns:
        List[U]: Список результатов обработки
    """
    # Используем оптимизированный по памяти AsyncBatchProcessor с большим размером пакета
    # для имитации поведения process_stream_concurrent
    processor = AsyncBatchProcessor(
        batch_size=len(items),  # Обрабатываем все элементы как один пакет
        max_concurrency=max_concurrency
    )

    # Создаем оптимизированный список для результатов
    results = MemoryOptimizedList()

    # Обрабатываем элементы асинхронно с оптимизацией памяти
    async for result in processor.process_items(items, process_func):
        results.append(result)

    # Освобождаем память
    gc.collect()

    return list(results)


async def async_filter(
    items: List[T],
    filter_func: FilterFunc[T],
    max_concurrency: int = 5
) -> List[T]:
    """
    Асинхронно фильтрует список элементов с оптимизацией памяти.

    Args:
        items: Список элементов для фильтрации
        filter_func: Асинхронная функция-предикат для фильтрации
        max_concurrency: Максимальное количество одновременных задач

    Returns:
        List[T]: Отфильтрованный список элементов
    """
    # Используем оптимизированный по памяти AsyncStreamProcessor
    processor = AsyncStreamProcessor(chunk_size=100, max_concurrency=max_concurrency)

    # Создаем оптимизированный список для результатов
    results = MemoryOptimizedList()

    # Фильтруем элементы асинхронно с оптимизацией памяти
    async for result in await processor.filter(items, filter_func):
        results.append(result)

    # Освобождаем память
    gc.collect()

    return list(results)


async def async_map(
    items: List[T],
    map_func: MapFunc[T, U],
    max_concurrency: int = 5
) -> List[U]:
    """
    Асинхронно отображает список элементов с оптимизацией памяти.

    Args:
        items: Список элементов для отображения
        map_func: Асинхронная функция для отображения
        max_concurrency: Максимальное количество одновременных задач

    Returns:
        List[U]: Список результатов отображения
    """
    # Используем оптимизированный по памяти AsyncStreamProcessor
    processor = AsyncStreamProcessor(chunk_size=100, max_concurrency=max_concurrency)

    # Создаем оптимизированный список для результатов
    results = MemoryOptimizedList()

    # Отображаем элементы асинхронно с оптимизацией памяти
    async for result in await processor.map(items, map_func):
        results.append(result)

    # Освобождаем память
    gc.collect()

    return list(results)


async def async_reduce(
    items: List[T],
    reduce_func: ReduceFunc[U, T],
    initial_value: U
) -> U:
    """
    Асинхронно сворачивает список элементов с оптимизацией памяти.

    Args:
        items: Список элементов для свертки
        reduce_func: Асинхронная функция для свертки
        initial_value: Начальное значение

    Returns:
        U: Результат свертки
    """
    # Используем оптимизированный по памяти AsyncStreamProcessor
    processor = AsyncStreamProcessor(chunk_size=100)

    # Выполняем свертку с оптимизацией памяти
    result = await processor.reduce(items, reduce_func, initial_value)

    # Освобождаем память
    gc.collect()

    return result


async def process_json_data(
    data: Dict[str, Any],
    path: str,
    default: Any = None
) -> Any:
    """
    Асинхронно извлекает данные из JSON по указанному пути.

    Args:
        data: JSON-данные
        path: Путь к данным в формате "key1.key2[0].key3"
        default: Значение по умолчанию

    Returns:
        Any: Извлеченные данные или значение по умолчанию
    """
    # Разбиваем путь на части
    parts = re.findall(r'(\w+)(?:\[(\d+)\])?', path)

    # Извлекаем данные
    current = data
    for key, index in parts:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

        if index:
            index = int(index)
            if isinstance(current, list) and 0 <= index < len(current):
                current = current[index]
            else:
                return default

    return current


async def extract_fields(
    data: Dict[str, Any],
    field_mappings: Dict[str, Union[str, Tuple[str, Any]]],
    transform_funcs: Optional[Dict[str, Callable[[Any], Any]]] = None
) -> Dict[str, Any]:
    """
    Асинхронно извлекает поля из JSON-данных по указанным путям.

    Args:
        data: JSON-данные
        field_mappings: Словарь соответствия полей и путей
            Ключи - имена полей в результате
            Значения - пути к данным или кортежи (путь, значение по умолчанию)
        transform_funcs: Словарь функций преобразования для полей
            Ключи - имена полей
            Значения - функции преобразования

    Returns:
        Dict[str, Any]: Словарь с извлеченными полями
    """
    result = {}
    transform_funcs = transform_funcs or {}

    for field, mapping in field_mappings.items():
        # Определяем путь и значение по умолчанию
        if isinstance(mapping, tuple):
            path, default = mapping
        else:
            path, default = mapping, None

        # Извлекаем значение
        value = await process_json_data(data, path, default)

        # Применяем функцию преобразования, если она указана
        if field in transform_funcs and value is not None:
            value = transform_funcs[field](value)

        result[field] = value

    return result
