"""
Асинхронный API сервер для парсеров.
"""

import os
import gc
import asyncio
import functools
import logging
import time
import json
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware        
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import ipaddress
from api.che168.parser import Che168Parser
from api.che168.detailed_api import (
    router as che168_detailed_router,
    CarDetailRequest,
    parse_car_details as parse_che168_car_details,
)
from api.dongchedi.models.response import DongchediApiResponse
from api.dongchedi.models.car import DongchediCar
from api.memory_optimized import MemoryOptimizedList
from converters import decode_dongchedi_list_sh_price, decode_dongchedi_detail
from car_filter import filter_cars_by_year, is_electric_car
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime, timezone
from models import TaskCreateRequest, TaskCreateResponse, TaskType
from source_probes import SourceProbe, probe_item_value, run_source_probe
from task_service import task_service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Модель для запроса детального парсинга che168
class CarUrlRequest(BaseModel):
    car_url: str

# Модель для запроса получения детальной информации о нескольких машинах
class MultipleCarIdsRequest(BaseModel):
    car_ids: List[str]

# Load environment variables
load_dotenv()

def _get_int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if not raw:
        return max(default, minimum)
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Некорректное значение %s=%s. Используется значение по умолчанию %s.", name, raw, default)
        return max(default, minimum)
    return max(value, minimum)

DONGCHEDI_ENHANCE_MAX_CONCURRENT = _get_int_env("DONGCHEDI_ENHANCE_MAX_CONCURRENT", 5)
INCREMENTAL_EXISTING_LIMIT = _get_int_env("INCREMENTAL_EXISTING_LIMIT", 15000)
PERF_ATTACH_BODY = os.getenv("PERF_ATTACH_BODY", "false").lower() == "true"

# IP Whitelist configuration
# Формат: "192.168.1.100,10.0.0.0/8,172.16.0.0/12" (IP адреса и/или CIDR)
# Пустая строка или не задано = доступ разрешён всем
ALLOWED_IPS_RAW = os.getenv("ALLOWED_IPS", "").strip()

def _parse_allowed_ips(raw: str) -> list:
    """Парсит список разрешённых IP/CIDR в список ipaddress объектов"""
    if not raw:
        return []
    
    result = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            # Пробуем как сеть (CIDR нотация)
            if "/" in item:
                result.append(ipaddress.ip_network(item, strict=False))
            else:
                # Одиночный IP адрес
                result.append(ipaddress.ip_address(item))
        except ValueError as e:
            logger.warning(f"Некорректный IP/CIDR в ALLOWED_IPS: {item} - {e}")
    
    return result

ALLOWED_IPS = _parse_allowed_ips(ALLOWED_IPS_RAW)
if ALLOWED_IPS:
    logger.info(f"IP Whitelist включён. Разрешённые адреса: {ALLOWED_IPS_RAW}")
