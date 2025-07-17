"""
Асинхронный парсер для сайта Dongchedi.
"""

import asyncio
import json
import re
import uuid
import datetime
import logging
from typing import Optional, Tuple, Dict, Any, List, Union

from .models.response import DongchediApiResponse, DongchediData
from .models.car import DongchediCar
from ..base_parser import BaseCarParser
from ..http_client import http_client
from ..retry import async_retry, default_retry_strategy, default_circuit_breaker
from .async_browser import fetch_car_detail_async, fetch_multiple_car_details


class AsyncDongchediParser(BaseCarParser):
    """Асинхронный парсер для сайта Dongchedi"""

    def __init__(self):
        self.base_url = "https://www.dongchedi.com/motor/pc/sh/sh_sku_list"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.dongchedi.com",
            "Referer": "https://www.dongchedi.com/",
            "Connection": "keep-alive"
        }

    def _build_url(self, page: int = 1) -> str:
        """Строит URL с параметрами запроса"""
        params = {
            "aid": "1839",  # Важный параметр для API
            "page": str(page),
            "limit": "80",
            "sort_type": "4"
        }

        # Строим URL с параметрами
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        # Проверяем, содержит ли базовый URL уже параметры
        if "?" in self.base_url:
            return f"{self.base_url}&{param_string}"
        else:
            return f"{self.base_url}?{param_string}"

    def fetch_cars(self, source: Optional[str] = None) -> DongchediApiResponse:
        """
        Выполняет запрос к API dongchedi и возвращает распарсенный DongchediApiResponse.
        По умолчанию загружает первую страницу.

        Этот метод сохранен для обратной совместимости и использует синхронный HTTP-клиент.

        Args:
            source: Игнорируется для этого парсера, так как используется API

        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        return self.fetch_cars_by_page(1)

    def fetch_cars_by_page(self, page: int) -> DongchediApiResponse:
        """
        Выполняет запрос к API dongchedi для конкретной страницы.

        Этот метод сохранен для обратной совместимости и использует синхронный HTTP-клиент.

        Args:
            page: Номер страницы (начиная с 1)

        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        # Используем синхронный метод для обратной совместимости
        loop = asyncio.get_event_loop()
        try:
            return loop.run_until_complete(self.async_fetch_cars_by_page(page))
        except Exception as e:
            return DongchediApiResponse(
                data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                message=f"Ошибка при получении данных: {str(e)}",
                status=500
            )

    def fetch_car_detail(self, car_id: str) -> Tuple[Optional[DongchediCar], Dict[str, Any]]:
        """
        Парсит детальную информацию о машине по car_id.

        Этот метод сохранен для обратной совместимости и использует асинхронную версию.

        Args:
            car_id: ID машины

        Returns:
            Tuple[Optional[DongchediCar], Dict[str, Any]]: Объект DongchediCar и метаданные
        """
        loop = asyncio.get_event_loop()
        try:
            return loop.run_until_complete(self.async_fetch_car_detail(car_id))
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching car detail: {str(e)}")
            return None, {"is_available": False, "error": str(e), "status": 500}

    @async_retry(retry_strategy=default_retry_strategy, circuit_breaker=default_circuit_breaker, endpoint="dongchedi_api")
    async def async_fetch_cars_by_page(self, page: int) -> DongchediApiResponse:
        """
        Асинхронно выполняет запрос к API dongchedi для конкретной страницы.

        Args:
            page: Номер страницы (начиная с 1)

        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        try:
            url = self._build_url(page)

            # Попробуем использовать POST, затем GET, если POST не работает
            try:
                status, data, text = await http_client.post(url, headers=self.headers)
                if status != 200:
                    status, data, text = await http_client.get(url, headers=self.headers)
            except Exception:
                status, data, text = await http_client.get(url, headers=self.headers)

            if status != 200:
                return DongchediApiResponse(
                    data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                    message=f"Ошибка HTTP: {status}",
                    status=status
                )

            # Если data пустой, пробуем распарсить JSON из text
            if not data and text:
                try:
                    # Иногда API может возвращать некорректный JSON с экранированными кавычками
                    fixed_text = text.replace('\\"', '"').replace('\\\\', '\\')
                    data = json.loads(fixed_text)
                except:
                    # Если все еще не работает, пробуем другой подход
                    try:
                        # Находим начало и конец JSON объекта
                        match = re.search(r'(\{.*\})', text, re.DOTALL)
                        if match:
                            data = json.loads(match.group(1))
                        else:
                            raise Exception("Could not find JSON object in response")
                    except Exception as e:
                        raise Exception(f"Failed to parse JSON: {str(e)}")

            # Преобразуем данные в наши модели
            cars = []
            if 'data' in data and 'search_sh_sku_info_list' in data['data']:
                cars = await self._process_car_data(data['data']['search_sh_sku_info_list'])

            # Если данных нет или список пуст, считаем что страницы не существует
            if not cars:
                return DongchediApiResponse(
                    data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                    message=f"Страница {page} не найдена или данные не соответствуют ожидаемому формату",
                    status=404
                )

            dongchedi_data = DongchediData(
                has_more=data.get('data', {}).get('has_more', False),
                search_sh_sku_info_list=cars,
                total=data.get('data', {}).get('total', 0)
            )

            return DongchediApiResponse(
                data=dongchedi_data,
                message=data.get('message', 'Success'),
                status=data.get('status', 200)
            )

        except Exception as e:
            return DongchediApiResponse(
                data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                message=f"Ошибка при получении данных: {str(e)}",
                status=500
            )

    async def _process_car_data(self, car_data_list: List[Dict[str, Any]]) -> List[DongchediCar]:
        """
        Асинхронно обрабатывает данные о машинах с оптимизацией памяти.

        Args:
            car_data_list: Список данных о машинах

        Returns:
            List[DongchediCar]: Список объектов DongchediCar
        """
        from ..async_processor import process_stream_concurrent
        from ..memory_optimized import AsyncBatchProcessor, MemoryOptimizedList
        import gc

        # Используем оптимизированный по памяти AsyncBatchProcessor
        processor = AsyncBatchProcessor(batch_size=20, max_concurrency=10)

        # Создаем оптимизированный список для результатов
        results = MemoryOptimizedList()

        # Обрабатываем данные о машинах асинхронно с оптимизацией памяти
        async for car in processor.process_items(car_data_list, self._process_single_car):
            if car is not None:
                results.append(car)

        # Освобождаем память
        gc.collect()

        return list(results)

    async def _process_single_car(self, car_data: Dict[str, Any]) -> Optional[DongchediCar]:
        """
        Асинхронно обрабатывает данные одной машины.

        Args:
            car_data: Данные о машине

        Returns:
            Optional[DongchediCar]: Объект DongchediCar или None в случае ошибки
        """
        try:
            from ..async_processor import extract_fields
            from converters import decode_dongchedi_list_sh_price, decode_dongchedi_detail

            # Генерируем UUID для машины
            car_uuid = str(uuid.uuid4())

            # Текущее время в формате RFC3339, совместимом с Go
            current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Определяем отображение полей
            field_mappings = {
                # Основные поля
                "car_id": ("car_id", None),
                "sku_id": ("sku_id", None),
                "title": ("title", None),
                "car_name": ("car_name", None),
                "car_year": ("car_year", None),
                "car_mileage": ("car_mileage", None),
                "sh_price": ("sh_price", None),
                "official_price": ("official_price", None),
                "image": ("image", None),
                "link": ("link", None),
                "brand_name": ("brand_name", None),
                "series_name": ("series_name", None),
                "car_source_city_name": ("car_source_city_name", None),
                "shop_id": ("shop_id", None),
                "tags": ("tags", None),
                "tags_v2": ("tags_v2", None),
                "brand_id": ("brand_id", 0),
                "series_id": ("series_id", 0),

                # Дополнительные поля
                "description": ("description", None),
                "color": ("color", None),
                "transmission": ("transmission", None),
                "fuel_type": ("fuel_type", None),
                "engine_volume": ("engine_volume", None),
                "body_type": ("body_type", None),
                "drive_type": ("drive_type", None),
                "condition": ("condition", None),

                # Поля с фиксированными значениями
                "uuid": (None, car_uuid),
                "source": (None, "dongchedi"),
                "is_available": (None, True),
                "created_at": (None, current_time),
                "updated_at": (None, current_time)
            }

            # Функции преобразования для полей
            transform_funcs = {
                # Преобразование car_id и sku_id в строки
                "car_id": lambda x: str(x) if x is not None else None,
                "sku_id": lambda x: str(x) if x is not None else None,

                # Преобразование списков в JSON-строки
                "tags": lambda x: json.dumps(x) if x is not None else None,
                "tags_v2": lambda x: json.dumps(x) if x is not None else None,

                # Декодирование цен
                "sh_price": lambda x: decode_dongchedi_list_sh_price(str(x)) if x is not None else None,
                "official_price": lambda x: decode_dongchedi_list_sh_price(str(x)) if x is not None else None,

                # Декодирование текстовых полей
                "title": lambda x: decode_dongchedi_detail(str(x)) if x is not None else None,
                "car_name": lambda x: decode_dongchedi_detail(str(x)) if x is not None else None,
                "sub_title": lambda x: decode_dongchedi_detail(str(x)) if x is not None else None,
            }

            # Извлекаем поля из данных
            filtered_car_data = await extract_fields(car_data, field_mappings, transform_funcs)

            # Копируем значения из одних полей в другие для совместимости
            if 'car_year' in filtered_car_data and filtered_car_data['car_year'] is not None:
                filtered_car_data['year'] = filtered_car_data['car_year']

            if 'car_mileage' in filtered_car_data and filtered_car_data['car_mileage'] is not None:
                # Преобразуем mileage в числовое значение, если возможно
                try:
                    mileage_str = str(filtered_car_data['car_mileage'])
                    mileage_numeric = re.sub(r'[^\d.]', '', mileage_str)
                    if mileage_numeric:
                        filtered_car_data['mileage'] = int(float(mileage_numeric))
                except:
                    pass

            if 'car_source_city_name' in filtered_car_data and filtered_car_data['car_source_city_name'] is not None:
                filtered_car_data['city'] = filtered_car_data['car_source_city_name']

            # Ensure price is properly set from sh_price
            if 'sh_price' in filtered_car_data and filtered_car_data['sh_price'] is not None:
                # Convert price to a numeric value if it's a string with units
                price_str = str(filtered_car_data['sh_price'])
                # Remove any non-numeric characters except decimal point
                price_numeric = re.sub(r'[^\d.]', '', price_str)
                if price_numeric:
                    filtered_car_data['price'] = price_numeric

            # Создаем объект DongchediCar
            return DongchediCar(**{k: v for k, v in filtered_car_data.items() if k in DongchediCar.__fields__})
        except Exception as e:
            # Логируем ошибку
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing car data: {str(e)}")
            return None

    async def async_fetch_cars(self, source: Optional[str] = None) -> DongchediApiResponse:
        """
        Асинхронно выполняет запрос к API dongchedi и возвращает распарсенный DongchediApiResponse.
        По умолчанию загружает первую страницу.

        Args:
            source: Игнорируется для этого парсера, так как используется API

        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        return await self.async_fetch_cars_by_page(1)

    @async_retry(retry_strategy=default_retry_strategy, circuit_breaker=default_circuit_breaker, endpoint="dongchedi_detail")
    async def async_fetch_car_detail(self, car_id: str) -> Tuple[Optional[DongchediCar], Dict[str, Any]]:
        """
        Асинхронно парсит детальную информацию о машине по car_id через Playwright.

        Args:
            car_id: ID машины

        Returns:
            Tuple[Optional[DongchediCar], Dict[str, Any]]: Объект DongchediCar и метаданные
        """
        try:
            # Используем асинхронный браузер для получения детальной информации
            car_info, meta = await fetch_car_detail_async(car_id)

            # Если получили данные о машине, создаем объект DongchediCar
            if car_info:
                try:
                    car_obj = DongchediCar(**{k: v for k, v in car_info.items() if k in DongchediCar.__fields__})
                    return car_obj, meta
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error creating DongchediCar object: {str(e)}")
                    return None, {"is_available": False, "error": str(e), "status": 500}
            else:
                return None, meta
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching car detail: {str(e)}")
            return None, {"is_available": False, "error": str(e), "status": 500}

    async def async_fetch_multiple_car_details(self, car_ids: List[str]) -> List[Tuple[Optional[DongchediCar], Dict[str, Any]]]:
        """
        Асинхронно парсит детальную информацию о нескольких машинах.

        Args:
            car_ids: Список ID машин

        Returns:
            List[Tuple[Optional[DongchediCar], Dict[str, Any]]]: Список кортежей с объектами DongchediCar и метаданными
        """
        # Используем функцию fetch_multiple_car_details из модуля async_browser
        car_details = await fetch_multiple_car_details(car_ids)

        # Преобразуем данные о машинах в объекты DongchediCar
        results = []
        for car_info, meta in car_details:
            if car_info:
                try:
                    car_obj = DongchediCar(**{k: v for k, v in car_info.items() if k in DongchediCar.__fields__})
                    results.append((car_obj, meta))
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error creating DongchediCar object: {str(e)}")
                    results.append((None, {"is_available": False, "error": str(e), "status": 500}))
            else:
                results.append((None, meta))

        return results

    async def async_fetch_all_cars(self) -> DongchediApiResponse:
        """
        Асинхронно получает все машины со всех страниц dongchedi с оптимизацией памяти.

        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        from ..async_processor import process_stream_concurrent
        from ..memory_optimized import AsyncBatchProcessor, MemoryOptimizedList
        import logging
        import gc

        logger = logging.getLogger(__name__)
        # Используем оптимизированный список для хранения машин
        all_cars = MemoryOptimizedList()
        seen_ids = set()

        # Функция для получения страницы с машинами
        async def fetch_page(page_num: int) -> List[Dict[str, Any]]:
            try:
                response = await self.async_fetch_cars_by_page(page_num)
                cars_list = getattr(response.data, 'search_sh_sku_info_list', [])
                # Преобразуем объекты в словари и сразу освобождаем память
                result = [car.dict() for car in cars_list]
                # Принудительно очищаем память после преобразования
                gc.collect()
                return result
            except Exception as e:
                logger.error(f"Error fetching page {page_num}: {str(e)}")
                return []

        # 1. Получаем первую страницу для определения общего количества страниц
        first_page_cars = await fetch_page(1)
        if not first_page_cars:
            return DongchediApiResponse(
                data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                message="Не удалось получить данные с первой страницы",
                status=404
            )

        # Добавляем машины с первой страницы
        for car_dict in first_page_cars:
            car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')
            if car_id not in seen_ids:
                all_cars.append(car_dict)
                seen_ids.add(car_id)

        # Освобождаем память после обработки первой страницы
        del first_page_cars
        gc.collect()

        # 2. Асинхронно получаем остальные страницы
        # Предполагаем, что всего может быть до 10 страниц (можно настроить)
        max_pages = 10

        # Обрабатываем страницы последовательно для экономии памяти
        for page in range(2, max_pages + 1):
            page_cars = await fetch_page(page)

            if not page_cars:
                continue

            # Проверяем, есть ли совпадения с уже полученными машинами
            found_existing = False
            for car_dict in page_cars:
                car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')

                if car_id not in seen_ids:
                    all_cars.append(car_dict)
                    seen_ids.add(car_id)
                else:
                    found_existing = True

            # Освобождаем память после обработки страницы
            del page_cars
            gc.collect()

            # Если нашли совпадение, прекращаем обработку страниц
            if found_existing:
                break

        # 3. Асинхронно преобразуем словари в объекты DongchediCar
        async def dict_to_car(car_dict: Dict[str, Any]) -> Optional[DongchediCar]:
            try:
                # Добавляем sort_number и source
                if 'source' not in car_dict:
                    car_dict['source'] = 'dongchedi'
                return DongchediCar(**car_dict)
            except Exception as e:
                logger.error(f"Error creating DongchediCar: {str(e)}")
                return None

        # Добавляем sort_number по убыванию (новые машины - большие номера)
        total = len(all_cars)
        for i, car in enumerate(all_cars):
            car['sort_number'] = total - i
            car['source'] = 'dongchedi'

        # Используем оптимизированный процессор для преобразования словарей в объекты DongchediCar
        processor = AsyncBatchProcessor(batch_size=20, max_concurrency=20)
        car_objects_list = MemoryOptimizedList()

        # Обрабатываем данные о машинах асинхронно с оптимизацией памяти
        async for car in processor.process_items(list(all_cars), dict_to_car):
            if car is not None:
                car_objects_list.append(car)

        # Преобразуем в обычный список для возврата
        car_objects = [car for car in car_objects_list if car is not None]

        # Освобождаем память
        del all_cars
        del car_objects_list
        del seen_ids
        gc.collect()

        return DongchediApiResponse(
            data=DongchediData(
                has_more=False,
                search_sh_sku_info_list=car_objects,
                total=len(car_objects)
            ),
            message=f"Загружено {len(car_objects)} машин со всех страниц.",
            status=200
        )

    async def async_fetch_incremental_cars(self, existing_cars: List[Dict[str, Any]]) -> DongchediApiResponse:
        """
        Асинхронно получает только новые машины с dongchedi до первого совпадения с существующими.
        Использует оптимизированные по памяти структуры данных.

        Args:
            existing_cars: Список существующих машин с полями car_id/sku_id/link

        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        from ..memory_optimized import AsyncBatchProcessor, MemoryOptimizedList
        import logging
        import gc

        logger = logging.getLogger(__name__)
        # Используем оптимизированный список для хранения новых машин
        new_cars = MemoryOptimizedList()
        existing_ids = set()
        pages_checked = 0

        # Собираем ID существующих машин
        for car in existing_cars:
            car_id = car.get('car_id') or car.get('sku_id') or car.get('link')
            if car_id:
                existing_ids.add(car_id)

        # Получаем следующий номер для нумерации
        next_sort_number = self._get_next_sort_number(existing_cars, 'dongchedi')

        # Функция для получения и обработки страницы
        async def process_page(page_num: int) -> Tuple[List[Dict[str, Any]], bool, bool]:
            """
            Получает и обрабатывает страницу с машинами.

            Args:
                page_num: Номер страницы

            Returns:
                Tuple[List[Dict[str, Any]], bool, bool]: Список новых машин, флаг найдены ли существующие машины, флаг есть ли еще страницы
            """
            try:
                response = await self.async_fetch_cars_by_page(page_num)
                cars_list = getattr(response.data, 'search_sh_sku_info_list', [])

                page_new_cars = []
                found_existing = False

                for car in cars_list:
                    car_dict = car.dict()
                    car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')

                    if car_id in existing_ids:
                        found_existing = True
                        break

                    page_new_cars.append(car_dict)

                has_more = getattr(response.data, 'has_more', False)
                return page_new_cars, found_existing, has_more
            except Exception as e:
                logger.error(f"Error processing page {page_num}: {str(e)}")
                return [], True, False  # В случае ошибки прекращаем обработку

        # Обрабатываем страницы последовательно, пока не найдем существующую машину
        page = 1
        while True:
            page_new_cars, found_existing, has_more = await process_page(page)
            pages_checked = page

            # Добавляем новые машины
            for car in page_new_cars:
                new_cars.append(car)

            # Освобождаем память после обработки страницы
            del page_new_cars
            gc.collect()

            # Если нашли существующую машину или нет больше страниц, прекращаем обработку
            if found_existing or not has_more:
                break

            page += 1

        # Если нет новых машин, возвращаем пустой результат
        if not new_cars:
            return DongchediApiResponse(
                data=DongchediData(
                    has_more=False,
                    search_sh_sku_info_list=[],
                    total=0
                ),
                message=f"Новых машин не найдено. Проверено {pages_checked} страниц.",
                status=200
            )

        # Добавляем sort_number по убыванию (новые машины - большие номера)
        total_new_cars = len(new_cars)
        for i, car in enumerate(new_cars):
            car['sort_number'] = next_sort_number + total_new_cars - i - 1
            car['source'] = 'dongchedi'

        # Асинхронно преобразуем словари в объекты DongchediCar
        async def dict_to_car(car_dict: Dict[str, Any]) -> Optional[DongchediCar]:
            try:
                return DongchediCar(**car_dict)
            except Exception as e:
                logger.error(f"Error creating DongchediCar: {str(e)}")
                return None

        # Используем оптимизированный процессор для преобразования словарей в объекты DongchediCar
        processor = AsyncBatchProcessor(batch_size=20, max_concurrency=20)
        car_objects_list = MemoryOptimizedList()

        # Обрабатываем данные о машинах асинхронно с оптимизацией памяти
        async for car in processor.process_items(list(new_cars), dict_to_car):
            if car is not None:
                car_objects_list.append(car)

        # Преобразуем в обычный список для возврата
        car_objects = [car for car in car_objects_list if car is not None]

        # Освобождаем память
        del new_cars
        del car_objects_list
        del existing_ids
        gc.collect()

        return DongchediApiResponse(
            data=DongchediData(
                has_more=False,
                search_sh_sku_info_list=car_objects,
                total=len(car_objects)
            ),
            message=f"Найдено {len(car_objects)} новых машин на {pages_checked} страницах.",
            status=200
        )

    def _get_next_sort_number(self, existing_cars: List[Dict[str, Any]], source: str) -> int:
        """
        Получает следующий номер для нумерации машин.
        При инкрементальном обновлении берет максимальный номер из существующих машин + 1.
        При полном парсинге начинает с 1.
        Новые машины получают большие номера (для сортировки по убыванию).
        """
        if not existing_cars:
            return 1

        # Ищем максимальный sort_number среди машин того же источника
        max_number = 0
        for car in existing_cars:
            if car.get('source') == source and car.get('sort_number'):
                max_number = max(max_number, car['sort_number'])

        return max_number + 1
