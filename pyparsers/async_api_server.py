"""
Асинхронный API сервер для парсеров.
"""

import os
import asyncio
import logging
import time
import json
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware        
from fastapi.responses import JSONResponse
from api.dongchedi.async_parser import AsyncDongchediParser
from api.che168.parser import Che168Parser
from api.dongchedi.models.response import DongchediApiResponse
from api.dongchedi.models.car import DongchediCar
from converters import decode_dongchedi_list_sh_price, decode_dongchedi_detail
from car_filter import filter_cars_by_year
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from datetime import datetime, timezone

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Модель для запроса детального парсинга che168
class CarUrlRequest(BaseModel):
    car_url: str

# Модель для запроса инкрементального обновления
class IncrementalRequest(BaseModel):
    existing_cars: List[Dict]

# Модель для запроса получения детальной информации о нескольких машинах
class MultipleCarIdsRequest(BaseModel):
    car_ids: List[str]

# Модель для ответа с информацией о производительности
class PerformanceInfo(BaseModel):
    execution_time_ms: float
    memory_usage_mb: Optional[float] = None
    request_timestamp: str
    response_timestamp: str

# Модель для расширенного ответа API
class ApiResponse(BaseModel):
    data: Any
    message: str
    status: int
    performance: Optional[PerformanceInfo] = None

# Load environment variables
load_dotenv()

async def _get_next_sort_number(existing_cars: List[Dict], source: str) -> int:
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

# Создаем приложение FastAPI с дополнительной информацией
app = FastAPI(
    title="Async Car Parsers API",
    description="Асинхронный API для парсинга информации о машинах с различных источников",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration from environment variables
cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
cors_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
cors_methods = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
cors_headers = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_credentials,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)

# Middleware для измерения производительности
@app.middleware("http")
async def add_performance_info(request, call_next):
    # Записываем время начала запроса
    start_time = time.time()
    request_timestamp = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Измеряем использование памяти до запроса
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / (1024 * 1024)  # MB
    except ImportError:
        memory_before = None

    # Выполняем запрос
    response = await call_next(request)

    # Записываем время окончания запроса
    end_time = time.time()
    response_timestamp = datetime.fromtimestamp(end_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    execution_time_ms = (end_time - start_time) * 1000

    # Измеряем использование памяти после запроса
    try:
        if memory_before is not None:
            memory_after = process.memory_info().rss / (1024 * 1024)  # MB
            memory_used = memory_after - memory_before
        else:
            memory_used = None
    except:
        memory_used = None

    # Добавляем информацию о производительности в заголовки ответа
    response.headers["X-Execution-Time"] = f"{execution_time_ms:.2f}ms"
    if memory_used is not None:
        response.headers["X-Memory-Usage"] = f"{memory_used:.2f}MB"
    response.headers["X-Request-Timestamp"] = request_timestamp
    response.headers["X-Response-Timestamp"] = response_timestamp

    # Если ответ в формате JSON, добавляем информацию о производительности в тело ответа
    if response.headers.get("content-type") == "application/json":
        try:
            body = await response.body()
            json_body = json.loads(body)

            if isinstance(json_body, dict):
                json_body["performance"] = {
                    "execution_time_ms": round(execution_time_ms, 2),
                    "memory_usage_mb": round(memory_used, 2) if memory_used is not None else None,
                    "request_timestamp": request_timestamp,
                    "response_timestamp": response_timestamp
                }

                return Response(
                    content=json.dumps(json_body),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json"
                )
        except:
            pass

    return response

# Создаем экземпляры парсеров
dongchedi_parser = AsyncDongchediParser()
che168_parser = Che168Parser()

# Асинхронные обертки для методов Che168Parser
class AsyncChe168Wrapper:
    def __init__(self, parser):
        self.parser = parser

    async def async_fetch_cars(self):
        # Запускаем синхронный метод в отдельном потоке через loop.run_in_executor
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_cars)

    async def async_fetch_cars_by_page(self, page):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_cars_by_page, page)

    async def async_fetch_car_detail(self, car_url):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_car_detail, car_url)