else:
    logger.warning("IP Whitelist отключён (ALLOWED_IPS не задан). Доступ открыт для всех!")


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки IP адреса клиента по whitelist"""

    def __init__(self, app, public_paths: set[str] | None = None):
        super().__init__(app)
        self.public_paths = public_paths or {"/health", "/"}
    
    async def dispatch(self, request: Request, call_next):
        # Если whitelist не настроен - пропускаем всех
        if not ALLOWED_IPS:
            return await call_next(request)
        
        # Публичные эндпоинты доступны всем
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # Получаем IP клиента (учитываем прокси)
        client_ip = self._get_client_ip(request)
        
        # Проверяем IP
        if not self._is_ip_allowed(client_ip):
            logger.warning(f"Доступ запрещён для IP: {client_ip} -> {request.url.path}")
            return JSONResponse(
                status_code=403,
                content={
                    "data": None,
                    "message": "Access denied: IP not in whitelist",
                    "status": 403
                }
            )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Получает реальный IP клиента (учитывает X-Forwarded-For, X-Real-IP)"""
        # Проверяем заголовки прокси
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For может содержать цепочку: "client, proxy1, proxy2"
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback на прямое подключение
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_ip_allowed(self, client_ip: str) -> bool:
        """Проверяет, входит ли IP в whitelist"""
        if client_ip == "unknown":
            return False
        
        try:
            ip = ipaddress.ip_address(client_ip)
        except ValueError:
            logger.warning(f"Некорректный IP адрес клиента: {client_ip}")
            return False
        
        for allowed in ALLOWED_IPS:
            if isinstance(allowed, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
                if ip in allowed:
                    return True
            elif ip == allowed:
                return True
        
        return False


def _get_next_sort_number(existing_cars: List[Dict], source: str) -> int:
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

# IP Whitelist middleware (первым, до CORS)
app.add_middleware(IPWhitelistMiddleware)

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

# Включаем роутеры для детального парсинга
app.include_router(che168_detailed_router)

# Локи для тяжёлых операций (полный парсинг), чтобы избежать дублирования нагрузки
# Используем LRU кэш для ограничения роста памяти
from collections import OrderedDict
from threading import Lock as ThreadLock

_full_fetch_locks: OrderedDict[str, asyncio.Lock] = OrderedDict()
_full_fetch_locks_max_size = 100  # Максимум 100 блокировок
_full_fetch_locks_lock = ThreadLock()


def _get_full_fetch_lock(key: str) -> asyncio.Lock:
    with _full_fetch_locks_lock:
        # Если блокировка уже существует, перемещаем её в конец (LRU)
        if key in _full_fetch_locks:
            lock = _full_fetch_locks.pop(key)
            _full_fetch_locks[key] = lock
            return lock
        
        # Если достигли лимита, удаляем самую старую блокировку
        if len(_full_fetch_locks) >= _full_fetch_locks_max_size:
            _full_fetch_locks.popitem(last=False)
        
        # Создаём новую блокировку
        lock = asyncio.Lock()
        _full_fetch_locks[key] = lock
        return lock

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

    # Если ответ в формате JSON, добавляем информацию о производительности в тело ответа (опционально)
    if PERF_ATTACH_BODY and response.headers.get("content-type") == "application/json":
        try:
            body = await response.body()
            # Ограничиваем размер body для обработки (максимум 10MB)
            MAX_BODY_SIZE = 10 * 1024 * 1024
            if len(body) > MAX_BODY_SIZE:
                # Пропускаем обработку для слишком больших ответов
                pass
            else:
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

# Импортируем синхронные парсеры
from api.dongchedi.parser import DongchediParser

# Создаем экземпляры парсеров
dongchedi_parser_instance = DongchediParser()
che168_parser_instance = Che168Parser()

# Асинхронные обертки для методов парсеров
class AsyncDongchediWrapper:
    def __init__(self, parser):
        self.parser = parser

    async def async_fetch_cars(self):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_cars)

    async def async_fetch_cars_by_page(self, page):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_cars_by_page, page)

    async def async_fetch_car_detail(self, car_id):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_car_detail, car_id)

    async def async_fetch_all_cars(self):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_all_cars)

    async def async_fetch_multiple_car_details(self, car_ids):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_multiple_car_details, car_ids)

async def run_blocking(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    # Добавляем таймаут для блокирующих операций (5 минут, согласовано с datahub)
    return await asyncio.wait_for(
        loop.run_in_executor(None, functools.partial(func, *args, **kwargs)),
        timeout=300.0  # 5 минут
    )
class AsyncChe168Wrapper:
    def __init__(self, parser):
        self.parser = parser

    async def async_fetch_cars(self):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_cars)

    async def async_fetch_cars_by_page(self, page):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_cars_by_page, page)

    async def async_fetch_car_detail(self, car_url):
        return await asyncio.get_event_loop().run_in_executor(None, self.parser.fetch_car_detail, car_url)

# Оборачиваем синхронные парсеры в асинхронные обертки
dongchedi_parser = AsyncDongchediWrapper(dongchedi_parser_instance)
che168_parser = AsyncChe168Wrapper(che168_parser_instance)

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
                "blocked": "/blocked",
                "cars": "/cars",
                "cars_page": "/cars/page/{page}",
                "cars_all": "/cars/all",
                "cars_incremental": "/cars/incremental",
                "health": "/health",
                "docs": "/docs",
                "redoc": "/redoc"
            }
        },
        "message": "Welcome to Async Car Parsers API",
        "status": 200
    }

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


