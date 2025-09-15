import os
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.dongchedi.parser import DongchediParser
from api.che168.parser import Che168Parser
from converters import decode_dongchedi_list_sh_price, decode_dongchedi_detail
from car_filter import filter_cars_by_year
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel
from models import TaskCreateRequest, TaskCreateResponse
from task_service import task_service

# Модель для запроса детального парсинга che168
class CarUrlRequest(BaseModel):
    car_url: str

# Load environment variables
load_dotenv()

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

app = FastAPI()

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

@app.get("/cars/dongchedi")
def get_dongchedi_cars():
    parser = DongchediParser()
    response = parser.fetch_cars()
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
def get_dongchedi_cars_by_page(page: int):
    """
    Получает данные о машинах с dongchedi для конкретной страницы

    Args:
        page: Номер страницы (начиная с 1)
    """
    parser = DongchediParser()
    response = parser.fetch_cars_by_page(page)
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

@app.get("/cars/che168")
def get_che168_cars():
    parser = Che168Parser()
    response = parser.fetch_cars()
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

@app.get("/cars/che168/page/{page}")
def get_che168_cars_by_page(page: int):
    """
    Получает данные о машинах с che168 для конкретной страницы

    Args:
        page: Номер страницы (начиная с 1)
    """
    parser = Che168Parser()
    response = parser.fetch_cars_by_page(page)
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

@app.get("/cars/dongchedi/all")
def get_dongchedi_all_cars():
    """
    Получает все машины со всех страниц dongchedi, затем повторно проверяет первые страницы и добавляет только новые машины до первого совпадения.
    Экономит память: хранит только уникальные id машин.
    """
    parser = DongchediParser()
    all_cars = []
    seen_ids = set()
    page = 1
    # 1. Основной проход по всем страницам
    while True:
        response = parser.fetch_cars_by_page(page)
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

                all_cars.append(car_dict)
                seen_ids.add(car_id)
        print(len(cars_list))
        if not getattr(response.data, 'has_more', False):
            break
        page += 1
    # 2. Повторная проверка первых страниц (на случай новых машин)
    for repeat_page in range(1, page):
        response = parser.fetch_cars_by_page(repeat_page)
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
def get_dongchedi_incremental_cars(existing_cars: List[Dict]):
    """
    Получает только новые машины с dongchedi до первого совпадения с существующими.

    Args:
        existing_cars: Список существующих машин с полями car_id/sku_id/link
    """
    parser = DongchediParser()
    new_cars = []
    existing_ids = set()
    existing_sku_ids = set()

    # Собираем ID существующих машин
    for car in existing_cars:
        car_id = car.get('car_id')
        sku_id=car.get('sku_id')
        if car_id:
            existing_ids.add(car_id)
        if sku_id:
            existing_sku_ids.add(sku_id)
    print(existing_ids)
    # Получаем следующий номер для нумерации
    next_sort_number = _get_next_sort_number(existing_cars, 'dongchedi')

    # Парсим до первого совпадения
    page = 1
    while True:
        response = parser.fetch_cars_by_page(page)
        cars_list = getattr(response.data, 'search_sh_sku_info_list', None)
        if not cars_list:
            break

        found_existing = False
        for car in cars_list:
            car_dict = car.dict()
            car_id = car_dict.get('car_id')

            if car_id in existing_ids:
                found_existing = True
                break
            
            sku_id = car_dict.get('sku_id')
            if sku_id in existing_sku_ids:
                print(car_id)
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

            # Преобразуем car_id в int64
            if 'car_id' in car_dict and car_dict['car_id'] is not None:
                try:
                    car_dict['car_id'] = int(car_dict['car_id'])
                except (ValueError, TypeError):
                    # Если не удалось преобразовать, устанавливаем значение по умолчанию
                    car_dict['car_id'] = 0

            new_cars.append(car_dict)

        if found_existing or page==10:
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

