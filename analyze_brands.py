#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для анализа брендов в базе данных:
- Поиск дубликатов брендов
- Проверка, когда название модели используется как бренд
- Статистика по различным параметрам
"""

import os
import sys
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Параметры подключения к БД
# Если POSTGRES_HOST = "postgres" (Docker service name), используем localhost для подключения с хоста
db_host = os.getenv('POSTGRES_HOST', 'localhost')
if db_host == 'postgres':
    db_host = 'localhost'

db_port = os.getenv('POSTGRES_PORT', '4827')
# Если порт не указан или стандартный 5432, используем 4827 (маппинг из docker-compose)
if db_port == '5432' or not db_port:
    db_port = '4827'

DB_CONFIG = {
    'host': db_host,
    'port': db_port,
    'database': os.getenv('POSTGRES_DB', 'carsdb'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
}


def get_db_connection():
    """Создает подключение к базе данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        print(f"Параметры: host={DB_CONFIG['host']}, port={DB_CONFIG['port']}, db={DB_CONFIG['database']}, user={DB_CONFIG['user']}")
        sys.exit(1)


def normalize_name(name: str) -> str:
    """Нормализует название для сравнения (lowercase, убирает пробелы)"""
    if not name:
        return ""
    return name.lower().strip()


def get_all_brands(conn) -> List[Dict]:
    """Получает все бренды из БД"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, name, orig_name, aliases, created_at, updated_at, deleted_at
            FROM brands
            WHERE deleted_at IS NULL
            ORDER BY name, orig_name
        """)
        return cur.fetchall()


def get_all_cars(conn) -> List[Dict]:
    """Получает все автомобили из БД"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT brand_name, series_name, brand_id, source, COUNT(*) as car_count
            FROM cars
            GROUP BY brand_name, series_name, brand_id, source
        """)
        return cur.fetchall()


def find_duplicate_brands(brands: List[Dict]) -> Dict[str, List[Dict]]:
    """Находит дубликаты брендов по различным критериям"""
    duplicates = defaultdict(list)
    
    # Группируем по нормализованному имени
    by_normalized_name = defaultdict(list)
    by_normalized_orig_name = defaultdict(list)
    
    for brand in brands:
        name_norm = normalize_name(brand.get('name') or '')
        orig_name_norm = normalize_name(brand.get('orig_name') or '')
        
        if name_norm:
            by_normalized_name[name_norm].append(brand)
        if orig_name_norm:
            by_normalized_orig_name[orig_name_norm].append(brand)
    
    # Дубликаты по name
    for norm_name, brand_list in by_normalized_name.items():
        if len(brand_list) > 1:
            duplicates[f"По name: '{norm_name}'"] = brand_list
    
    # Дубликаты по orig_name
    for norm_name, brand_list in by_normalized_orig_name.items():
        if len(brand_list) > 1:
            duplicates[f"По orig_name: '{norm_name}'"] = brand_list
    
    # Пересечения: когда name одного бренда совпадает с orig_name другого
    name_to_brands = {normalize_name(b.get('name') or ''): b for b in brands if b.get('name')}
    orig_name_to_brands = {normalize_name(b.get('orig_name') or ''): b for b in brands if b.get('orig_name')}
    
    for name_norm, brand in name_to_brands.items():
        if name_norm in orig_name_to_brands and orig_name_to_brands[name_norm]['id'] != brand['id']:
            key = f"Пересечение name/orig_name: '{name_norm}'"
            if key not in duplicates:
                duplicates[key] = [brand, orig_name_to_brands[name_norm]]
    
    return duplicates


def find_brand_as_model(brands: List[Dict], cars: List[Dict]) -> List[Dict]:
    """Находит случаи, когда название бренда используется как название модели"""
    brand_names = set()
    brand_orig_names = set()
    
    for brand in brands:
        if brand.get('name'):
            brand_names.add(normalize_name(brand['name']))
        if brand.get('orig_name'):
            brand_orig_names.add(normalize_name(brand['orig_name']))
    
    # Все уникальные названия брендов (объединение)
    all_brand_names = brand_names | brand_orig_names
    
    # Проверяем, какие из них встречаются как series_name
    brand_as_model = []
    series_name_counter = Counter()
    
    for car in cars:
        series_name = normalize_name(car.get('series_name') or '')
        if series_name and series_name in all_brand_names:
            series_name_counter[series_name] += car.get('car_count', 0)
    
    # Формируем список проблемных брендов
    for brand_name, count in series_name_counter.items():
        # Находим соответствующий бренд
        matching_brands = [b for b in brands 
                          if normalize_name(b.get('name') or '') == brand_name 
                          or normalize_name(b.get('orig_name') or '') == brand_name]
        
        for brand in matching_brands:
            brand_as_model.append({
                'brand': brand,
                'brand_name': brand_name,
                'used_as_model_count': count,
                'examples': [c for c in cars if normalize_name(c.get('series_name') or '') == brand_name][:5]
            })
    
    return brand_as_model


