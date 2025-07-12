from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.dongchedi.parser import DongchediParser
from api.che168.parser import Che168Parser
from converters import decode_sh_price
from typing import List, Dict

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/cars/dongchedi")
def get_dongchedi_cars():
    parser = DongchediParser()
    response = parser.fetch_cars()
    # Преобразуем в формат для совместимости с фронтендом
    filtered_cars = []
    for car in response.data.search_sh_sku_info_list:
        car_dict = car.dict()
        if car_dict.get('sh_price'):
            car_dict['sh_price'] = decode_sh_price(car_dict['sh_price'])
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
    for car in response.data.search_sh_sku_info_list:
        car_dict = car.dict()
        if car_dict.get('sh_price'):
            car_dict['sh_price'] = decode_sh_price(car_dict['sh_price'])
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
    return {
        "data": {
            "has_more": response.data.has_more,
            "search_sh_sku_info_list": [car.dict() for car in response.data.search_sh_sku_info_list],
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
    return {
        "data": {
            "has_more": response.data.has_more,
            "search_sh_sku_info_list": [car.dict() for car in response.data.search_sh_sku_info_list],
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
        for car in cars_list:
            car_dict = car.dict()
            car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')
            if car_id not in seen_ids:
                if car_dict.get('sh_price'):
                    car_dict['sh_price'] = decode_sh_price(car_dict['sh_price'])
                all_cars.append(car_dict)
                seen_ids.add(car_id)
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
                    car_dict['sh_price'] = decode_sh_price(car_dict['sh_price'])
                all_cars.append(car_dict)
                seen_ids.add(car_id)
            else:
                # Как только встретили первое совпадение — прекращаем повторный проход
                break
        else:
            continue
        break
    total = len(all_cars)
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
    
    # Собираем ID существующих машин
    for car in existing_cars:
        car_id = car.get('car_id') or car.get('sku_id') or car.get('link')
        if car_id:
            existing_ids.add(car_id)
    
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
                
            if car_dict.get('sh_price'):
                car_dict['sh_price'] = decode_sh_price(car_dict['sh_price'])
            new_cars.append(car_dict)
        
        if found_existing:
            break
            
        if not getattr(response.data, 'has_more', False):
            break
        page += 1
    
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
        
        if found_existing:
            break
            
        if not getattr(response.data, 'has_more', False):
            break
        page += 1
    
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
    Получает все машины со всех страниц che168, затем повторно проверяет первые страницы и добавляет только новые машины до первого совпадения.
    Экономит память: хранит только уникальные id машин.
    """
    parser = Che168Parser()
    all_cars = []
    seen_ids = set()
    page = 1
    # 1. Основной проход по всем страницам (максимум 100 для che168)
    while page <= 100:
        response = parser.fetch_cars_by_page(page)
        cars_list = getattr(response.data, 'search_sh_sku_info_list', None)
        if not cars_list:
            break
        for car in cars_list:
            car_dict = car.dict()
            car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')
            if car_id not in seen_ids:
                all_cars.append(car_dict)
                seen_ids.add(car_id)
        if not getattr(response.data, 'has_more', False):
            break
        page += 1
    # 2. Повторная проверка первых страниц (на случай новых машин)
    for repeat_page in range(1, min(page, 101)):
        response = parser.fetch_cars_by_page(repeat_page)
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
    total = len(all_cars)
    return {
        "data": {
            "search_sh_sku_info_list": all_cars,
            "total": total
        },
        "message": f"Загружено {total} машин со всех страниц.",
        "status": 200
    }