# Оборачиваем синхронный парсер в асинхронную обертку
che168_parser = AsyncChe168Wrapper(che168_parser)

@app.get("/")
async def root():
    """
    Корневой эндпоинт API.
    """
    return {
        "data": {
            "name": "Async Car Parsers API",
            "version": "1.0.0",
            "description": "Асинхронный API для парсинга информации о машинах с различных источников",
            "endpoints": {
                "dongchedi": "/cars/dongchedi",
                "dongchedi_page": "/cars/dongchedi/page/{page}",
                "dongchedi_all": "/cars/dongchedi/all",
                "dongchedi_incremental": "/cars/dongchedi/incremental",
                "dongchedi_car": "/cars/dongchedi/car/{car_id}",
                "dongchedi_cars": "/cars/dongchedi/cars",
                "che168": "/cars/che168",
                "che168_page": "/cars/che168/page/{page}",
                "che168_all": "/cars/che168/all",
                "che168_incremental": "/cars/che168/incremental",
                "che168_car": "/cars/che168/car",
                "health": "/health",
                "docs": "/docs",
                "redoc": "/redoc"
            }
        },
        "message": "Welcome to Async Car Parsers API",
        "status": 200
    }

@app.get("/health")
async def health_check():
    """
    Проверка работоспособности API.
    """
    return {
        "data": {
            "status": "ok",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime()),
            "services": {
                "dongchedi_parser": "available",
                "che168_parser": "available"
            }
        },
        "message": "Service is healthy",
        "status": 200
    }

@app.get("/cars/dongchedi")
async def get_dongchedi_cars():
    """
    Получает данные о машинах с dongchedi.
    """
    response = await dongchedi_parser.async_fetch_cars()

    # Фильтруем машины по году (не меньше 2017)
    filtered_cars_list = filter_cars_by_year(response.data.search_sh_sku_info_list, min_year=2017)
    
    # Преобразуем в формат для совместимости с фронтендом
    filtered_cars = []
    total_cars = len(filtered_cars_list)
    for i, car in enumerate(filtered_cars_list):
        car_dict = car.dict()
        car_dict.update({
            'sort_number': total_cars - i,  # Новые машины (первые в списке) получают большие номера
            'source': 'dongchedi'
        })
        if car_dict.get('sh_price'):
            car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
        filtered_cars.append(car_dict)

    return {
        "data": {
            "has_more": response.data.has_more,
            "search_sh_sku_info_list": filtered_cars,
            "total": response.data.total
        },
        "message": response.message,
        "status": response.status
    }

@app.get("/cars/dongchedi/page/{page}")
async def get_dongchedi_cars_by_page(page: int):
    """
    Получает данные о машинах с dongchedi для конкретной страницы.

    Args:
        page: Номер страницы (начиная с 1)
    """
    response = await dongchedi_parser.async_fetch_cars_by_page(page)

    # Фильтруем машины по году (не меньше 2017)
    filtered_cars_list = filter_cars_by_year(response.data.search_sh_sku_info_list, min_year=2017)
    
    # Преобразуем в формат для совместимости с фронтендом
    filtered_cars = []
    total_cars = len(filtered_cars_list)
    for i, car in enumerate(filtered_cars_list):
        car_dict = car.dict()
        car_dict.update({
            'sort_number': total_cars - i,  # Новые машины (первые в списке) получают большие номера
            'source': 'dongchedi'
        })
        if car_dict.get('sh_price'):
            car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
        filtered_cars.append(car_dict)

    return {
        "data": {
            "has_more": response.data.has_more,
            "search_sh_sku_info_list": filtered_cars,
            "total": response.data.total,
            "current_page": page
        },
        "message": response.message,
        "status": response.status
    }

