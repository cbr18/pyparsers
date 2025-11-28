#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый анализ размеров полей через docker exec
"""

import subprocess
import re

def analyze_field(field_name):
    """Анализирует одно поле"""
    query = f"""
SELECT 
    COUNT(*) as total,
    COUNT({field_name}) as non_null,
    MAX(LENGTH(COALESCE({field_name}::text, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE({field_name}::text, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE({field_name}::text, '')))::int as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE({field_name}::text, '')))::int as p99
FROM cars 
WHERE {field_name} IS NOT NULL;
"""
    
    try:
        result = subprocess.run(
            ['docker', 'exec', 'carcatch-postgres', 'psql', '-U', 'postgres', '-d', 'carsdb', '-t', '-A', '-F', '|'],
            input=query,
            text=True,
            capture_output=True,
            check=True
        )
        
        if result.stdout.strip():
            parts = result.stdout.strip().split('|')
            if len(parts) >= 6:
                return {
                    'total': int(parts[0]),
                    'non_null': int(parts[1]),
                    'max_len': int(parts[2]) if parts[2] else 0,
                    'avg_len': float(parts[3]) if parts[3] else 0,
                    'p95': int(parts[4]) if parts[4] else 0,
                    'p99': int(parts[5]) if parts[5] else 0,
                }
    except Exception as e:
        print(f"Ошибка для {field_name}: {e}")
    
    return None

def suggest_varchar_size(max_len, p99):
    """Предлагает размер VARCHAR"""
    if max_len == 0:
        return None
    
    # Используем p99 с запасом
    suggested = max(p99, max_len)
    
    # Округляем до стандартных размеров
    if suggested <= 10:
        return 10
    elif suggested <= 20:
        return 20
    elif suggested <= 50:
        return 50
    elif suggested <= 100:
        return 100
    elif suggested <= 255:
        return 255
    else:
        return None  # TEXT

# Основные поля для анализа
fields = [
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
    'seat_count', 'door_count', 'recycling_fee', 'customs_duty'
]

print("Анализ полей таблицы cars")
print("=" * 100)
print(f"{'Поле':<35} {'Макс':<8} {'P99':<8} {'Предложение':<20}")
print("-" * 100)

suggestions = []

for field in fields:
    stats = analyze_field(field)
    if stats and stats['non_null'] > 0:
        suggested = suggest_varchar_size(stats['max_len'], stats['p99'])
        if suggested and suggested < 255:
            suggestions.append({
                'field': field,
                'max': stats['max_len'],
                'p99': stats['p99'],
                'suggested': f'VARCHAR({suggested})' if suggested else 'TEXT'
            })
            print(f"{field:<35} {stats['max_len']:<8} {stats['p99']:<8} {suggestions[-1]['suggested']:<20}")

print("\n" + "=" * 100)
print(f"\nНайдено {len(suggestions)} полей для оптимизации\n")

if suggestions:
    print("SQL для миграции:")
    print("-" * 100)
    for s in suggestions:
        print(f"ALTER TABLE cars ALTER COLUMN {s['field']} TYPE {s['suggested']};")



