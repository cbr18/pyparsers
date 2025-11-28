#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для анализа размеров полей в БД и предложения оптимизации типов данных
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from collections import defaultdict

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


def analyze_field_sizes(table_name, fields_to_analyze):
    """Анализирует размеры полей в таблице"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    results = {}
    
    for field in fields_to_analyze:
        try:
            # Получаем статистику по полю
            query = f"""
                SELECT 
                    COUNT(*) as total_count,
                    COUNT({field}) as non_null_count,
                    MAX(LENGTH(COALESCE({field}::text, ''))) as max_length,
                    AVG(LENGTH(COALESCE({field}::text, ''))) as avg_length,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE({field}::text, ''))) as p95_length,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE({field}::text, ''))) as p99_length
                FROM {table_name}
                WHERE {field} IS NOT NULL
            """
            cursor.execute(query)
            row = cursor.fetchone()
            
            if row and row['non_null_count'] > 0:
                results[field] = {
                    'total': row['total_count'],
                    'non_null': row['non_null_count'],
                    'max_length': row['max_length'] or 0,
                    'avg_length': round(row['avg_length'] or 0, 2),
                    'p95_length': int(row['p95_length'] or 0),
                    'p99_length': int(row['p99_length'] or 0),
                }
            else:
                results[field] = {
                    'total': 0,
                    'non_null': 0,
                    'max_length': 0,
                    'avg_length': 0,
                    'p95_length': 0,
                    'p99_length': 0,
                }
        except Exception as e:
            print(f"Ошибка при анализе поля {field}: {e}")
            results[field] = None
    
    cursor.close()
    conn.close()
    return results


def suggest_type(current_type, max_length, p95_length, p99_length, field_name):
    """Предлагает оптимальный тип данных на основе статистики"""
    if current_type.startswith('VARCHAR'):
        # Извлекаем текущий размер
        current_size = 255
        if '(' in current_type:
            try:
                current_size = int(current_type.split('(')[1].split(')')[0])
            except:
                pass
        
        # Если поле пустое или очень короткое
        if max_length == 0:
            return None, "Поле пустое или NULL"
        
        # Определяем оптимальный размер
        # Используем p99 для безопасности, но округляем до стандартных значений
        suggested_size = p99_length
        
        # Округляем до стандартных размеров
        if suggested_size <= 10:
            suggested_size = 10
        elif suggested_size <= 20:
            suggested_size = 20
        elif suggested_size <= 50:
            suggested_size = 50
        elif suggested_size <= 100:
            suggested_size = 100
        elif suggested_size <= 255:
            suggested_size = 255
        else:
            # Если больше 255, оставляем TEXT
            return 'TEXT', f"Максимальная длина {max_length}, рекомендуется TEXT"
        
        # Если текущий размер больше предложенного, предлагаем уменьшить
        if current_size > suggested_size:
            return f'VARCHAR({suggested_size})', f"Текущий: {current_type}, макс: {max_length}, p99: {p99_length}"
        else:
            return None, f"Текущий размер оптимален"
    
    return None, "Не VARCHAR, пропускаем"


def main():
    print("Анализ размеров полей в таблице cars...")
    print("=" * 80)
    
    # Поля VARCHAR(255) для анализа
    varchar_fields = [
        'source', 'sku_id', 'car_name', 'brand_name', 'series_name', 'city',
        'car_source_city_name', 'shop_id', 'price', 'color', 'transmission',
        'fuel_type', 'engine_volume', 'engine_volume_ml', 'body_type',
        'drive_type', 'condition', 'transmission_type', 'gear_count',
        'engine_type', 'engine_code', 'cylinder_count', 'valve_count',
        'compression_ratio', 'turbo_type', 'battery_capacity', 'electric_range',
        'charging_time', 'fast_charge_time', 'charge_port_type', 'power',
        'torque', 'acceleration', 'max_speed', 'fuel_consumption',
        'emission_standard', 'length', 'width', 'height', 'wheelbase',
        'curb_weight', 'gross_weight', 'trunk_volume', 'fuel_tank_volume',
        'differential_type', 'front_suspension', 'rear_suspension',
        'front_brakes', 'rear_brakes', 'brake_system', 'wheel_size',
        'tire_size', 'wheel_type', 'tire_type', 'airbag_count', 'abs',
        'esp', 'tcs', 'hill_assist', 'blind_spot_monitor', 'lane_departure',
        'air_conditioning', 'climate_control', 'seat_heating',
        'seat_ventilation', 'seat_massage', 'steering_wheel_heating',
        'upholstery', 'sunroof', 'panoramic_roof', 'navigation',
        'audio_system', 'speakers_count', 'bluetooth', 'usb', 'aux',
        'headlight_type', 'fog_lights', 'led_lights', 'daytime_running',
        'inspection_date', 'interior_color', 'exterior_color',
        'seat_count', 'door_count', 'recycling_fee', 'customs_duty',
        'first_registration_time'
    ]
    
    results = analyze_field_sizes('cars', varchar_fields)
    
    # Выводим результаты
    suggestions = []
    
    print("\nПоля, требующие оптимизации:\n")
    print(f"{'Поле':<35} {'Текущий тип':<20} {'Макс. длина':<12} {'P95':<8} {'P99':<8} {'Предложение':<20}")
    print("-" * 120)
    
    for field, stats in sorted(results.items()):
        if stats is None:
            continue
        
        if stats['non_null'] == 0:
            continue
        
        current_type = 'VARCHAR(255)'  # Предполагаем, что все VARCHAR(255)
        suggested_type, reason = suggest_type(
            current_type,
            stats['max_length'],
            stats['p95_length'],
            stats['p99_length'],
            field
        )
        
        if suggested_type and suggested_type != current_type:
            suggestions.append({
                'field': field,
                'current': current_type,
                'suggested': suggested_type,
                'max_length': stats['max_length'],
                'p95': stats['p95_length'],
                'p99': stats['p99_length'],
                'reason': reason
            })
            print(f"{field:<35} {current_type:<20} {stats['max_length']:<12} {stats['p95_length']:<8} {stats['p99_length']:<8} {suggested_type:<20}")
    
    print("\n" + "=" * 80)
    print(f"\nНайдено {len(suggestions)} полей для оптимизации\n")
    
    # Выводим SQL для миграции
    if suggestions:
        print("SQL для миграции:")
        print("-" * 80)
        for item in suggestions:
            print(f"ALTER TABLE cars ALTER COLUMN {item['field']} TYPE {item['suggested']};")
    
    # Анализ полей brands
    print("\n\n" + "=" * 80)
    print("Анализ размеров полей в таблице brands...")
    print("=" * 80)
    
    brands_fields = ['name', 'orig_name']
    brands_results = analyze_field_sizes('brands', brands_fields)
    
    print("\nПоля, требующие оптимизации:\n")
    print(f"{'Поле':<35} {'Текущий тип':<20} {'Макс. длина':<12} {'P95':<8} {'P99':<8} {'Предложение':<20}")
    print("-" * 120)
    
    brands_suggestions = []
    for field, stats in sorted(brands_results.items()):
        if stats is None or stats['non_null'] == 0:
            continue
        
        current_type = 'VARCHAR(255)'
        suggested_type, reason = suggest_type(
            current_type,
            stats['max_length'],
            stats['p95_length'],
            stats['p99_length'],
            field
        )
        
        if suggested_type and suggested_type != current_type:
            brands_suggestions.append({
                'field': field,
                'current': current_type,
                'suggested': suggested_type,
                'max_length': stats['max_length'],
                'p95': stats['p95_length'],
                'p99': stats['p99_length'],
            })
            print(f"{field:<35} {current_type:<20} {stats['max_length']:<12} {stats['p95_length']:<8} {stats['p99_length']:<8} {suggested_type:<20}")
    
    if brands_suggestions:
        print("\nSQL для миграции brands:")
        print("-" * 80)
        for item in brands_suggestions:
            print(f"ALTER TABLE brands ALTER COLUMN {item['field']} TYPE {item['suggested']};")


if __name__ == '__main__':
    main()