def _summarize_dongchedi_detail(detail_response: Any, details: Dict[str, Any]) -> bool:
    detail_data = detail_response.get("data") if isinstance(detail_response, dict) else None
    details["detail_status"] = detail_response.get("status") if isinstance(detail_response, dict) else None
    if not isinstance(detail_data, dict):
        details["detail_error"] = "detail_unavailable"
        return False

    details["detail_is_banned"] = int(bool(detail_data.get("is_banned")))
    details["detail_has_images"] = int(
        bool(detail_data.get("image")) or bool(detail_data.get("image_gallery")) or bool(detail_data.get("image_count"))
    )
    details["detail_has_registration"] = int(bool(detail_data.get("first_registration_time")))

    if detail_response.get("status") == 200:
        return True

    details["detail_error"] = detail_data.get("error") or "detailed_probe_failed"
    return False


def _summarize_che168_detail(detail_response: Any, details: Dict[str, Any]) -> bool:
    detail_data = detail_response.data or {}
    details["detail_is_banned"] = int(bool(detail_response.is_banned))
    details["detail_has_images"] = int(
        bool(detail_data.get("image")) or bool(detail_data.get("image_gallery")) or bool(detail_data.get("image_count"))
    ) if isinstance(detail_data, dict) else 0
    details["detail_has_registration"] = int(bool(detail_data.get("first_registration_time"))) if isinstance(detail_data, dict) else 0

    if detail_response.success and isinstance(detail_data, dict) and detail_data:
        return True

    details["detail_error"] = detail_response.error or "detailed_probe_failed"
    return False


def _build_dongchedi_probe() -> SourceProbe:
    return SourceProbe(
        source="dongchedi",
        candidate_fields=("car_id", "image"),
        list_fetch=lambda: get_dongchedi_cars_by_page(1),
        detail_fetch=lambda candidate: get_dongchedi_car_detail(str(probe_item_value(candidate, "car_id"))),
        summarize_detail=_summarize_dongchedi_detail,
        list_timeout=60,
        detail_timeout=90,
    )


def _build_che168_probe() -> SourceProbe:
    return SourceProbe(
        source="che168",
        candidate_fields=("car_id", "shop_id", "image"),
        list_fetch=lambda: get_che168_cars_by_page(1),
        detail_fetch=lambda candidate: parse_che168_car_details(
            CarDetailRequest(
                car_id=int(probe_item_value(candidate, "car_id")),
                shop_id=int(probe_item_value(candidate, "shop_id")),
                force_update=False,
            )
        ),
        summarize_detail=_summarize_che168_detail,
        list_timeout=60,
        detail_timeout=120,
    )


async def get_dongchedi_blocked_status():
    """Короткий probe по dongchedi: list page 1 + one detailed."""
    return await run_source_probe(_build_dongchedi_probe())


async def get_che168_blocked_status():
    """Короткий probe по che168: list page 1 + one detailed."""
    return await run_source_probe(_build_che168_probe())

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
        
        # Фильтруем машины с годом выпуска меньше 2017
        year = car_dict.get('year')
        if year is not None:
            try:
                if int(year) < 2017:
                    continue
            except (ValueError, TypeError):
                pass
                
        car_dict.update({
            'sort_number': total_cars - i,  # Новые машины (первые в списке) получают большие номера
            'source': 'dongchedi'
        })
        if car_dict.get('sh_price'):
            car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])

            # Преобразуем car_id в int64 для совместимости с Go
            if 'car_id' in car_dict and car_dict['car_id'] is not None:
                try:
                    car_dict['car_id'] = int(car_dict['car_id'])
                except (ValueError, TypeError):
                    # Если не удалось преобразовать, устанавливаем значение по умолчанию
                    car_dict['car_id'] = 0

            # Тип силовой установки (электро/гибрид/ДВС) определяется в datahub
            # после получения полных данных, здесь не меняем is_available

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
        
        # Фильтруем машины с годом выпуска меньше 2017
        year = car_dict.get('year')
        if year is not None:
            try:
                if int(year) < 2017:
                    continue
            except (ValueError, TypeError):
                pass
                
        car_dict.update({
            'sort_number': total_cars - i,  # Новые машины (первые в списке) получают большие номера
            'source': 'dongchedi'
        })
        if car_dict.get('sh_price'):
            car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])

            # Преобразуем car_id в int64 для совместимости с Go
            if 'car_id' in car_dict and car_dict['car_id'] is not None:
                try:
                    car_dict['car_id'] = int(car_dict['car_id'])
                except (ValueError, TypeError):
                    # Если не удалось преобразовать, устанавливаем значение по умолчанию
                    car_dict['car_id'] = 0

            # Тип силовой установки определяется в datahub после получения полных данных

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

