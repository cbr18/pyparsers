"""
Unit tests for memory optimization module.
"""

import asyncio
import unittest
import time
import sys
import gc
from unittest.mock import patch, MagicMock

from api.memory_optimized import (
    AsyncBatchProcessor,
    StreamProcessor,
    AsyncStreamProcessor,
    MemoryOptimizedList
)


class TestAsyncBatchProcessor(unittest.TestCase):
    """Test cases for AsyncBatchProcessor."""

    def setUp(self):
        """Set up test environment."""
        self.processor = AsyncBatchProcessor(batch_size=10, max_concurrency=5)

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.processor.batch_size, 10)
        self.assertEqual(self.processor.max_concurrency, 5)
        self.assertEqual(self.processor.buffer_size, 1000)

    def test_process_items_list(self):
        """Test processing a list of items."""
        async def run_test():
            async def process_func(item):
                await asyncio.sleep(0.01)
                return item * 2

            items = list(range(25))
            results = []
            async for result in self.processor.process_items(items, process_func):
                results.append(result)

            self.assertEqual(len(results), 25)
            self.assertEqual(results, [i * 2 for i in range(25)])

        asyncio.run(run_test())

    def test_process_items_iterator(self):
        """Test processing an iterator."""
        async def run_test():
            async def process_func(item):
                await asyncio.sleep(0.01)
                return item * 2

            items = iter(range(25))
            results = []
            async for result in self.processor.process_items(items, process_func):
                results.append(result)

            self.assertEqual(len(results), 25)
            self.assertEqual(results, [i * 2 for i in range(25)])

        asyncio.run(run_test())

    def test_process_items_async_iterator(self):
        """Test processing an async iterator."""
        async def run_test():
            async def process_func(item):
                await asyncio.sleep(0.01)
                return item * 2

            async def async_iter():
                for i in range(25):
                    yield i

            results = []
            async for result in self.processor.process_items(async_iter(), process_func):
                results.append(result)

            self.assertEqual(len(results), 25)
            self.assertEqual(results, [i * 2 for i in range(25)])

        asyncio.run(run_test())

    def test_process_items_with_error(self):
        """Test processing items with errors."""
        async def run_test():
            async def process_func(item):
                await asyncio.sleep(0.01)
                if item % 5 == 0:
                    raise ValueError(f"Error processing {item}")
                return item * 2

            items = list(range(25))
            results = []

            # We should get results for all non-error items
            with self.assertLogs(level='ERROR') as cm:
                async for result in self.processor.process_items(items, process_func):
                    results.append(result)

            # Check that we got the expected number of results (excluding errors)
            self.assertEqual(len(results), 20)  # 25 - 5 errors

            # Check that errors were logged
            self.assertEqual(len(cm.records), 5)
            for record in cm.records:
                self.assertIn("Error processing item", record.getMessage())

        asyncio.run(run_test())


class TestStreamProcessor(unittest.TestCase):
    """Test cases for StreamProcessor."""

    def setUp(self):
        """Set up test environment."""
        self.processor = StreamProcessor(chunk_size=10)

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.processor.chunk_size, 10)

    def test_map(self):
        """Test mapping function."""
        items = range(25)
        results = list(self.processor.map(items, lambda x: x * 2))
        self.assertEqual(len(results), 25)
        self.assertEqual(results, [i * 2 for i in range(25)])

    def test_filter(self):
        """Test filtering function."""
        items = range(25)
        results = list(self.processor.filter(items, lambda x: x % 2 == 0))
        self.assertEqual(len(results), 13)  # 0, 2, 4, ..., 24
        self.assertEqual(results, [i for i in range(25) if i % 2 == 0])

    def test_reduce(self):
        """Test reducing function."""
        items = range(25)
        result = self.processor.reduce(items, lambda acc, x: acc + x, 0)
        self.assertEqual(result, sum(range(25)))


