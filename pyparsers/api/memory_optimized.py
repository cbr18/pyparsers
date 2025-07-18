"""
Модуль с оптимизированными по памяти структурами данных и процессорами.
"""

import asyncio
import gc
from typing import List, Dict, Any, Optional, Callable, AsyncIterator, TypeVar, Generic, Iterable

T = TypeVar('T')
U = TypeVar('U')

class MemoryOptimizedList(List[T]):
    """
    Список, оптимизированный по памяти.
    Автоматически освобождает память при достижении определенного размера.
    """

    def __init__(self, iterable: Iterable[T] = None):
        super().__init__(iterable or [])
        self._gc_threshold = 1000  # Порог для вызова сборщика мусора

    def append(self, item: T) -> None:
        """
        Добавляет элемент в список и при необходимости освобождает память.
        """
        super().append(item)
        if len(self) % self._gc_threshold == 0:
            gc.collect()

    def extend(self, iterable: Iterable[T]) -> None:
        """
        Расширяет список элементами из iterable и при необходимости освобождает память.
        """
        super().extend(iterable)
        if len(self) % self._gc_threshold == 0:
            gc.collect()


class AsyncBatchProcessor(Generic[T, U]):
    """
    Асинхронный процессор для обработки элементов пакетами.
    Оптимизирован по памяти и производительности.
    """

    def __init__(self, batch_size: int = 10, max_concurrency: int = 5):
        """
        Инициализирует процессор с указанным размером пакета и максимальным количеством одновременных задач.

        Args:
            batch_size: Размер пакета для обработки
            max_concurrency: Максимальное количество одновременных задач
        """
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def process_items(self, items: List[T], processor_func: Callable[[T], U]) -> AsyncIterator[U]:
        """
        Асинхронно обрабатывает элементы с помощью указанной функции.

        Args:
            items: Список элементов для обработки
            processor_func: Асинхронная функция для обработки элементов

        Yields:
            Результаты обработки элементов
        """
        # Разбиваем элементы на пакеты
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]

            # Обрабатываем пакет элементов
            async with self.semaphore:
                tasks = [self._process_item(item, processor_func) for item in batch]
                results = await asyncio.gather(*tasks)

                # Освобождаем память после обработки пакета
                del batch
                gc.collect()

                # Возвращаем результаты
                for result in results:
                    yield result

    async def _process_item(self, item: T, processor_func: Callable[[T], U]) -> U:
        """
        Обрабатывает один элемент с помощью указанной функции.

        Args:
            item: Элемент для обработки
            processor_func: Асинхронная функция для обработки элемента

        Returns:
            Результат обработки элемента
        """
        try:
            return await processor_func(item)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error processing item: {str(e)}")
            return None
