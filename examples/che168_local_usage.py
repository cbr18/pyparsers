#!/usr/bin/env python3
"""
Примеры использования локального файла для Che168 парсера
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.parser_factory import ParserFactory
from api.che168fetch import Che168Parser
from translate import translate_text
from converters import decode_sh_price

def print_car_info(car, source_name="Unknown"):
    """Универсальная функция для вывода информации о машине"""
    output = []
    output.append("-" * 50)
    output.append(f"Источник: {source_name}")
    output.append("-" * 50)
    
    # Основная информация
    if car.brand_name:
        output.append(f"Марка: {translate_text(car.brand_name)}")
    if car.car_name:
        output.append(f"Модель: {translate_text(car.car_name)}")
    if car.series_name:
        output.append(f"Серия: {translate_text(car.series_name)}")
    if car.car_year:
        output.append(f"Год: {car.car_year}")
    if car.car_source_city_name:
        output.append(f"Город: {translate_text(car.car_source_city_name)}")
    if car.car_mileage:
        output.append(f"Пробег: {car.car_mileage} км")
    
    # Цена
    if car.sh_price:
        decoded_price = decode_sh_price(car.sh_price)
        output.append(f"Цена: {decoded_price}")
    
    # Заголовок
    if car.title:
        output.append(f"Заголовок: {translate_text(car.title)}")
    
    # Ссылки
    if car.image:
        output.append(f"Фото: {car.image}")
    if car.link:
        output.append(f"Ссылка: {car.link}")
    
    # Дополнительная информация
    if car.tags_v2:
        output.append(f"Теги: {car.tags_v2}")
    
    output.append("")
    print("\n".join(output))

def example_1_factory_local():
    """Пример 1: Использование фабрики с локальным файлом"""
    print("=== ПРИМЕР 1: Фабрика парсеров + локальный файл ===")
    
    parser = ParserFactory.get_parser('che168')
    response = parser.fetch_cars('local')
    
    if response.data and response.data.search_sh_sku_info_list:
        print(f"Найдено машин: {len(response.data.search_sh_sku_info_list)}")
        for i, car in enumerate(response.data.search_sh_sku_info_list[:2]):
            print_car_info(car, "Фабрика + local")
    else:
        print("Машины не найдены")

def example_2_direct_parser():
    """Пример 2: Прямое использование парсера"""
    print("\n=== ПРИМЕР 2: Прямое использование парсера ===")
    
    parser = Che168Parser()
    response = parser.fetch_cars('local')
    
    if response.data and response.data.search_sh_sku_info_list:
        print(f"Найдено машин: {len(response.data.search_sh_sku_info_list)}")
        for i, car in enumerate(response.data.search_sh_sku_info_list[:2]):
            print_car_info(car, "Прямой парсер")
    else:
        print("Машины не найдены")

def example_3_custom_file_path():
    """Пример 3: Указание пути к файлу"""
    print("\n=== ПРИМЕР 3: Указание пути к файлу ===")
    
    # Путь к файлу относительно корня проекта
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '二手车_二手车之家.html')
    
    parser = Che168Parser()
    response = parser.fetch_cars(file_path)
    
    if response.data and response.data.search_sh_sku_info_list:
        print(f"Найдено машин: {len(response.data.search_sh_sku_info_list)}")
        for i, car in enumerate(response.data.search_sh_sku_info_list[:2]):
            print_car_info(car, "Кастомный путь")
    else:
        print("Машины не найдены")

def example_4_batch_processing():
    """Пример 4: Пакетная обработка данных"""
    print("\n=== ПРИМЕР 4: Пакетная обработка ===")
    
    parser = Che168Parser()
    response = parser.fetch_cars('local')
    
    if response.data and response.data.search_sh_sku_info_list:
        cars = response.data.search_sh_sku_info_list
        
        # Статистика по годам
        years = {}
        for car in cars:
            if car.car_year:
                years[car.car_year] = years.get(car.car_year, 0) + 1
        
        print("Статистика по годам:")
        for year in sorted(years.keys()):
            print(f"  {year}: {years[year]} машин")
        
        # Средняя цена
        prices = []
        for car in cars:
            if car.sh_price:
                try:
                    price = float(car.sh_price)
                    prices.append(price)
                except:
                    pass
        
        if prices:
            avg_price = sum(prices) / len(prices)
            print(f"\nСредняя цена: {avg_price:.2f} млн юаней")
            print(f"Минимальная цена: {min(prices):.2f} млн юаней")
            print(f"Максимальная цена: {max(prices):.2f} млн юаней")

def example_5_filtering():
    """Пример 5: Фильтрация данных"""
    print("\n=== ПРИМЕР 5: Фильтрация данных ===")
    
    parser = Che168Parser()
    response = parser.fetch_cars('local')
    
    if response.data and response.data.search_sh_sku_info_list:
        cars = response.data.search_sh_sku_info_list
        
        # Фильтруем машины 2020 года и новее
        recent_cars = [car for car in cars if car.car_year and car.car_year >= 2020]
        
        print(f"Машины 2020 года и новее ({len(recent_cars)} из {len(cars)}):")
        for i, car in enumerate(recent_cars[:3]):
            print_car_info(car, f"Новые машины ({car.car_year})")

def main():
    """Основная функция с примерами"""
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ЛОКАЛЬНОГО ФАЙЛА ДЛЯ CHE168")
    print("=" * 60)
    
    example_1_factory_local()
    example_2_direct_parser()
    example_3_custom_file_path()
    example_4_batch_processing()
    example_5_filtering()
    
    print("\n" + "=" * 60)
    print("ИНСТРУКЦИЯ ПО ОБНОВЛЕНИЮ ЛОКАЛЬНОГО ФАЙЛА:")
    print("1. Откройте https://www.che168.com в браузере")
    print("2. Сохраните страницу как HTML (Ctrl+S)")
    print("3. Переименуйте файл в '二手车_二手车之家.html'")
    print("4. Поместите файл в корень проекта")
    print("5. Запустите парсер снова")

if __name__ == "__main__":
    main() 