class TestAsyncStreamProcessor(unittest.TestCase):
    """Test cases for AsyncStreamProcessor."""

    def setUp(self):
        """Set up test environment."""
        self.processor = AsyncStreamProcessor(chunk_size=10, max_concurrency=5)

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.processor.chunk_size, 10)
        self.assertEqual(self.processor.max_concurrency, 5)

    def test_map(self):
        """Test async mapping function."""
        async def run_test():
            async def process_func(item):
                await asyncio.sleep(0.01)
                return item * 2

            items = range(25)
            results = []
            async for result in await self.processor.map(items, process_func):
                results.append(result)

            self.assertEqual(len(results), 25)
            self.assertEqual(results, [i * 2 for i in range(25)])

        asyncio.run(run_test())

    def test_filter(self):
        """Test async filtering function."""
        async def run_test():
            async def predicate(item):
                await asyncio.sleep(0.01)
                return item % 2 == 0

            items = range(25)
            results = []
            async for result in await self.processor.filter(items, predicate):
                results.append(result)

            self.assertEqual(len(results), 13)  # 0, 2, 4, ..., 24
            self.assertEqual(results, [i for i in range(25) if i % 2 == 0])

        asyncio.run(run_test())

    def test_reduce(self):
        """Test async reducing function."""
        async def run_test():
            async def reducer(acc, item):
                await asyncio.sleep(0.01)
                return acc + item

            items = range(25)
            result = await self.processor.reduce(items, reducer, 0)
            self.assertEqual(result, sum(range(25)))

        asyncio.run(run_test())


class TestMemoryOptimizedList(unittest.TestCase):
    """Test cases for MemoryOptimizedList."""

    def test_init_empty(self):
        """Test initialization with empty list."""
        lst = MemoryOptimizedList()
        self.assertEqual(len(lst), 0)

    def test_init_with_items(self):
        """Test initialization with items."""
        items = [1, 2, 3, 4, 5]
        lst = MemoryOptimizedList(items)
        self.assertEqual(len(lst), 5)
        self.assertEqual(list(lst), items)

    def test_append(self):
        """Test append method."""
        lst = MemoryOptimizedList()
        lst.append(1)
        lst.append(2)
        self.assertEqual(len(lst), 2)
        self.assertEqual(list(lst), [1, 2])

    def test_appendleft(self):
        """Test appendleft method."""
        lst = MemoryOptimizedList()
        lst.appendleft(1)
        lst.appendleft(2)
        self.assertEqual(len(lst), 2)
        self.assertEqual(list(lst), [2, 1])

    def test_extend(self):
        """Test extend method."""
        lst = MemoryOptimizedList([1, 2])
        lst.extend([3, 4, 5])
        self.assertEqual(len(lst), 5)
        self.assertEqual(list(lst), [1, 2, 3, 4, 5])

    def test_pop(self):
        """Test pop method."""
        lst = MemoryOptimizedList([1, 2, 3])
        item = lst.pop()
        self.assertEqual(item, 3)
        self.assertEqual(len(lst), 2)
        self.assertEqual(list(lst), [1, 2])

    def test_popleft(self):
        """Test popleft method."""
        lst = MemoryOptimizedList([1, 2, 3])
        item = lst.popleft()
        self.assertEqual(item, 1)
        self.assertEqual(len(lst), 2)
        self.assertEqual(list(lst), [2, 3])

    def test_clear(self):
        """Test clear method."""
        lst = MemoryOptimizedList([1, 2, 3])
        lst.clear()
        self.assertEqual(len(lst), 0)
        self.assertEqual(list(lst), [])

    def test_getitem(self):
        """Test __getitem__ method."""
        lst = MemoryOptimizedList([1, 2, 3])
        self.assertEqual(lst[0], 1)
        self.assertEqual(lst[1], 2)
        self.assertEqual(lst[2], 3)

    def test_add_unique(self):
        """Test add_unique method."""
        lst = MemoryOptimizedList()

        # Add unique items
        self.assertTrue(lst.add_unique(1, lambda x: x))
        self.assertTrue(lst.add_unique(2, lambda x: x))
        self.assertTrue(lst.add_unique(3, lambda x: x))

        # Try to add duplicate items
        self.assertFalse(lst.add_unique(1, lambda x: x))
        self.assertFalse(lst.add_unique(2, lambda x: x))

        # Check final list
        self.assertEqual(len(lst), 3)
        self.assertEqual(list(lst), [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