@app.get("/cars/dongchedi/all")
async def get_dongchedi_all_cars():
    """
    Получает все машины со всех страниц dongchedi, затем повторно проверяет первые страницы и добавляет только новые машины до первого совпадения.
    Экономит память: хранит только уникальные id машин.
    """
    all_cars = []
    seen_ids = set()
    page = 1
    # 1. Основной проход по всем страницам
    while True:
        response = await dongchedi_parser.async_fetch_cars_by_page(page)
        cars_list = getattr(response.data, 'search_sh_sku_info_list', None)
        if not cars_list:
            break
        
        # Фильтруем машины по году (не меньше 2017)
        filtered_cars_list = filter_cars_by_year(cars_list, min_year=2017)
        
        for car in filtered_cars_list:
            car_dict = car.dict()
            car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')
            if car_id not in seen_ids:
                if car_dict.get('sh_price'):
                    car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
                all_cars.append(car_dict)
                seen_ids.add(car_id)
        print(len(cars_list))
        if not getattr(response.data, 'has_more', False):
            break
        page += 1
    # 2. Повторная проверка первых страниц (на случай новых машин)
    for repeat_page in range(1, page):
        response = await dongchedi_parser.async_fetch_cars_by_page(repeat_page)
        cars_list = getattr(response.data, 'search_sh_sku_info_list', None)
        if not cars_list:
            break
        for car in cars_list:
            car_dict = car.dict()
            car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')
            if car_id not in seen_ids:
                if car_dict.get('sh_price'):
                    car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
                all_cars.append(car_dict)
                seen_ids.add(car_id)
            else:
                # Как только встретили первое совпадение — прекращаем повторный проход
                break
        else:
            continue
        break

    # Добавляем sort_number по убыванию (новые машины - большие номера)
    total = len(all_cars)
    for i, car in enumerate(all_cars):
        car['sort_number'] = total - i
        car['source'] = 'dongchedi'

    return {
        "data": {
            "search_sh_sku_info_list": all_cars,
            "total": total
        },
        "message": f"Загружено {total} машин со всех страниц.",
        "status": 200
    }

@app.post("/cars/dongchedi/incremental")
async def get_dongchedi_incremental_cars(request: IncrementalRequest):
    """
    Получает только новые машины с dongchedi до первого совпадения с существующими.

    Args:
        request: Запрос с существующими машинами
    """
    existing_cars = request.existing_cars
    new_cars = []
    existing_ids = set()

    # Собираем ID существующих машин
    for car in existing_cars:
        car_id = car.get('car_id') or car.get('sku_id') or car.get('link')
        if car_id:
            existing_ids.add(car_id)

    # Получаем следующий номер для нумерации
    next_sort_number = await _get_next_sort_number(existing_cars, 'dongchedi')

    # Парсим до первого совпадения
    page = 1
    while True:
        response = await dongchedi_parser.async_fetch_cars_by_page(page)
        cars_list = getattr(response.data, 'search_sh_sku_info_list', None)
        if not cars_list:
            break

        found_existing = False
        for car in cars_list:
            car_dict = car.dict()
            car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')

            if car_id in existing_ids:
                found_existing = True
                break
                
            # Фильтруем машины с годом выпуска меньше 2017
            year = car_dict.get('year')
            if year is not None:
                try:
                    if int(year) < 2017:
                        continue
                except (ValueError, TypeError):
                    pass

            if car_dict.get('sh_price'):
                car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
            new_cars.append(car_dict)

        if found_existing:
            break

        if not getattr(response.data, 'has_more', False):
            break
        page += 1

    # Добавляем sort_number по убыванию (новые машины - большие номера)
    total_new_cars = len(new_cars)
    for i, car in enumerate(new_cars):
        car['sort_number'] = next_sort_number + total_new_cars - i - 1
        car['source'] = 'dongchedi'

    return {
        "data": {
            "search_sh_sku_info_list": new_cars,
            "total": len(new_cars),
            "pages_checked": page
        },
        "message": f"Найдено {len(new_cars)} новых машин на {page} страницах.",
        "status": 200
    }

