"""
Асинхронный API сервер для парсеров.
"""

import os
import asyncio
import logging
import time
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.dongchedi.async_parser import AsyncDongchediParser
from api.dongchedi.models.response import DongchediApiResponse
from api.dongchedi.models.car import DongchediCar
from converters import decode_dongchedi_list_sh_price
from typing import List, Dict, Optional, Any, Union, Set
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Модель для запроса детального парсинга
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
    request_timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime(start_time))

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
    response_timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime(end_time))
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

@app.get("/cars/dongchedi")
async def get_dongchedi_cars():
    """
    Получает данные о машинах с dongchedi.
    """
    response = await dongchedi_parser.async_fetch_cars()

    # Преобразуем в формат для совместимости с фронтендом
    filtered_cars = []
    total_cars = len(response.data.search_sh_sku_info_list)
    for i, car in enumerate(response.data.search_sh_sku_info_list):
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

    # Преобразуем в формат для совместимости с фронтендом
    filtered_cars = []
    total_cars = len(response.data.search_sh_sku_info_list)
    for i, car in enumerate(response.data.search_sh_sku_info_list):
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
    Получает все машины со всех страниц dongchedi.
    """
    response = await dongchedi_parser.async_fetch_all_cars()

    # Преобразуем в формат для совместимости с фронтендом
    filtered_cars = []
    for car in response.data.search_sh_sku_info_list:
        car_dict = car.dict()
        if car_dict.get('sh_price'):
            car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
        filtered_cars.append(car_dict)

    return {
        "data": {
            "search_sh_sku_info_list": filtered_cars,
            "total": len(filtered_cars)
        },
        "message": response.message,
        "status": response.status
    }

@app.post("/cars/dongchedi/incremental")
async def get_dongchedi_incremental_cars(request: IncrementalRequest):
    """
    Получает только новые машины с dongchedi до первого совпадения с существующими.

    Args:
        request: Запрос с существующими машинами
    """
    response = await dongchedi_parser.async_fetch_incremental_cars(request.existing_cars)

    # Преобразуем в формат для совместимости с фронтендом
    filtered_cars = []
    for car in response.data.search_sh_sku_info_list:
        car_dict = car.dict()
        if car_dict.get('sh_price'):
            car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
        filtered_cars.append(car_dict)

    return {
        "data": {
            "search_sh_sku_info_list": filtered_cars,
            "total": len(filtered_cars)
        },
        "message": response.message,
        "status": response.status
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
