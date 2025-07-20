"""
Модуль для фильтрации автомобилей по различным критериям.
"""

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