@app.get("/cars/dongchedi/car/{car_id}")
async def get_dongchedi_car_detail(car_id: str):
    """
    Получает детальную информацию о конкретной машине с dongchedi по ID.

    Использует асинхронный метод async_fetch_car_detail для получения данных.
    """
    # Получаем детальную информацию о машине
    car_obj, meta = await dongchedi_parser.async_fetch_car_detail(car_id)

    if car_obj is not None:
        return {
            "data": car_obj.dict(),
            "message": "Success",
            "status": meta.get("status", 200)
        }
    else:
        return {
            "data": {"car_id": car_id, "is_available": False, "source": "dongchedi", "error": meta.get("error")},
            "message": f"Ошибка при парсинге: {meta.get('error')}",
            "status": meta.get("status", 500)
        }

@app.post("/cars/dongchedi/cars")
async def get_dongchedi_multiple_cars(request: MultipleCarIdsRequest):
    """
    Получает детальную информацию о нескольких машинах с dongchedi по их ID.

    Args:
        request: Запрос со списком ID машин
    """
    # Проверяем количество запрашиваемых машин
    if len(request.car_ids) > 20:
        return JSONResponse(
            status_code=400,
            content={
                "data": {"error": "Too many car IDs", "max_allowed": 20},
                "message": "Слишком много ID машин. Максимальное количество: 20",
                "status": 400
            }
        )

    # Получаем детальную информацию о машинах
    results = await dongchedi_parser.async_fetch_multiple_car_details(request.car_ids)

    # Преобразуем результаты в формат для ответа
    cars_data = []
    for car_obj, meta in results:
        if car_obj is not None:
            car_dict = car_obj.dict()
            if car_dict.get('sh_price'):
                car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
            cars_data.append({
                "car": car_dict,
                "meta": meta,
                "status": meta.get("status", 200)
            })
        else:
            car_id = meta.get("car_id", "unknown")
            cars_data.append({
                "car": {"car_id": car_id, "is_available": False, "source": "dongchedi", "error": meta.get("error")},
                "meta": meta,
                "status": meta.get("status", 500)
            })

    return {
        "data": {
            "cars": cars_data,
            "total": len(cars_data),
            "successful": sum(1 for item in cars_data if item["status"] == 200)
        },
        "message": "Получена информация о машинах",
        "status": 200
    }

@app.get("/cars/che168")
async def get_che168_cars():
    """
    Получает данные о машинах с che168.
    """
    response = await che168_parser.async_fetch_cars()
    
    # Фильтруем машины по году (не меньше 2017)
    filtered_cars_list = filter_cars_by_year(response.data.search_sh_sku_info_list, min_year=2017)
    
    # Преобразуем в формат для совместимости с фронтендом
    cars_with_metadata = []
    total_cars = len(filtered_cars_list)
    for i, car in enumerate(filtered_cars_list):
        car_dict = car.dict()
        car_dict.update({
            'sort_number': total_cars - i,  # Новые машины (первые в списке) получают большие номера
            'source': 'che168'
        })
        cars_with_metadata.append(car_dict)

    return {
        "data": {
            "has_more": response.data.has_more,
            "search_sh_sku_info_list": cars_with_metadata,
            "total": response.data.total
        },
        "message": response.message,
        "status": response.status
    }

