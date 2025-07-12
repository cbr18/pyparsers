#!/usr/bin/env python3
"""
Пример демонстрации логики нумерации sort_number
"""

def demonstrate_numbering_logic():
    """Демонстрирует логику нумерации sort_number"""
    
    print("=== Демонстрация логики нумерации sort_number ===\n")
    
    # Имитируем данные с парсера (отсортированные по новизне)
    raw_cars = [
        "Новая машина 1 (самая новая)",
        "Новая машина 2", 
        "Новая машина 3",
        "Средняя машина 1",
        "Средняя машина 2",
        "Старая машина 1",
        "Старая машина 2 (самая старая)"
    ]
    
    print("1. Данные с парсера (отсортированные по новизне):")
    for i, car in enumerate(raw_cars):
        print(f"   {i+1}. {car}")
    
    print("\n2. Применение sort_number (по убыванию):")
    total_cars = len(raw_cars)
    for i, car in enumerate(raw_cars):
        sort_number = total_cars - i
        print(f"   {car} → sort_number: {sort_number}")
    
    print("\n3. Результат сортировки по sort_number (по убыванию):")
    cars_with_numbers = []
    for i, car in enumerate(raw_cars):
        cars_with_numbers.append({
            'title': car,
            'sort_number': total_cars - i
        })
    
    # Сортировка по убыванию sort_number
    sorted_cars = sorted(cars_with_numbers, key=lambda x: x['sort_number'], reverse=True)
    
    for car in sorted_cars:
        print(f"   {car['title']} (sort_number: {car['sort_number']})")
    
    print("\n4. Логика инкрементального обновления:")
    
    # Существующие машины
    existing_cars = [
        {'title': 'Существующая машина 1', 'sort_number': 5, 'source': 'dongchedi'},
        {'title': 'Существующая машина 2', 'sort_number': 3, 'source': 'dongchedi'},
        {'title': 'Существующая машина 3', 'sort_number': 1, 'source': 'dongchedi'},
    ]
    
    print("   Существующие машины:")
    for car in existing_cars:
        print(f"     {car['title']} (sort_number: {car['sort_number']})")
    
    # Новые машины (найденные при инкрементальном обновлении)
    max_existing = max(car['sort_number'] for car in existing_cars)
    new_cars = [
        "Новая машина A",
        "Новая машина B", 
        "Новая машина C"
    ]
    
    print("\n   Новые машины (получают номера > max_existing):")
    for i, car in enumerate(new_cars):
        new_sort_number = max_existing + i + 1
        print(f"     {car} → sort_number: {new_sort_number}")
    
    print(f"\n   Максимальный существующий номер: {max_existing}")
    print(f"   Новые машины получают номера: {max_existing + 1}, {max_existing + 2}, {max_existing + 3}")
    
    print("\n5. Преимущества такой логики:")
    print("   ✅ Новые машины всегда имеют большие номера")
    print("   ✅ При сортировке по убыванию получаем самые новые первыми")
    print("   ✅ Инкрементальное обновление не нарушает порядок")
    print("   ✅ Можно легко получить топ-N самых новых машин")

if __name__ == "__main__":
    demonstrate_numbering_logic() 