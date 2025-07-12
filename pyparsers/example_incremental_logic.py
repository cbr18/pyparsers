#!/usr/bin/env python3
"""
Пример демонстрации исправленной логики инкрементального обновления
"""

def demonstrate_incremental_logic():
    """Демонстрирует логику инкрементального обновления"""
    
    print("=== Демонстрация исправленной логики инкрементального обновления ===\n")
    
    # Существующие машины
    existing_cars = [
        {'title': 'Существующая машина 1', 'sort_number': 5, 'source': 'dongchedi'},
        {'title': 'Существующая машина 2', 'sort_number': 3, 'source': 'dongchedi'},
        {'title': 'Существующая машина 3', 'sort_number': 1, 'source': 'dongchedi'},
    ]
    
    print("1. Существующие машины:")
    for car in existing_cars:
        print(f"   {car['title']} (sort_number: {car['sort_number']})")
    
    # Находим максимальный номер
    max_existing = max(car['sort_number'] for car in existing_cars)
    print(f"\n   Максимальный существующий номер: {max_existing}")
    
    # Новые машины (найденные при инкрементальном обновлении)
    # Данные с парсера (отсортированные по новизне)
    new_cars_raw = [
        "Новая машина A (самая новая)",
        "Новая машина B",
        "Новая машина C (самая старая из новых)"
    ]
    
    print(f"\n2. Новые машины с парсера (отсортированные по новизне):")
    for i, car in enumerate(new_cars_raw):
        print(f"   {i+1}. {car}")
    
    # Применяем исправленную логику нумерации
    next_sort_number = max_existing + 1
    total_new_cars = len(new_cars_raw)
    
    print(f"\n3. Применение исправленной логики нумерации:")
    print(f"   next_sort_number = {max_existing} + 1 = {next_sort_number}")
    print(f"   total_new_cars = {total_new_cars}")
    
    new_cars_with_numbers = []
    for i, car in enumerate(new_cars_raw):
        sort_number = next_sort_number + total_new_cars - i - 1
        new_cars_with_numbers.append({
            'title': car,
            'sort_number': sort_number,
            'source': 'dongchedi'
        })
        print(f"   {car} → sort_number: {sort_number}")
    
    print(f"\n4. Формула: sort_number = {next_sort_number} + {total_new_cars} - i - 1")
    for i, car in enumerate(new_cars_raw):
        sort_number = next_sort_number + total_new_cars - i - 1
        print(f"   i={i}: {next_sort_number} + {total_new_cars} - {i} - 1 = {sort_number}")
    
    print(f"\n5. Результат сортировки по sort_number (по убыванию):")
    all_cars = existing_cars + new_cars_with_numbers
    sorted_cars = sorted(all_cars, key=lambda x: x['sort_number'], reverse=True)
    
    for car in sorted_cars:
        print(f"   {car['title']} (sort_number: {car['sort_number']})")
    
    print(f"\n6. Преимущества исправленной логики:")
    print(f"   ✅ Новые машины получают номера больше существующих")
    print(f"   ✅ Среди новых машин самые новые получают большие номера")
    print(f"   ✅ При сортировке по убыванию получаем правильный порядок")
    print(f"   ✅ Инкрементальное обновление работает корректно")

def compare_old_vs_new_logic():
    """Сравнивает старую и новую логику"""
    
    print("\n=== Сравнение старой и новой логики ===\n")
    
    # Исходные данные
    existing_cars = [
        {'title': 'Существующая', 'sort_number': 5, 'source': 'dongchedi'},
    ]
    
    new_cars_raw = [
        "Новая машина A (самая новая)",
        "Новая машина B",
        "Новая машина C (самая старая из новых)"
    ]
    
    max_existing = 5
    next_sort_number = max_existing + 1  # 6
    
    print("Исходные данные:")
    print(f"   Существующие машины: sort_number = {max_existing}")
    print(f"   Новые машины: {len(new_cars_raw)} штук")
    print(f"   next_sort_number = {next_sort_number}")
    
    print(f"\nСТАРАЯ логика (по возрастанию):")
    for i, car in enumerate(new_cars_raw):
        old_sort_number = next_sort_number + i
        print(f"   {car} → sort_number: {old_sort_number}")
    
    print(f"\nНОВАЯ логика (по убыванию):")
    total_new_cars = len(new_cars_raw)
    for i, car in enumerate(new_cars_raw):
        new_sort_number = next_sort_number + total_new_cars - i - 1
        print(f"   {car} → sort_number: {new_sort_number}")
    
    print(f"\nРезультат сортировки по убыванию:")
    
    # Старая логика
    old_cars = [
        {'title': 'Существующая', 'sort_number': 5},
        {'title': 'Новая машина A (самая новая)', 'sort_number': 6},
        {'title': 'Новая машина B', 'sort_number': 7},
        {'title': 'Новая машина C (самая старая из новых)', 'sort_number': 8},
    ]
    
    # Новая логика
    new_cars = [
        {'title': 'Существующая', 'sort_number': 5},
        {'title': 'Новая машина A (самая новая)', 'sort_number': 8},
        {'title': 'Новая машина B', 'sort_number': 7},
        {'title': 'Новая машина C (самая старая из новых)', 'sort_number': 6},
    ]
    
    print(f"   СТАРАЯ: {[car['title'] for car in sorted(old_cars, key=lambda x: x['sort_number'], reverse=True)]}")
    print(f"   НОВАЯ:  {[car['title'] for car in sorted(new_cars, key=lambda x: x['sort_number'], reverse=True)]}")
    
    print(f"\nВывод: Новая логика правильно сортирует по новизне!")

if __name__ == "__main__":
    demonstrate_incremental_logic()
    compare_old_vs_new_logic() 