@app.get("/cars/che168/page/{page}")
async def get_che168_cars_by_page(page: int):
    """
    Получает данные о машинах с che168 для конкретной страницы

    Args:
        page: Номер страницы (начиная с 1)
    """
    response = await che168_parser.async_fetch_cars_by_page(page)
    
    # Фильтруем машины по году (не меньше 2017)
    filtered_cars_list = filter_cars_by_year(response.data.search_sh_sku_info_list, min_year=2017)
    
    # Преобразуем в формат для совместимости с фронтендом
    cars_with_metadata = []
    total_cars = len(filtered_cars_list)
    for i, car in enumerate(filtered_cars_list):
        car_dict = car.dict()
        car_dict.update({
            'sort_number': total_cars - i,  # Новые машины (первые в списке) получают большие номера
            'source': 'che168'
        })
        cars_with_metadata.append(car_dict)

    return {
        "data": {
            "has_more": response.data.has_more,
            "search_sh_sku_info_list": cars_with_metadata,
            "total": response.data.total,
            "current_page": page
        },
        "message": response.message,
        "status": response.status
    }

@app.post("/cars/che168/incremental")
async def get_che168_incremental_cars(request: IncrementalRequest):
    """
    Получает только новые машины с che168 до первого совпадения с существующими.

    Args:
        request: Запрос с существующими машинами
    """
    existing_cars = request.existing_cars
    new_cars = []
    existing_ids = set()

    # Собираем ID существующих машин
    for car in existing_cars:
        car_id = car.get('car_id') or car.get('sku_id') or car.get('link')
        if car_id:
            existing_ids.add(car_id)

    # Получаем следующий номер для нумерации
    next_sort_number = await _get_next_sort_number(existing_cars, 'che168')

    # Парсим до первого совпадения
    page = 1
    while True:
        response = await che168_parser.async_fetch_cars_by_page(page)
        cars_list = getattr(response.data, 'search_sh_sku_info_list', None)
        if not cars_list:
            break

        found_existing = False
        for car in cars_list:
            car_dict = car.dict()
            car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')

            if car_id in existing_ids:
                found_existing = True
                break
                
            # Фильтруем машины с годом выпуска меньше 2017
            year = car_dict.get('year')
            if year is not None:
                try:
                    if int(year) < 2017:
                        continue
                except (ValueError, TypeError):
                    pass

            new_cars.append(car_dict)

        if found_existing:
            break

        if not getattr(response.data, 'has_more', False):
            break
        page += 1

    # Добавляем sort_number по убыванию (новые машины - большие номера)
    total_new_cars = len(new_cars)
    for i, car in enumerate(new_cars):
        car['sort_number'] = next_sort_number + total_new_cars - i - 1
        car['source'] = 'che168'

    return {
        "data": {
            "search_sh_sku_info_list": new_cars,
            "total": len(new_cars),
            "pages_checked": page
        },
        "message": f"Найдено {len(new_cars)} новых машин на {page} страницах.",
        "status": 200
    }

@app.get("/cars/che168/all")
async def get_che168_all_cars():
    """
    Получает все машины со всех страниц che168, затем повторно проверяет первые страницы и добавляет только новые машины до первого совпадения.
    Экономит память: хранит только уникальные id машин.
    """
    all_cars = []
    seen_ids = set()
    page = 1
    # 1. Основной проход по всем страницам (максимум 100 для che168)
    while page <= 100:
        response = await che168_parser.async_fetch_cars_by_page(page)
        cars_list = getattr(response.data, 'search_sh_sku_info_list', None)
        if not cars_list:
            break
        for car in cars_list:
            car_dict = car.dict()
            
            # Фильтруем машины с годом выпуска меньше 2017
            year = car_dict.get('year')
            if year is not None:
                try:
                    if int(year) < 2017:
                        continue
                except (ValueError, TypeError):
                    pass
                    
            car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')
            if car_id not in seen_ids:
                all_cars.append(car_dict)
                seen_ids.add(car_id)
        if not getattr(response.data, 'has_more', False):
            break
        page += 1
    # 2. Повторная проверка первых страниц (на случай новых машин)
    for repeat_page in range(1, min(page, 101)):
        response = await che168_parser.async_fetch_cars_by_page(repeat_page)
        cars_list = getattr(response.data, 'search_sh_sku_info_list', None)
        if not cars_list:
            break
        for car in cars_list:
            car_dict = car.dict()
            car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')
            if car_id not in seen_ids:
                all_cars.append(car_dict)
                seen_ids.add(car_id)
            else:
                # Как только встретили первое совпадение — прекращаем повторный проход
                break
        else:
            continue
        break

    # Добавляем sort_number по убыванию (новые машины - большие номера)
    total = len(all_cars)
    for i, car in enumerate(all_cars):
        car['sort_number'] = total - i
        car['source'] = 'che168'

    return {
        "data": {
            "search_sh_sku_info_list": all_cars,
            "total": total
        },
        "message": f"Загружено {total} машин со всех страниц.",
        "status": 200
    }

