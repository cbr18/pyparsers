#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для консолидации брендов:
- Объединяет дубликаты брендов
- Собирает все алиасы из дубликатов
- Добавляет модели в алиасы, если они используются как бренды
- Генерирует SQL файл для обновления таблицы brands
"""

import os
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Параметры подключения к БД
db_host = os.getenv('POSTGRES_HOST', 'localhost')
if db_host == 'postgres':
    db_host = 'localhost'

db_port = os.getenv('POSTGRES_PORT', '4827')
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
    """Нормализует название для сравнения"""
    if not name:
        return ""
    return name.lower().strip()


def parse_aliases(aliases_str: str) -> Set[str]:
    """Парсит строку алиасов в множество"""
    if not aliases_str:
        return set()
    return {a.strip() for a in aliases_str.split(',') if a.strip()}


def format_aliases(aliases_set: Set[str]) -> str:
    """Форматирует множество алиасов в строку"""
    return ','.join(sorted(aliases_set))


def get_all_brands(conn) -> List[Dict]:
    """Получает все бренды из БД"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, name, orig_name, aliases, created_at, updated_at
            FROM brands
            WHERE deleted_at IS NULL
            ORDER BY name, orig_name
        """)
        return cur.fetchall()


def get_all_cars(conn) -> List[Dict]:
    """Получает все автомобили из БД с группировкой по брендам и моделям"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT DISTINCT brand_name, series_name, mybrand_id
            FROM cars
            WHERE brand_name IS NOT NULL AND brand_name != ''
        """)
        return cur.fetchall()


def find_duplicate_groups(brands: List[Dict]) -> List[List[Dict]]:
    """Находит группы дубликатов брендов используя Union-Find алгоритм"""
    # Создаем индекс: нормализованное имя -> список брендов
    name_to_brands = defaultdict(list)
    orig_name_to_brands = defaultdict(list)
    brand_by_id = {b['id']: b for b in brands}
    
    for brand in brands:
        name_norm = normalize_name(brand.get('name') or '')
        orig_name_norm = normalize_name(brand.get('orig_name') or '')
        
        if name_norm:
            name_to_brands[name_norm].append(brand)
        if orig_name_norm:
            orig_name_to_brands[orig_name_norm].append(brand)
    
    # Union-Find структура для объединения связанных брендов
    parent = {b['id']: b['id'] for b in brands}
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Объединяем бренды с одинаковым name
    for name_norm, brand_list in name_to_brands.items():
        if len(brand_list) > 1:
            for i in range(len(brand_list) - 1):
                union(brand_list[i]['id'], brand_list[i+1]['id'])
    
    # Объединяем бренды с одинаковым orig_name
    for orig_name_norm, brand_list in orig_name_to_brands.items():
        if len(brand_list) > 1:
            for i in range(len(brand_list) - 1):
                union(brand_list[i]['id'], brand_list[i+1]['id'])
    
    # Объединяем бренды, где name одного совпадает с orig_name другого
    for name_norm, name_brands in name_to_brands.items():
        if name_norm in orig_name_to_brands:
            orig_brands = orig_name_to_brands[name_norm]
            for nb in name_brands:
                for ob in orig_brands:
                    union(nb['id'], ob['id'])
    
    # Группируем бренды по их корневому родителю
    groups = defaultdict(list)
    for brand in brands:
        root = find(brand['id'])
        groups[root].append(brand)
    
    # Возвращаем только группы с дубликатами (больше 1 бренда)
    duplicate_groups = [group for group in groups.values() if len(group) > 1]
    
    return duplicate_groups


def filter_invalid_aliases(aliases: Set[str], all_brand_names: Set[str], current_brand_name: str, current_brand_orig_name: str) -> Set[str]:
    """Фильтрует алиасы, убирая названия других брендов и служебные слова"""
    filtered = set()
    
    # Слова, которые нужно исключить (родительские компании, общие термины)
    excluded_patterns = [
        '集团',  # группа
        '高端品牌',  # премиум бренд
        '母公司',  # родительская компания
        'group',
        'parent',
        '高端',
    ]
    
    current_normalized = normalize_name(current_brand_name or '')
    current_orig_normalized = normalize_name(current_brand_orig_name or '')
    
    for alias in aliases:
        alias_normalized = normalize_name(alias)
        
        # Пропускаем пустые алиасы
        if not alias or not alias.strip():
            continue
        
        # Пропускаем, если это название другого бренда (но не текущего)
        if alias_normalized in all_brand_names:
            if alias_normalized != current_normalized and alias_normalized != current_orig_normalized:
                continue  # Это название другого бренда, пропускаем
        
        # Пропускаем алиасы, содержащие исключенные паттерны
        should_exclude = False
        for pattern in excluded_patterns:
            if pattern.lower() in alias_normalized:
                should_exclude = True
                break
        
        if not should_exclude:
            filtered.add(alias)
    
    return filtered


def consolidate_brand_group(brand_group: List[Dict], models_as_brands: Dict[str, Set[str]], all_brand_names: Set[str]) -> Dict:
    """Объединяет группу дубликатов в один бренд"""
    # Выбираем "лучший" бренд (с наибольшим количеством информации)
    best_brand = max(brand_group, key=lambda b: (
        len(b.get('name') or ''),
        len(b.get('orig_name') or ''),
        len(b.get('aliases') or ''),
        b.get('created_at', '').isoformat() if b.get('created_at') else ''
    ))
    
    # Собираем все уникальные значения
    all_names = set()
    all_orig_names = set()
    all_aliases = set()
    
    for brand in brand_group:
        if brand.get('name'):
            all_names.add(brand['name'])
            all_aliases.add(brand['name'])
        if brand.get('orig_name'):
            all_orig_names.add(brand['orig_name'])
            all_aliases.add(brand['orig_name'])
        if brand.get('aliases'):
            all_aliases.update(parse_aliases(brand['aliases']))
    
    # Выбираем основное name и orig_name
    main_name = best_brand.get('name') or (all_names.pop() if all_names else None)
    main_orig_name = best_brand.get('orig_name') or (all_orig_names.pop() if all_orig_names else None)
    
    # Добавляем все варианты в алиасы
    all_aliases.update(all_names)
    all_aliases.update(all_orig_names)
    
    # Убираем основные name и orig_name из алиасов (с учетом регистра и нормализации)
    main_name_norm = normalize_name(main_name or '')
    main_orig_name_norm = normalize_name(main_orig_name or '')
    
    aliases_to_remove = set()
    for alias in all_aliases:
        alias_norm = normalize_name(alias)
        if alias_norm == main_name_norm or alias_norm == main_orig_name_norm:
            aliases_to_remove.add(alias)
    
    all_aliases -= aliases_to_remove
    
    # Фильтруем алиасы - убираем названия других брендов и служебные слова
    all_aliases = filter_invalid_aliases(all_aliases, all_brand_names, main_name, main_orig_name)
    
    # Еще раз убираем основные имена (на случай, если они попали обратно через фильтрацию)
    aliases_to_remove_final = set()
    for alias in all_aliases:
        alias_norm = normalize_name(alias)
        if alias_norm == main_name_norm or alias_norm == main_orig_name_norm:
            aliases_to_remove_final.add(alias)
    all_aliases -= aliases_to_remove_final
    
    # Добавляем модели, которые используются как бренды
    brand_key = normalize_name(main_name or main_orig_name or '')
    if brand_key in models_as_brands:
        model_aliases = models_as_brands[brand_key]
        # Фильтруем модели тоже
        filtered_models = filter_invalid_aliases(model_aliases, all_brand_names, main_name, main_orig_name)
        # Убираем из моделей основные имена
        for model_alias in list(filtered_models):
            model_alias_norm = normalize_name(model_alias)
            if model_alias_norm == main_name_norm or model_alias_norm == main_orig_name_norm:
                filtered_models.discard(model_alias)
        all_aliases.update(filtered_models)
    
    # Сортируем алиасы для консистентности
    sorted_aliases = sorted(all_aliases)
    
    return {
        'id': best_brand['id'],
        'name': main_name,
        'orig_name': main_orig_name,
        'aliases': format_aliases(set(sorted_aliases)) if sorted_aliases else None,
        'duplicate_ids': [b['id'] for b in brand_group if b['id'] != best_brand['id']],
        'created_at': best_brand.get('created_at'),
        'updated_at': best_brand.get('updated_at')
    }


def find_models_as_brands(brands: List[Dict], cars: List[Dict]) -> Dict[str, Set[str]]:
    """Находит модели, которые используются как бренды"""
    brand_names = set()
    for brand in brands:
        if brand.get('name'):
            brand_names.add(normalize_name(brand['name']))
        if brand.get('orig_name'):
            brand_names.add(normalize_name(brand['orig_name']))
    
    models_as_brands = defaultdict(set)
    
    for car in cars:
        brand_name = normalize_name(car.get('brand_name') or '')
        series_name = normalize_name(car.get('series_name') or '')
        
        if series_name and series_name in brand_names:
            # Эта модель используется как бренд
            models_as_brands[brand_name].add(car.get('series_name'))
    
    return models_as_brands


def escape_sql_string(s: str) -> str:
    """Экранирует строку для SQL"""
    if not s:
        return ''
    return s.replace("'", "''")


def generate_sql(consolidated_brands: List[Dict], duplicate_ids: Set[str], output_file: str):
    """Генерирует SQL файл для обновления таблицы brands"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- SQL скрипт для консолидации брендов\n")
        f.write("-- Сгенерировано автоматически\n")
        f.write("-- ВНИМАНИЕ: Выполняйте этот скрипт на копии БД или после бэкапа!\n\n")
        
        f.write("BEGIN;\n\n")
        
        # Обновляем консолидированные бренды
        f.write("-- Обновление консолидированных брендов\n")
        for brand in consolidated_brands:
            name = brand['name']
            orig_name = brand['orig_name']
            aliases = brand['aliases']
            
            name_sql = f"'{escape_sql_string(name)}'" if name else 'NULL'
            orig_name_sql = f"'{escape_sql_string(orig_name)}'" if orig_name else 'NULL'
            aliases_sql = f"'{escape_sql_string(aliases)}'" if aliases else 'NULL'
            
            f.write(f"UPDATE brands\n")
            f.write(f"SET name = {name_sql},\n")
            f.write(f"    orig_name = {orig_name_sql},\n")
            f.write(f"    aliases = {aliases_sql},\n")
            f.write(f"    updated_at = NOW()\n")
            f.write(f"WHERE id = '{brand['id']}';\n\n")
        
        # Обновляем ссылки в таблице cars на консолидированные бренды
        f.write("-- Обновление ссылок в таблице cars\n")
        for brand in consolidated_brands:
            if brand['duplicate_ids']:
                duplicate_ids_str = "', '".join(brand['duplicate_ids'])
                f.write(f"UPDATE cars\n")
                f.write(f"SET mybrand_id = '{brand['id']}'\n")
                f.write(f"WHERE mybrand_id IN ('{duplicate_ids_str}');\n\n")
        
        # Удаляем дубликаты (soft delete)
        f.write("-- Удаление дубликатов (soft delete)\n")
        all_duplicate_ids = set()
        for brand in consolidated_brands:
            all_duplicate_ids.update(brand['duplicate_ids'])
        
        if all_duplicate_ids:
            duplicate_ids_list = list(all_duplicate_ids)
            # Разбиваем на батчи по 100 для больших списков
            batch_size = 100
            for i in range(0, len(duplicate_ids_list), batch_size):
                batch = duplicate_ids_list[i:i+batch_size]
                duplicate_ids_str = "', '".join(batch)
                f.write(f"UPDATE brands\n")
                f.write(f"SET deleted_at = NOW(),\n")
                f.write(f"    updated_at = NOW()\n")
                f.write(f"WHERE id IN ('{duplicate_ids_str}');\n\n")
        
        f.write("COMMIT;\n\n")
        f.write("-- Проверка результатов\n")
        f.write("SELECT COUNT(*) as total_brands FROM brands WHERE deleted_at IS NULL;\n")
        f.write("SELECT COUNT(*) as duplicate_brands FROM brands WHERE deleted_at IS NOT NULL;\n")
    
    # Генерируем также файл для заполнения таблицы с нуля
    insert_file = output_file.replace('.sql', '_insert.sql')
    with open(insert_file, 'w', encoding='utf-8') as f:
        f.write("-- SQL скрипт для заполнения таблицы brands с нуля\n")
        f.write("-- Сгенерировано автоматически\n")
        f.write("-- ВНИМАНИЕ: Этот скрипт очищает таблицу и заполняет её заново!\n\n")
        
        f.write("BEGIN;\n\n")
        
        f.write("-- Очистка таблицы (soft delete всех существующих)\n")
        f.write("UPDATE brands SET deleted_at = NOW(), updated_at = NOW() WHERE deleted_at IS NULL;\n\n")
        
        f.write("-- Вставка консолидированных брендов\n")
        f.write("INSERT INTO brands (id, name, orig_name, aliases, created_at, updated_at)\n")
        f.write("VALUES\n")
        
        values = []
        for brand in consolidated_brands:
            name = brand['name']
            orig_name = brand['orig_name']
            aliases = brand['aliases']
            
            name_sql = f"'{escape_sql_string(name)}'" if name else 'NULL'
            orig_name_sql = f"'{escape_sql_string(orig_name)}'" if orig_name else 'NULL'
            aliases_sql = f"'{escape_sql_string(aliases)}'" if aliases else 'NULL'
            
            values.append(f"    ('{brand['id']}', {name_sql}, {orig_name_sql}, {aliases_sql}, NOW(), NOW())")
        
        f.write(",\n".join(values))
        f.write(";\n\n")
        
        f.write("COMMIT;\n\n")
        f.write("-- Проверка результатов\n")
        f.write("SELECT COUNT(*) as total_brands FROM brands WHERE deleted_at IS NULL;\n")
        f.write("SELECT name, orig_name, aliases FROM brands WHERE deleted_at IS NULL ORDER BY name LIMIT 10;\n")
    
    return insert_file


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
        
        print("Поиск дубликатов...")
        duplicate_groups = find_duplicate_groups(brands)
        print(f"Найдено групп дубликатов: {len(duplicate_groups)}")
        
        print("Поиск моделей, используемых как бренды...")
        models_as_brands = find_models_as_brands(brands, cars)
        print(f"Найдено брендов с моделями в алиасах: {len(models_as_brands)}")
        
        # Создаем набор всех названий брендов для фильтрации
        all_brand_names = set()
        for brand in brands:
            if brand.get('name'):
                all_brand_names.add(normalize_name(brand['name']))
            if brand.get('orig_name'):
                all_brand_names.add(normalize_name(brand['orig_name']))
        
        print("Консолидация брендов...")
        consolidated_brands = []
        all_duplicate_ids = set()
        processed_ids = set()
        
        # Обрабатываем группы дубликатов
        for brand_group in duplicate_groups:
            consolidated = consolidate_brand_group(brand_group, models_as_brands, all_brand_names)
            consolidated_brands.append(consolidated)
            all_duplicate_ids.update(consolidated['duplicate_ids'])
            processed_ids.update(b['id'] for b in brand_group)
            print(f"  Объединена группа: {len(brand_group)} брендов -> 1 (ID: {consolidated['id']}, name: {consolidated.get('name') or consolidated.get('orig_name')})")
        
        # Обрабатываем оставшиеся бренды (без дубликатов)
        for brand in brands:
            if brand['id'] not in processed_ids:
                # Добавляем модели в алиасы, если нужно
                brand_key = normalize_name(brand.get('name') or brand.get('orig_name') or '')
                aliases = parse_aliases(brand.get('aliases') or '')
                
                if brand_key in models_as_brands:
                    aliases.update(models_as_brands[brand_key])
                
                # Фильтруем алиасы
                filtered_aliases = filter_invalid_aliases(
                    aliases, 
                    all_brand_names, 
                    brand.get('name'), 
                    brand.get('orig_name')
                )
                
                consolidated_brands.append({
                    'id': brand['id'],
                    'name': brand.get('name'),
                    'orig_name': brand.get('orig_name'),
                    'aliases': format_aliases(filtered_aliases) if filtered_aliases else None,
                    'duplicate_ids': [],
                    'created_at': brand.get('created_at'),
                    'updated_at': brand.get('updated_at')
                })
        
        print(f"\nВсего консолидировано брендов: {len(consolidated_brands)}")
        print(f"Будет удалено дубликатов: {len(all_duplicate_ids)}")
        
        print("\nГенерация SQL файлов...")
        output_file = 'consolidate_brands.sql'
        insert_file = generate_sql(consolidated_brands, all_duplicate_ids, output_file)
        print(f"SQL файл для обновления создан: {output_file}")
        print(f"SQL файл для заполнения с нуля создан: {insert_file}")
        
    finally:
        conn.close()
        print("\nПодключение закрыто.")


if __name__ == '__main__':
    main()

