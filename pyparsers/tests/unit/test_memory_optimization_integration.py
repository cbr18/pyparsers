"""
Integration tests for memory optimization with async parser.
"""

import unittest
import asyncio
import sys
import gc
import time
import psutil
import os
from unittest.mock import patch, MagicMock

# Import the modules we want to test
from api.memory_optimized import AsyncBatchProcessor, MemoryOptimizedList
from api.dongchedi.async_parser import AsyncDongchediParser


class TestMemoryOptimizationIntegration(unittest.TestCase):
    """Test cases for memory optimization integration with async parser."""

    def setUp(self):
        """Set up test environment."""
        self.parser = AsyncDongchediParser()

    def test_memory_usage_tracking(self):
        """Helper function to demonstrate memory usage tracking."""
        # This is just a demonstration of how to track memory usage
        process = psutil.Process(os.getpid())

        # Get initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create a large list to consume memory
        large_list = [i for i in range(1000000)]

        # Get memory usage after creating the list
        after_list_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Delete the list and force garbage collection
        del large_list
        gc.collect()

        # Get memory usage after cleanup
        after_cleanup_memory = process.memory_info().rss / 1024 / 1024  # MB

        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"After list creation: {after_list_memory:.2f} MB")
        print(f"After cleanup: {after_cleanup_memory:.2f} MB")

        # We expect memory usage to increase after creating the list and decrease after cleanup
        self.assertGreater(after_list_memory, initial_memory)
        self.assertLess(after_cleanup_memory, after_list_memory)

    @patch('api.dongchedi.async_parser.http_client')
    def test_process_car_data_memory_optimization(self, mock_http_client):
        """Test that _process_car_data uses memory optimization."""
        async def run_test():
            # Create mock car data
            mock_car_data = []
            for i in range(100):
                mock_car_data.append({
                    'car_id': f'car_{i}',
                    'sku_id': f'sku_{i}',
                    'title': f'Car Title {i}',
                    'car_name': f'Car Name {i}',
                    'car_year': 2020,
                    'car_mileage': f'{i*1000} km',
                    'sh_price': f'{i*1000}',
                    'brand_name': 'TestBrand',
                    'series_name': 'TestSeries'
                })

            # Process the car data
            result = await self.parser._process_car_data(mock_car_data)

            # Check that we got the expected number of results
            self.assertEqual(len(result), 100)

            # Check that the results are correctly processed
            self.assertEqual(result[0].car_id, 'car_0')
            self.assertEqual(result[99].car_id, 'car_99')

            # Check that all cars have the source set to 'dongchedi'
            for car in result:
                self.assertEqual(car.source, 'dongchedi')

        asyncio.run(run_test())

    @patch('api.dongchedi.async_parser.http_client')
    def test_memory_optimized_list_usage(self, mock_http_client):
        """Test that MemoryOptimizedList is used correctly."""
        # Create a MemoryOptimizedList
        opt_list = MemoryOptimizedList()

        # Add items
        for i in range(100):
            opt_list.append(i)

        # Check length
        self.assertEqual(len(opt_list), 100)

        # Check iteration
        self.assertEqual(list(opt_list), list(range(100)))

        # Check indexing
        self.assertEqual(opt_list[0], 0)
        self.assertEqual(opt_list[99], 99)

        # Check pop
        self.assertEqual(opt_list.pop(), 99)
        self.assertEqual(len(opt_list), 99)

        # Check popleft
        self.assertEqual(opt_list.popleft(), 0)
        self.assertEqual(len(opt_list), 98)

        # Check extend
        opt_list.extend([100, 101, 102])
        self.assertEqual(len(opt_list), 101)
        self.assertEqual(opt_list[-1], 102)

        # Check clear
        opt_list.clear()
        self.assertEqual(len(opt_list), 0)

    @patch('api.dongchedi.async_parser.http_client')
    def test_async_batch_processor_usage(self, mock_http_client):
        """Test that AsyncBatchProcessor is used correctly."""
        async def run_test():
            # Create an AsyncBatchProcessor
            processor = AsyncBatchProcessor(batch_size=10, max_concurrency=5)

            # Define a processing function
            async def process_func(item):
                await asyncio.sleep(0.01)
                return item * 2

            # Process items
            items = list(range(50))
            results = []
            async for result in processor.process_items(items, process_func):
                results.append(result)

            # Check results
            self.assertEqual(len(results), 50)
            self.assertEqual(results, [i * 2 for i in range(50)])

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
