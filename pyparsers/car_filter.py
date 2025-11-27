"""
Модуль для фильтрации автомобилей по различным критериям.
"""

import logging

logger = logging.getLogger(__name__)

def is_electric_car(car_dict: dict) -> bool:
    """
    Проверяет, является ли автомобиль электромобилем по нескольким полям.
    
    Args:
        car_dict: Словарь с данными автомобиля
        
    Returns:
        True, если автомобиль является электромобилем, иначе False
    """
    if not car_dict:
        return False
    
    car_id = car_dict.get('car_id') or car_dict.get('sku_id') or 'unknown'
    
    # Проверяем fuel_type
    fuel_type = str(car_dict.get('fuel_type', '')).strip()
    fuel_type_lower = fuel_type.lower()
    
    # Проверяем числовой код "4" (электромобиль в che168)
    if fuel_type == "4":
        logger.debug(f"is_electric_car({car_id}): True - fuel_type='4'")
        return True
    
    # Проверяем строковые значения
    electric_fuel_types = [
        'pure electric', '纯电动', '电', '充电', 'electric', 'ev',
        '纯电', '电动车', '电动', '新能源', 'new energy'
    ]
    if fuel_type_lower and any(electric_type in fuel_type_lower for electric_type in electric_fuel_types):
        logger.debug(f"is_electric_car({car_id}): True - fuel_type='{fuel_type}' contains electric keyword")
        return True
    
    # Проверяем engine_volume - для электромобилей может быть пустым или содержать "电"
    engine_volume = str(car_dict.get('engine_volume', '')).strip()
    if engine_volume and '电' in engine_volume:
        logger.debug(f"is_electric_car({car_id}): True - engine_volume='{engine_volume}' contains 电")
        return True
    
    # Проверяем наличие полей, характерных для электромобилей
    battery_capacity = car_dict.get('battery_capacity')
    electric_range = car_dict.get('electric_range')
    if battery_capacity or electric_range:
        logger.debug(f"is_electric_car({car_id}): True - battery_capacity='{battery_capacity}', electric_range='{electric_range}'")
        return True
    
    # Точные фразы для определения электромобиля (более строгий критерий)
    # Убрал проверку tags, description, title - слишком много ложных срабатываний
    # Основной критерий - fuel_type и battery_capacity/electric_range
    
    return False

def filter_cars_by_year(cars, min_year=2017):
    """
    Фильтрует список автомобилей, оставляя только те, у которых год выпуска не меньше указанного.
    
    Args:
        cars: Список автомобилей (словари или объекты с методом dict())
        min_year: Минимальный год выпуска (включительно)
        
    Returns:
        Отфильтрованный список автомобилей
    """
    filtered_cars = []
    
    for car in cars:
        # Если это объект с методом dict(), преобразуем его в словарь
        if hasattr(car, 'dict') and callable(getattr(car, 'dict')):
            car_dict = car.dict()
        else:
            car_dict = car
            
        # Проверяем год выпуска
        year = car_dict.get('year')
        if year is not None:
            try:
                # Преобразуем год в число, если это строка
                year_int = int(year)
                if year_int >= min_year:
                    filtered_cars.append(car)
            except (ValueError, TypeError):
                # Если не удалось преобразовать год в число, пропускаем машину
                pass
        
    return filtered_cars