async def _collect_dongchedi_all_cars() -> Dict[str, Any]:
    """Фактический сбор всех машин dongchedi (без конкурентных дублей)."""
    all_cars = MemoryOptimizedList()
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

                # Преобразуем car_id в int64 для совместимости с Go
                if 'car_id' in car_dict and car_dict['car_id'] is not None:
                    try:
                        car_dict['car_id'] = int(car_dict['car_id'])
                    except (ValueError, TypeError):
                        # Если не удалось преобразовать, устанавливаем значение по умолчанию
                        car_dict['car_id'] = 0

                # Тип силовой установки определяется в datahub после получения полных данных

                all_cars.append(car_dict)
                seen_ids.add(car_id)
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

                # Преобразуем car_id в int64 для совместимости с Go
                if 'car_id' in car_dict and car_dict['car_id'] is not None:
                    try:
                        car_dict['car_id'] = int(car_dict['car_id'])
                    except (ValueError, TypeError):
                        # Если не удалось преобразовать, устанавливаем значение по умолчанию
                        car_dict['car_id'] = 0

                # Тип силовой установки определяется в datahub после получения полных данных

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

    response_payload = {
        "data": {
            "search_sh_sku_info_list": all_cars,
            "total": total
        },
        "message": f"Загружено {total} машин со всех страниц.",
        "status": 200
    }
    # Очищаем seen_ids для освобождения памяти
    seen_ids.clear()
    del seen_ids
    gc.collect()
    return response_payload


async def get_dongchedi_all_cars():
    """
    Получает все машины со всех страниц dongchedi, затем повторно проверяет первые страницы и добавляет только новые машины до первого совпадения.
    Экономит память: хранит только уникальные id машин.
    """
    lock = _get_full_fetch_lock("dongchedi_all")
    async with lock:
        return await _collect_dongchedi_all_cars()

async def get_dongchedi_incremental_cars(existing_cars: List[Dict]):
    """
    Получает только новые машины с dongchedi до первого совпадения с существующими.

    Args:
        existing_cars: Список существующих машин с полями car_id/sku_id/link
    """
    new_cars = MemoryOptimizedList()
    existing_ids = set()
    existing_sku_ids = set()

    # Собираем ID существующих машин
    for car in existing_cars:
        if len(existing_ids) >= INCREMENTAL_EXISTING_LIMIT and len(existing_sku_ids) >= INCREMENTAL_EXISTING_LIMIT:
            break

        car_id = car.get('car_id')
        sku_id = car.get('sku_id')
        if car_id and len(existing_ids) < INCREMENTAL_EXISTING_LIMIT:
            existing_ids.add(str(car_id))
        if sku_id and len(existing_sku_ids) < INCREMENTAL_EXISTING_LIMIT:
            existing_sku_ids.add(str(sku_id))
    
    # Получаем следующий номер для нумерации
    next_sort_number = _get_next_sort_number(existing_cars, 'dongchedi')

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
            car_id = car_dict.get('car_id')
            car_id_str = str(car_id) if car_id is not None else None

            if car_id_str and car_id_str in existing_ids:
                found_existing = True
                break
            
            sku_id = car_dict.get('sku_id')
            sku_id_str = str(sku_id) if sku_id is not None else None
            if sku_id_str and sku_id_str in existing_sku_ids:
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

            # Преобразуем car_id в int64 для совместимости с Go
            if 'car_id' in car_dict and car_dict['car_id'] is not None:
                try:
                    car_dict['car_id'] = int(car_dict['car_id'])
                except (ValueError, TypeError):
                    # Если не удалось преобразовать, устанавливаем значение по умолчанию
                    car_dict['car_id'] = 0

            new_cars.append(car_dict)

        if found_existing or page == 10:
            break

        if not getattr(response.data, 'has_more', False):
            break
        page += 1

    # Добавляем sort_number по убыванию (новые машины - большие номера)
    total_new_cars = len(new_cars)
    for i, car in enumerate(new_cars):
        car['sort_number'] = next_sort_number + total_new_cars - i - 1
        car['source'] = 'dongchedi'

    response_payload = {
        "data": {
            "search_sh_sku_info_list": new_cars,
            "total": len(new_cars),
            "pages_checked": page
        },
        "message": f"Найдено {len(new_cars)} новых машин на {page} страницах.",
        "status": 200
    }
    # Очищаем existing_ids для освобождения памяти
    existing_ids.clear()
    existing_sku_ids.clear()
    del existing_ids
    del existing_sku_ids
    gc.collect()
    return response_payload

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

