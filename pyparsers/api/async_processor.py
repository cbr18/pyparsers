"""
Модуль с асинхронными процессорами для обработки данных.
"""

import asyncio
import logging
from typing import Dict, Any, List, Callable, Tuple, Optional, TypeVar, AsyncIterator

T = TypeVar('T')
U = TypeVar('U')

async def process_stream_concurrent(items: List[T], processor_func: Callable[[T], U], max_concurrency: int = 5) -> AsyncIterator[U]:
    """
    Асинхронно обрабатывает элементы с ограничением на количество одновременных задач.

    Args:
        items: Список элементов для обработки
        processor_func: Асинхронная функция для обработки элементов
        max_concurrency: Максимальное количество одновременных задач

    Yields:
        Результаты обработки элементов
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def process_with_semaphore(item: T) -> U:
        async with semaphore:
            return await processor_func(item)

    # Создаем задачи для всех элементов
    tasks = [process_with_semaphore(item) for item in items]

    # Обрабатываем задачи по мере их завершения
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            yield result
        except Exception as e:
            logging.getLogger(__name__).error(f"Error processing item: {str(e)}")
            yield None

async def extract_fields(data: Dict[str, Any], field_mappings: Dict[str, Tuple[Optional[str], Any]],
                        transform_funcs: Dict[str, Callable[[Any], Any]] = None) -> Dict[str, Any]:
    """
    Асинхронно извлекает поля из данных с применением трансформаций.

    Args:
        data: Исходные данные
        field_mappings: Отображение полей (ключ -> (исходное_поле, значение_по_умолчанию))
        transform_funcs: Функции преобразования для полей (ключ -> функция)

    Returns:
        Словарь с извлеченными полями
    """
    result = {}
    transform_funcs = transform_funcs or {}

    for target_field, (source_field, default_value) in field_mappings.items():
        # Если исходное поле указано, извлекаем значение из данных
        if source_field:
            value = data.get(source_field, default_value)
        else:
            # Иначе используем значение по умолчанию
            value = default_value

        # Применяем функцию преобразования, если она указана
        if target_field in transform_funcs and value is not None:
            try:
                value = transform_funcs[target_field](value)
            except Exception as e:
                logging.getLogger(__name__).error(f"Error transforming field {target_field}: {str(e)}")

        # Добавляем поле в результат
        result[target_field] = value

    return result
