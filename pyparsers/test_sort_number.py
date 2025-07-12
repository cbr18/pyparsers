#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы системы sort_number
"""

import requests
import json
from typing import List, Dict

def test_sort_number_system():
    """Тестирует систему нумерации sort_number"""
    
    base_url = "http://localhost:8000"
    
    print("=== Тестирование системы sort_number ===\n")
    
    # 1. Тест обычного парсинга (должен начинать с 1)
    print("1. Тест обычного парсинга dongchedi:")
    try:
        response = requests.get(f"{base_url}/cars/dongchedi")
        if response.status_code == 200:
            data = response.json()
            cars = data['data']['search_sh_sku_info_list']
            print(f"   Найдено машин: {len(cars)}")
            if cars:
                print(f"   Первая машина sort_number: {cars[0].get('sort_number')}")
                print(f"   Последняя машина sort_number: {cars[-1].get('sort_number')}")
                print(f"   Источник: {cars[0].get('source')}")
        else:
            print(f"   Ошибка: {response.status_code}")
    except Exception as e:
        print(f"   Ошибка подключения: {e}")
    
    print("\n2. Тест обычного парсинга che168:")
    try:
        response = requests.get(f"{base_url}/cars/che168")
        if response.status_code == 200:
            data = response.json()
            cars = data['data']['search_sh_sku_info_list']
            print(f"   Найдено машин: {len(cars)}")
            if cars:
                print(f"   Первая машина sort_number: {cars[0].get('sort_number')}")
                print(f"   Последняя машина sort_number: {cars[-1].get('sort_number')}")
                print(f"   Источник: {cars[0].get('source')}")
        else:
            print(f"   Ошибка: {response.status_code}")
    except Exception as e:
        print(f"   Ошибка подключения: {e}")
    
    # 2. Тест инкрементального обновления
    print("\n3. Тест инкрементального обновления:")
    
    # Создаем тестовые существующие машины
    existing_cars = [
        {
            'car_id': 12345,
            'sort_number': 5,
            'source': 'dongchedi'
        },
        {
            'car_id': 67890,
            'sort_number': 10,
            'source': 'dongchedi'
        }
    ]
    
    try:
        response = requests.post(
            f"{base_url}/cars/dongchedi/incremental",
            json=existing_cars
        )
        if response.status_code == 200:
            data = response.json()
            new_cars = data['data']['search_sh_sku_info_list']
            print(f"   Найдено новых машин: {len(new_cars)}")
            if new_cars:
                print(f"   Первая новая машина sort_number: {new_cars[0].get('sort_number')}")
                print(f"   Ожидаемый номер: 11 (max из существующих + 1)")
        else:
            print(f"   Ошибка: {response.status_code}")
    except Exception as e:
        print(f"   Ошибка подключения: {e}")
    
    # 3. Тест полного парсинга
    print("\n4. Тест полного парсинга dongchedi (может занять время):")
    try:
        response = requests.get(f"{base_url}/cars/dongchedi/all")
        if response.status_code == 200:
            data = response.json()
            cars = data['data']['search_sh_sku_info_list']
            print(f"   Найдено машин: {len(cars)}")
            if cars:
                print(f"   Первая машина sort_number: {cars[0].get('sort_number')}")
                print(f"   Последняя машина sort_number: {cars[-1].get('sort_number')}")
                print(f"   Источник: {cars[0].get('source')}")
        else:
            print(f"   Ошибка: {response.status_code}")
    except Exception as e:
        print(f"   Ошибка подключения: {e}")

def test_sorting_example():
    """Пример сортировки машин по sort_number"""
    print("\n=== Пример сортировки ===")
    
    # Имитируем данные с разных источников (большие номера = новые машины)
    sample_cars = [
        {'title': 'Car 1 (новая)', 'sort_number': 5, 'source': 'dongchedi'},
        {'title': 'Car 2 (старая)', 'sort_number': 1, 'source': 'che168'},
        {'title': 'Car 3 (средняя)', 'sort_number': 3, 'source': 'dongchedi'},
        {'title': 'Car 4 (средняя)', 'sort_number': 2, 'source': 'che168'},
        {'title': 'Car 5 (новая)', 'sort_number': 4, 'source': 'dongchedi'},
    ]
    
    print("Исходный порядок:")
    for car in sample_cars:
        print(f"  {car['title']} - sort_number: {car['sort_number']}, source: {car['source']}")
    
    # Сортировка по новизне (sort_number по убыванию - новые первыми)
    sorted_cars = sorted(sample_cars, key=lambda x: x['sort_number'], reverse=True)
    
    print("\nСортировка по новизне (sort_number по убыванию - новые первыми):")
    for car in sorted_cars:
        print(f"  {car['title']} - sort_number: {car['sort_number']}, source: {car['source']}")
    
    # Сортировка по источнику и новизне
    sorted_by_source = sorted(sample_cars, key=lambda x: (x['source'], -x['sort_number']))
    
    print("\nСортировка по источнику и новизне:")
    for car in sorted_by_source:
        print(f"  {car['title']} - sort_number: {car['sort_number']}, source: {car['source']}")
    
    print("\nОбъяснение логики:")
    print("- Большие sort_number = новые машины (первые в отсортированном списке)")
    print("- Малые sort_number = старые машины (последние в отсортированном списке)")
    print("- При сортировке по убыванию получаем самые новые машины первыми")

if __name__ == "__main__":
    test_sort_number_system()
    test_sorting_example() 