@app.post("/cars/che168/car")
async def get_che168_car_detail(request: CarUrlRequest):
    """
    Получает детальную информацию о конкретной машине с che168 по URL
    """
    car_obj, meta = await che168_parser.async_fetch_car_detail(request.car_url)
    if car_obj is not None:
        return {
            "data": car_obj.dict(),
            "message": "Success",
            "status": meta.get("status", 200)
        }
    else:
        return {
            "data": {"car_id": None, "is_available": False, "source": "che168", "error": meta.get("error")},
            "message": f"Ошибка при парсинге: {meta.get('error')}",
            "status": meta.get("status", 500)
        }

@app.get("/cars/dongchedi/stats")
async def get_dongchedi_stats():
    """
    Получает статистику по машинам с dongchedi.
    """
    # Получаем первую страницу для статистики
    response = await dongchedi_parser.async_fetch_cars_by_page(1)

    # Собираем статистику
    total_cars = getattr(response.data, 'total', 0)
    has_more = getattr(response.data, 'has_more', False)
    cars_on_page = len(getattr(response.data, 'search_sh_sku_info_list', []))

    # Собираем статистику по брендам
    brands = {}
    for car in getattr(response.data, 'search_sh_sku_info_list', []):
        brand = car.brand_name
        if brand:
            brands[brand] = brands.get(brand, 0) + 1

    # Сортируем бренды по количеству машин
    sorted_brands = sorted(brands.items(), key=lambda x: x[1], reverse=True)

    return {
        "data": {
            "total_cars": total_cars,
            "has_more_pages": has_more,
            "cars_on_first_page": cars_on_page,
            "top_brands": dict(sorted_brands[:10]) if sorted_brands else {},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime())
        },
        "message": "Статистика по машинам с dongchedi",
        "status": 200
    }

@app.get("/update/dongchedi/full")
async def update_dongchedi_full():
    """
    Эндпоинт для полного обновления данных dongchedi.
    Используется Go-приложением для получения всех машин.
    """
    try:
        # Получаем все машины с dongchedi
        response = await dongchedi_parser.async_fetch_all_cars()

        # Преобразуем car_id из строки в число для совместимости с Go структурой
        cars_list = getattr(response.data, 'search_sh_sku_info_list', [])
        for car in cars_list:
            # Преобразуем car_id в int64 для совместимости с Go
            if hasattr(car, 'car_id') and car.car_id is not None:
                try:
                    car.car_id = int(car.car_id)
                except (ValueError, TypeError):
                    # Если не удалось преобразовать, устанавливаем значение по умолчанию
                    car.car_id = 0

        # Возвращаем количество найденных машин
        count = len(cars_list)

        return {
            "count": count,
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Error in update_dongchedi_full: {str(e)}")
        return {
            "count": 0,
            "status": "error",
            "message": str(e)
        }

@app.get("/update/che168/full")
async def update_che168_full():
    """
    Эндпоинт для полного обновления данных che168.
    Используется Go-приложением для получения всех машин.
    """
    try:
        # Получаем все машины с che168
        response = await get_che168_all_cars()

        # Возвращаем количество найденных машин
        count = len(getattr(response.data, 'search_sh_sku_info_list', []))

        return {
            "count": count,
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Error in update_che168_full: {str(e)}")
        return {
            "count": 0,
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