async def get_che168_cars():
    """
    Получает данные о машинах с che168.
    """
    response = await che168_parser.async_fetch_cars()
    
    # Преобразуем в формат для совместимости с фронтендом
    cars_with_metadata = []
    total_cars = len(response.data.search_sh_sku_info_list)
    for i, car in enumerate(response.data.search_sh_sku_info_list):
        car_dict = car.dict()
        
        # Фильтруем машины с годом выпуска меньше 2017
        year = car_dict.get('year')
        if year is not None:
            try:
                if int(year) < 2017:
                    continue
            except (ValueError, TypeError):
                pass
                
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

async def get_che168_cars_by_page(page: int):
    """
    Получает данные о машинах с che168 для конкретной страницы

    Args:
        page: Номер страницы (начиная с 1)
    """
    response = await che168_parser.async_fetch_cars_by_page(page)
    
    # Преобразуем в формат для совместимости с фронтендом
    cars_with_metadata = []
    total_cars = len(response.data.search_sh_sku_info_list)
    for i, car in enumerate(response.data.search_sh_sku_info_list):
        car_dict = car.dict()
        
        # Фильтруем машины с годом выпуска меньше 2017
        year = car_dict.get('year')
        if year is not None:
            try:
                if int(year) < 2017:
                    continue
            except (ValueError, TypeError):
                pass
                
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

async def get_che168_incremental_cars(existing_cars: List[Dict]):
    """
    Получает только новые машины с che168 до первого совпадения с существующими.

    Args:
        existing_cars: Список существующих машин с полями car_id/sku_id/link
    """
    new_cars = []
    existing_ids = set()

    # Собираем ID существующих машин
    for car in existing_cars:
        car_id = car.get('car_id') or car.get('sku_id') or car.get('link')
        if car_id:
            existing_ids.add(car_id)

    # Получаем следующий номер для нумерации
    next_sort_number = _get_next_sort_number(existing_cars, 'che168')

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

        if found_existing or page == 10:
            break

        if not getattr(response.data, 'has_more', False):
            break
        page += 1

    # Добавляем sort_number по убыванию (новые машины - большие номера)
    total_new_cars = len(new_cars)
    for i, car in enumerate(new_cars):
        car['sort_number'] = next_sort_number + total_new_cars - i - 1
        car['source'] = 'che168'

    result = {
        "data": {
            "search_sh_sku_info_list": new_cars,
            "total": len(new_cars),
            "pages_checked": page
        },
        "message": f"Найдено {len(new_cars)} новых машин на {page} страницах.",
        "status": 200
    }
    # Очищаем existing_ids для освобождения памяти
    existing_ids.clear()
    del existing_ids
    gc.collect()
    return result