def get_brand_statistics(conn, brands: List[Dict], cars: List[Dict]) -> Dict:
    """Собирает статистику по брендам"""
    stats = {
        'total_brands': len(brands),
        'brands_with_name': len([b for b in brands if b.get('name')]),
        'brands_with_orig_name': len([b for b in brands if b.get('orig_name')]),
        'brands_with_aliases': len([b for b in brands if b.get('aliases')]),
        'brands_without_name': len([b for b in brands if not b.get('name')]),
        'brands_without_orig_name': len([b for b in brands if not b.get('orig_name')]),
    }
    
    # Статистика по использованию брендов в автомобилях
    brand_usage = Counter()
    brand_series_count = defaultdict(set)
    
    for car in cars:
        brand_name = car.get('brand_name') or ''
        series_name = car.get('series_name') or ''
        car_count = car.get('car_count', 0)
        
        if brand_name:
            brand_usage[normalize_name(brand_name)] += car_count
            if series_name:
                brand_series_count[normalize_name(brand_name)].add(normalize_name(series_name))
    
    stats['brands_used_in_cars'] = len(brand_usage)
    stats['brands_not_used_in_cars'] = stats['total_brands'] - stats['brands_used_in_cars']
    stats['top_10_brands_by_cars'] = brand_usage.most_common(10)
    stats['brands_with_most_series'] = sorted(
        [(name, len(series)) for name, series in brand_series_count.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Статистика по источникам
    source_stats = Counter()
    for car in cars:
        source = car.get('source') or 'unknown'
        source_stats[source] += car.get('car_count', 0)
    stats['cars_by_source'] = dict(source_stats)
    
    return stats


def print_report(brands: List[Dict], cars: List[Dict], duplicates: Dict, brand_as_model: List[Dict], stats: Dict):
    """Выводит отчет"""
    print("=" * 80)
    print("СТАТИСТИКА ПО БРЕНДАМ В БАЗЕ ДАННЫХ")
    print("=" * 80)
    print()
    
    # Общая статистика
    print("📊 ОБЩАЯ СТАТИСТИКА")
    print("-" * 80)
    print(f"Всего брендов в БД: {stats['total_brands']}")
    print(f"  - С названием (name): {stats['brands_with_name']}")
    print(f"  - С оригинальным названием (orig_name): {stats['brands_with_orig_name']}")
    print(f"  - С алиасами: {stats['brands_with_aliases']}")
    print(f"  - Без названия: {stats['brands_without_name']}")
    print(f"  - Без оригинального названия: {stats['brands_without_orig_name']}")
    print()
    print(f"Брендов используется в автомобилях: {stats['brands_used_in_cars']}")
    print(f"Брендов НЕ используется в автомобилях: {stats['brands_not_used_in_cars']}")
    print()
    
    # Дубликаты
    print("🔍 ДУБЛИКАТЫ БРЕНДОВ")
    print("-" * 80)
    if duplicates:
        print(f"Найдено групп дубликатов: {len(duplicates)}")
        print()
        for key, brand_list in duplicates.items():
            print(f"{key}:")
            for brand in brand_list:
                print(f"  - ID: {brand['id']}")
                print(f"    name: {brand.get('name') or '(пусто)'}")
                print(f"    orig_name: {brand.get('orig_name') or '(пусто)'}")
                print(f"    aliases: {brand.get('aliases') or '(пусто)'}")
                print()
    else:
        print("Дубликаты не найдены ✓")
    print()
    
    # Бренды, используемые как модели
    print("⚠️  БРЕНДЫ, ИСПОЛЬЗУЕМЫЕ КАК НАЗВАНИЯ МОДЕЛЕЙ")
    print("-" * 80)
    if brand_as_model:
        print(f"Найдено проблемных брендов: {len(brand_as_model)}")
        print()
        for item in brand_as_model:
            brand = item['brand']
            print(f"Бренд: '{item['brand_name']}'")
            print(f"  ID: {brand['id']}")
            print(f"  name: {brand.get('name') or '(пусто)'}")
            print(f"  orig_name: {brand.get('orig_name') or '(пусто)'}")
            print(f"  Используется как модель в {item['used_as_model_count']} автомобилях")
            if item['examples']:
                print(f"  Примеры:")
                for ex in item['examples'][:3]:
                    print(f"    - {ex.get('brand_name')} {ex.get('series_name')} (source: {ex.get('source')}, count: {ex.get('car_count')})")
            print()
    else:
        print("Проблем не найдено ✓")
    print()
    
    # Топ брендов
    print("🏆 ТОП-10 БРЕНДОВ ПО КОЛИЧЕСТВУ АВТОМОБИЛЕЙ")
    print("-" * 80)
    for i, (brand_name, count) in enumerate(stats['top_10_brands_by_cars'], 1):
        print(f"{i:2}. {brand_name}: {count} автомобилей")
    print()
    
    # Бренды с наибольшим количеством серий
    print("📋 ТОП-10 БРЕНДОВ ПО КОЛИЧЕСТВУ СЕРИЙ/МОДЕЛЕЙ")
    print("-" * 80)
    for i, (brand_name, series_count) in enumerate(stats['brands_with_most_series'], 1):
        print(f"{i:2}. {brand_name}: {series_count} серий")
    print()
    
    # Статистика по источникам
    print("📦 АВТОМОБИЛИ ПО ИСТОЧНИКАМ")
    print("-" * 80)
    for source, count in sorted(stats['cars_by_source'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count} автомобилей")
    print()
    
    # Бренды без использования
    if stats['brands_not_used_in_cars'] > 0:
        print("❌ БРЕНДЫ, КОТОРЫЕ НЕ ИСПОЛЬЗУЮТСЯ В АВТОМОБИЛЯХ")
        print("-" * 80)
        used_brand_names = {normalize_name(c.get('brand_name') or '') for c in cars if c.get('brand_name')}
        unused_brands = []
        for brand in brands:
            name_norm = normalize_name(brand.get('name') or '')
            orig_name_norm = normalize_name(brand.get('orig_name') or '')
            if name_norm not in used_brand_names and orig_name_norm not in used_brand_names:
                unused_brands.append(brand)
        
        for brand in unused_brands[:20]:  # Показываем первые 20
            print(f"  - ID: {brand['id']}, name: {brand.get('name') or '(пусто)'}, orig_name: {brand.get('orig_name') or '(пусто)'}")
        if len(unused_brands) > 20:
            print(f"  ... и еще {len(unused_brands) - 20} брендов")
        print()
    
    print("=" * 80)


def save_detailed_report(brands: List[Dict], cars: List[Dict], duplicates: Dict, 
                         brand_as_model: List[Dict], stats: Dict, filename: str = 'brand_analysis_report.txt'):
    """Сохраняет детальный отчет в файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ДЕТАЛЬНЫЙ ОТЧЕТ ПО АНАЛИЗУ БРЕНДОВ\n")
        f.write("=" * 80 + "\n\n")
        
        # Общая статистика
        f.write("ОБЩАЯ СТАТИСТИКА\n")
        f.write("-" * 80 + "\n")
        f.write(f"Всего брендов в БД: {stats['total_brands']}\n")
        f.write(f"  - С названием (name): {stats['brands_with_name']}\n")
        f.write(f"  - С оригинальным названием (orig_name): {stats['brands_with_orig_name']}\n")
        f.write(f"  - С алиасами: {stats['brands_with_aliases']}\n")
        f.write(f"  - Без названия: {stats['brands_without_name']}\n")
        f.write(f"  - Без оригинального названия: {stats['brands_without_orig_name']}\n\n")
        f.write(f"Брендов используется в автомобилях: {stats['brands_used_in_cars']}\n")
        f.write(f"Брендов НЕ используется в автомобилях: {stats['brands_not_used_in_cars']}\n\n")
        
        # Дубликаты
        f.write("ДУБЛИКАТЫ БРЕНДОВ\n")
        f.write("-" * 80 + "\n")
        if duplicates:
            f.write(f"Найдено групп дубликатов: {len(duplicates)}\n\n")
            for key, brand_list in duplicates.items():
                f.write(f"{key}:\n")
                for brand in brand_list:
                    f.write(f"  - ID: {brand['id']}\n")
                    f.write(f"    name: {brand.get('name') or '(пусто)'}\n")
                    f.write(f"    orig_name: {brand.get('orig_name') or '(пусто)'}\n")
                    f.write(f"    aliases: {brand.get('aliases') or '(пусто)'}\n")
                    f.write(f"    created_at: {brand.get('created_at')}\n")
                    f.write(f"    updated_at: {brand.get('updated_at')}\n\n")
        else:
            f.write("Дубликаты не найдены ✓\n\n")
        
        # Бренды как модели
        f.write("БРЕНДЫ, ИСПОЛЬЗУЕМЫЕ КАК НАЗВАНИЯ МОДЕЛЕЙ\n")
        f.write("-" * 80 + "\n")
        if brand_as_model:
            f.write(f"Найдено проблемных брендов: {len(brand_as_model)}\n\n")
            for item in brand_as_model:
                brand = item['brand']
                f.write(f"Бренд: '{item['brand_name']}'\n")
                f.write(f"  ID: {brand['id']}\n")
                f.write(f"  name: {brand.get('name') or '(пусто)'}\n")
                f.write(f"  orig_name: {brand.get('orig_name') or '(пусто)'}\n")
                f.write(f"  Используется как модель в {item['used_as_model_count']} автомобилях\n")
                if item['examples']:
                    f.write(f"  Примеры:\n")
                    for ex in item['examples']:
                        f.write(f"    - {ex.get('brand_name')} {ex.get('series_name')} (source: {ex.get('source')}, count: {ex.get('car_count')})\n")
                f.write("\n")
        else:
            f.write("Проблем не найдено ✓\n\n")
        
        # Топ брендов
        f.write("ТОП-10 БРЕНДОВ ПО КОЛИЧЕСТВУ АВТОМОБИЛЕЙ\n")
        f.write("-" * 80 + "\n")
        for i, (brand_name, count) in enumerate(stats['top_10_brands_by_cars'], 1):
            f.write(f"{i:2}. {brand_name}: {count} автомобилей\n")
        f.write("\n")
        
        # Бренды с наибольшим количеством серий
        f.write("ТОП-10 БРЕНДОВ ПО КОЛИЧЕСТВУ СЕРИЙ/МОДЕЛЕЙ\n")
        f.write("-" * 80 + "\n")
        for i, (brand_name, series_count) in enumerate(stats['brands_with_most_series'], 1):
            f.write(f"{i:2}. {brand_name}: {series_count} серий\n")
        f.write("\n")
        
        # Статистика по источникам
        f.write("АВТОМОБИЛИ ПО ИСТОЧНИКАМ\n")
        f.write("-" * 80 + "\n")
        for source, count in sorted(stats['cars_by_source'].items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {source}: {count} автомобилей\n")
        f.write("\n")
        
        # Все бренды
        f.write("ВСЕ БРЕНДЫ В БД\n")
        f.write("-" * 80 + "\n")
        for brand in sorted(brands, key=lambda x: (x.get('name') or x.get('orig_name') or '')):
            f.write(f"ID: {brand['id']}\n")
            f.write(f"  name: {brand.get('name') or '(пусто)'}\n")
            f.write(f"  orig_name: {brand.get('orig_name') or '(пусто)'}\n")
            f.write(f"  aliases: {brand.get('aliases') or '(пусто)'}\n")
            f.write(f"  created_at: {brand.get('created_at')}\n")
            f.write(f"  updated_at: {brand.get('updated_at')}\n\n")
    
    print(f"\nДетальный отчет сохранен в файл: {filename}")


def main():
    """Основная функция"""
    print("Подключение к базе данных...")
    conn = get_db_connection()
    
    try:
        print("Загрузка данных из БД...")
        brands = get_all_brands(conn)
        cars = get_all_cars(conn)
        
        print(f"Загружено брендов: {len(brands)}")
        print(f"Загружено групп автомобилей: {len(cars)}")
        print()
        
        print("Анализ данных...")
        duplicates = find_duplicate_brands(brands)
        brand_as_model = find_brand_as_model(brands, cars)
        stats = get_brand_statistics(conn, brands, cars)
        
        print()
        print_report(brands, cars, duplicates, brand_as_model, stats)
        
        # Сохраняем детальный отчет
        save_detailed_report(brands, cars, duplicates, brand_as_model, stats)
        
    finally:
        conn.close()
        print("\nПодключение закрыто.")


if __name__ == '__main__':
    main()