@app.post("/cars/che168/incremental")
def get_che168_incremental_cars(existing_cars: List[Dict]):
    """
    Получает только новые машины с che168 до первого совпадения с существующими.

    Args:
        existing_cars: Список существующих машин с полями car_id/sku_id/link
    """
    parser = Che168Parser()
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
        response = parser.fetch_cars_by_page(page)
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

            new_cars.append(car_dict)

        if found_existing or page==10:
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
def get_che168_all_cars():
    """
    Получает все машины со всех страниц che168.
    Принудительно проходит по всем страницам от 1 до 100, чтобы гарантировать полный сбор данных.
    Экономит память: хранит только уникальные id машин.
    """
    import logging
    import time
    import sys

    # Настройка логирования
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Создаем парсер
    parser = Che168Parser()
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
                response = parser.fetch_cars_by_page(page)
                cars_list = getattr(response.data, 'search_sh_sku_info_list', None)

                if cars_list and len(cars_list) > 0:
                    logger.info(f"[CHE168] Успешно получены данные со страницы {page} (попытка {attempt+1})")
                    break

                logger.warning(f"[CHE168] Попытка {attempt+1}: Страница {page} не содержит машин, пробуем еще раз")
                time.sleep(2)  # Пауза перед следующей попыткой

            except Exception as e:
                logger.error(f"[CHE168] Ошибка при парсинге страницы {page}, попытка {attempt+1}: {str(e)}")
                time.sleep(3)  # Увеличенная пауза при ошибке

        # Обрабатываем полученные данные
        if cars_list and len(cars_list) > 0:
            new_cars_count = 0
            for car in cars_list:
                car_dict = car.dict()
                car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')

                if car_id and car_id not in seen_ids:
                    all_cars.append(car_dict)
                    seen_ids.add(car_id)
                    new_cars_count += 1

            logger.info(f"[CHE168] На странице {page} найдено {len(cars_list)} машин, из них {new_cars_count} новых")
        else:
            logger.warning(f"[CHE168] Страница {page} не содержит машин после всех попыток")

        # Небольшая пауза между запросами, чтобы не перегружать сервер
        time.sleep(1)

    # Второй проход: проверяем первые 10 страниц еще раз для поиска новых машин
    # Это нужно, так как во время парсинга могли появиться новые объявления
    logger.info(f"[CHE168] Первый проход завершен. Найдено {len(all_cars)} уникальных машин")
    logger.info("[CHE168] Начинаем повторную проверку первых 10 страниц")

    for repeat_page in range(1, min(11, max_pages + 1)):
        logger.info(f"[CHE168] Повторная проверка страницы {repeat_page}...")

        try:
            response = parser.fetch_cars_by_page(repeat_page)
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
            time.sleep(1)

        except Exception as e:
            logger.error(f"[CHE168] Ошибка при повторной проверке страницы {repeat_page}: {str(e)}")

    # Добавляем sort_number по убыванию (новые машины - большие номера)
    total = len(all_cars)
    logger.info(f"[CHE168] Всего найдено {total} уникальных машин")

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

@app.get("/cars/dongchedi/car/{car_id}")
def get_dongchedi_car_detail(car_id: str):
    """
    Получает детальную информацию о конкретной машине с dongchedi по ID
    """
    from api.dongchedi.parser import DongchediParser
    parser = DongchediParser()
    car_obj, meta = parser.fetch_car_detail(car_id)
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

@app.post("/cars/che168/car")
def get_che168_car_detail(request: CarUrlRequest):
    """
    Получает детальную информацию о конкретной машине с che168 по URL
    """
    from api.che168.parser import Che168Parser
    parser = Che168Parser()
    car_obj, meta = parser.fetch_car_detail(request.car_url)
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

@app.post("/tasks", response_model=TaskCreateResponse)
async def create_task(request: TaskCreateRequest):
    """
    Создать новую задачу парсинга
    """
    if request.source not in ["dongchedi", "che168"]:
        return {"error": "Invalid source. Must be 'dongchedi' or 'che168'"}
    
    task = task_service.create_task(request.source)
    
    # Запускаем обработку задачи в фоне
    asyncio.create_task(task_service.process_task(task.id))
    
    return TaskCreateResponse(task_id=task.id)

@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
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

@app.on_event("shutdown")
async def shutdown_event():
    """
    Закрыть HTTP сессию при завершении работы
    """
    await task_service.close_session()