async def _collect_che168_all_cars() -> Dict[str, Any]:
    """Фактический сбор всех машин che168 (без параллельных дублей)."""
    all_cars = []
    seen_ids = set()

    # Принудительно проходим по всем страницам от 1 до 100
    # Это гарантирует, что мы получим все доступные машины
    max_pages = 100

    logger.info(f"[CHE168] Начинаем парсинг всех страниц che168 (всего {max_pages} страниц)")

    # Первый проход: собираем все машины со всех страниц
    for page in range(1, max_pages + 1):
        logger.info(f"[CHE168] Парсинг страницы {page} из {max_pages}...")

        # Делаем до 3 попыток получить данные с каждой страницы
        cars_list = None
        for attempt in range(3):
            try:
                response = await che168_parser.async_fetch_cars_by_page(page)
                cars_list = getattr(response.data, 'search_sh_sku_info_list', None)

                if cars_list and len(cars_list) > 0:
                    logger.info(f"[CHE168] Успешно получены данные со страницы {page} (попытка {attempt+1})")
                    break

                logger.warning(f"[CHE168] Попытка {attempt+1}: Страница {page} не содержит машин, пробуем еще раз")
                await asyncio.sleep(2)  # Пауза перед следующей попыткой

            except Exception as e:
                logger.error(f"[CHE168] Ошибка при парсинге страницы {page}, попытка {attempt+1}: {str(e)}")
                await asyncio.sleep(3)  # Увеличенная пауза при ошибке

        # Обрабатываем полученные данные
        if cars_list and len(cars_list) > 0:
            new_cars_count = 0
            for car in cars_list:
                car_dict = car.dict()
                car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')

                if car_id and car_id not in seen_ids:
                    # Тип силовой установки определяется в datahub
                    all_cars.append(car_dict)
                    seen_ids.add(car_id)
                    new_cars_count += 1

            logger.info(f"[CHE168] На странице {page} найдено {len(cars_list)} машин, из них {new_cars_count} новых")
        else:
            logger.warning(f"[CHE168] Страница {page} не содержит машин после всех попыток")

        # Небольшая пауза между запросами, чтобы не перегружать сервер
        await asyncio.sleep(1)

    # Второй проход: проверяем первые 10 страниц еще раз для поиска новых машин
    # Это нужно, так как во время парсинга могли появиться новые объявления
    logger.info(f"[CHE168] Первый проход завершен. Найдено {len(all_cars)} уникальных машин")
    logger.info("[CHE168] Начинаем повторную проверку первых 10 страниц")

    for repeat_page in range(1, min(11, max_pages + 1)):
        logger.info(f"[CHE168] Повторная проверка страницы {repeat_page}...")

        try:
            response = await che168_parser.async_fetch_cars_by_page(repeat_page)
            cars_list = getattr(response.data, 'search_sh_sku_info_list', None)

            if not cars_list or len(cars_list) == 0:
                logger.warning(f"[CHE168] Повторная проверка: страница {repeat_page} не содержит машин")
                continue

            new_cars_count = 0
            for car in cars_list:
                car_dict = car.dict()
                car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')

                if not car_id:
                    continue

                if car_id not in seen_ids:
                    all_cars.append(car_dict)
                    seen_ids.add(car_id)
                    new_cars_count += 1

            logger.info(f"[CHE168] При повторной проверке страницы {repeat_page} найдено {new_cars_count} новых машин")

            # Пауза между запросами
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"[CHE168] Ошибка при повторной проверке страницы {repeat_page}: {str(e)}")

    # Добавляем sort_number по убыванию (новые машины - большие номера)
    total = len(all_cars)
    logger.info(f"[CHE168] Всего найдено {total} уникальных машин")

    for i, car in enumerate(all_cars):
        car['sort_number'] = total - i
        car['source'] = 'che168'

    result = {
        "data": {
            "search_sh_sku_info_list": all_cars,
            "total": total
        },
        "message": f"Загружено {total} машин со всех страниц.",
        "status": 200
    }
    # Очищаем seen_ids для освобождения памяти
    seen_ids.clear()
    del seen_ids
    gc.collect()
    return result


async def get_che168_all_cars():
    """
    Получает все машины со всех страниц che168.
    Принудительно проходит по всем страницам от 1 до 100, чтобы гарантировать полный сбор данных.
    Экономит память: хранит только уникальные id машин.
    """
    lock = _get_full_fetch_lock("che168_all")
    async with lock:
        return await _collect_che168_all_cars()

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

async def create_task(request: TaskCreateRequest):
    """
    Создать новую задачу парсинга
    """
    if request.source not in ["dongchedi", "che168"]:
        return {"error": "Invalid source. Must be 'dongchedi' or 'che168'"}
    
    # Тип задачи: full / incremental (по умолчанию full)
    task_type = getattr(request, 'task_type', TaskType.FULL)
    id_field = getattr(request, 'id_field', None)
    existing_ids = getattr(request, 'existing_ids', None)
    task = task_service.create_task(request.source, task_type, id_field, existing_ids)
    
    # Запускаем обработку задачи в фоне
    asyncio.create_task(task_service.process_task(task.id))
    
    return TaskCreateResponse(task_id=task.id)

async def get_task_status(task_id: str):
    """
    Получить статус задачи
    """
    if task_id not in task_service.tasks:
        return {"error": "Task not found"}
    
    task = task_service.tasks[task_id]
    return {
        "task_id": task.id,
        "source": task.source,
        "status": task.status,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    }

async def enhance_dongchedi_car(sku_id: str, car_id: str = None):
    """
    Улучшает машину детальной информацией.
    
    Args:
        sku_id: SKU ID машины
        car_id: Car ID для технических характеристик (опционально)
    """
    try:
        # Создаем пустой объект машины для обогащения
        from api.dongchedi.models.car import DongchediCar
        car_obj = DongchediCar(sku_id=sku_id, source='dongchedi')
        
        # Улучшаем машину детальной информацией
        try:
            enhanced_car = await run_blocking(
                dongchedi_parser_instance.enhance_car_with_details,
                car_obj,
                sku_id,
                car_id,
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout enhancing car {sku_id} (exceeded 5 minutes)")
            return {
                "data": {"error": "Request timeout - exceeded 5 minutes"},
                "message": "Таймаут при улучшении машины",
                "status": 504
            }
        
        if enhanced_car is None:
            return {
                "data": {"error": "Failed to enhance car"},
                "message": "Не удалось обогатить машину",
                "status": 500
            }

        # ВАЖНО: вернуть обёрнутый ответ {"data": ...}, чтобы клиент datahub смог десериализовать
        return {
            "data": enhanced_car.dict(),
            "message": "Success",
            "status": 200
        }
    except Exception as e:
        logger.error(f"Error enhancing car {sku_id}: {str(e)}")
        return {
            "data": {"error": str(e)},
            "message": "Ошибка при улучшении машины",
            "status": 500
        }

async def get_dongchedi_car_specs(car_id: str):
    """
    Получает технические характеристики машины по car_id.
    
    Args:
        car_id: Car ID для страницы характеристик
    """
    try:
        specs, meta = await run_blocking(
            dongchedi_parser_instance.fetch_car_specifications,
            car_id,
        )
        
        return {
            "data": specs,
            "message": "Технические характеристики получены",
            "status": meta.get("status", 200)
        }
    except Exception as e:
        logger.error(f"Error getting car specs {car_id}: {str(e)}")
        return {
            "data": {"error": str(e)},
            "message": "Ошибка при получении характеристик",
            "status": 500
        }

async def batch_enhance_dongchedi_cars(request: dict):
    """
    Массовое улучшение машин детальной информацией.
    
    Args:
        request: Словарь с car_ids и их соответствующими sku_ids
        Пример: {"car_123": "sku_456", "car_789": "sku_012"}
    """
    try:
        semaphore = asyncio.Semaphore(DONGCHEDI_ENHANCE_MAX_CONCURRENT)

        async def process_item(car_id: str, sku_id: str):
            async with semaphore:
                try:
                    car_obj, meta = await dongchedi_parser.async_fetch_car_detail(sku_id)
                    if car_obj is None:
                        return {
                            "car_id": car_id,
                            "sku_id": sku_id,
                            "status": "error",
                            "message": "Car not found",
                        }

                    enhanced_car = await run_blocking(
                        dongchedi_parser_instance.enhance_car_with_details,
                        car_obj,
                        sku_id,
                        car_id,
                    )

                    return {
                        "car_id": car_id,
                        "sku_id": sku_id,
                        "status": "success",
                        "data": enhanced_car.dict(),
                    }
                except Exception as exc:
                    return {
                        "car_id": car_id,
                        "sku_id": sku_id,
                        "status": "error",
                        "message": str(exc),
                    }

        items = list(request.items())
        tasks = [
            asyncio.create_task(process_item(car_id, sku_id))
            for car_id, sku_id in items
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        normalized_results = []
        for task_result, (car_id, sku_id) in zip(raw_results, items):
            if isinstance(task_result, Exception):
                logger.error("Error in batch enhance for car %s/%s: %s", car_id, sku_id, task_result)
                normalized_results.append({
                    "car_id": car_id,
                    "sku_id": sku_id,
                    "status": "error",
                    "message": str(task_result)
                })
            else:
                normalized_results.append(task_result)

        successful = sum(1 for r in normalized_results if r.get("status") == "success")
        
        return {
            "data": {
                "results": normalized_results,
                "total": len(normalized_results),
                "successful": successful,
                "failed": len(normalized_results) - successful
            },
            "message": f"Обработано {len(normalized_results)} машин, успешно: {successful}",
            "status": 200
        }
    except Exception as e:
        logger.error(f"Error in batch enhance: {str(e)}")
        return {
            "data": {"error": str(e)},
            "message": "Ошибка при массовом улучшении",
            "status": 500
        }

async def shutdown_event():
    """
    Закрыть HTTP сессию при завершении работы
    """
    await task_service.close_session()
    # Закрываем глобальную HTTP сессию
    from api.http_client import http_client
    await http_client.close()

if __name__ == "__main__":
    import subprocess
    import sys
    subprocess.run([
        sys.executable, "-m", "granian",
        "--interface", "asgi",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--http1-keep-alive",
        "async_api_server:app"
    ])
