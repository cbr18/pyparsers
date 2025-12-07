#!/usr/bin/env python3
"""
Скрипт для анализа статистики по is_banned из логов
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

def analyze_logs(log_file_path):
    """Анализирует логи и собирает статистику по is_banned"""
    
    stats = {
        'total_parsed': 0,
        'banned_detected': 0,
        'banned_with_data': 0,
        'banned_lost': 0,
        'banned_in_params': 0,
        'banned_in_carinfo': 0,
        'no_significant_fields': 0,
        'banned_no_significant': 0,
        'car_ids': defaultdict(lambda: {
            'banned': False,
            'has_significant': False,
            'lost': False,
            'where_banned': None
        })
    }
    
    if not Path(log_file_path).exists():
        print(f"Файл {log_file_path} не найден")
        return stats
    
    with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Ищем записи о парсинге
            if '[API] Парсинг car_id:' in line:
                match = re.search(r'car_id:\s*(\d+)', line)
                if match:
                    car_id = match.group(1)
                    stats['total_parsed'] += 1
                    stats['car_ids'][car_id] = {
                        'banned': False,
                        'has_significant': False,
                        'lost': False,
                        'where_banned': None
                    }
            
            # Ищем записи о блокировке в getparamtypeitems
            if '[API] getparamtypeitems вернул' in line and ('403' in line or '514' in line):
                match = re.search(r'car_id=(\d+)', line)
                if match:
                    car_id = match.group(1)
                    stats['banned_detected'] += 1
                    stats['banned_in_params'] += 1
                    stats['car_ids'][car_id]['banned'] = True
                    stats['car_ids'][car_id]['where_banned'] = 'params_api'
            
            # Ищем записи о блокировке в getcarinfo
            if '[API] getcarinfo вернул' in line and ('403' in line or '514' in line):
                match = re.search(r'car_id=(\d+)', line)
                if match:
                    car_id = match.group(1)
                    stats['banned_detected'] += 1
                    stats['banned_in_carinfo'] += 1
                    if stats['car_ids'][car_id]['where_banned'] is None:
                        stats['car_ids'][car_id]['where_banned'] = 'carinfo_api'
                    stats['car_ids'][car_id]['banned'] = True
            
            # Ищем записи о потере is_banned
            if 'ПОТЕРЯ is_banned' in line:
                match = re.search(r'car_id=(\d+)', line)
                if match:
                    car_id = match.group(1)
                    stats['banned_lost'] += 1
                    stats['banned_no_significant'] += 1
                    stats['car_ids'][car_id]['lost'] = True
            
            # Ищем записи о том, что нет значимых полей
            if '[API] Нет значимых полей' in line:
                match = re.search(r'car_id=(\d+)', line)
                if match:
                    car_id = match.group(1)
                    stats['no_significant_fields'] += 1
                    stats['car_ids'][car_id]['has_significant'] = False
            
            # Ищем успешные парсинги с is_banned (когда fallback сработал)
            if '[API] Источник заблокирован' in line and 'fallback успешно получил' in line:
                match = re.search(r'car_id=(\d+)', line)
                if match:
                    car_id = match.group(1)
                    stats['banned_with_data'] += 1
    
    return stats

def print_stats(stats):
    """Выводит статистику"""
    print("=" * 80)
    print("СТАТИСТИКА ПО is_banned")
    print("=" * 80)
    print()
    
    print(f"Всего попыток парсинга: {stats['total_parsed']}")
    print(f"Обнаружено блокировок: {stats['banned_detected']}")
    print()
    
    if stats['total_parsed'] > 0:
        ban_rate = (stats['banned_detected'] / stats['total_parsed']) * 100
        print(f"Процент блокировок: {ban_rate:.2f}%")
        print()
    
    print("Распределение блокировок:")
    print(f"  - В getparamtypeitems: {stats['banned_in_params']}")
    print(f"  - В getcarinfo: {stats['banned_in_carinfo']}")
    print()
    
    print("Результаты блокировок:")
    print(f"  - Блокировка + данные получены: {stats['banned_with_data']}")
    print(f"  - Блокировка + is_banned потерян: {stats['banned_lost']}")
    print()
    
    if stats['banned_detected'] > 0:
        lost_rate = (stats['banned_lost'] / stats['banned_detected']) * 100
        print(f"Процент потерь is_banned: {lost_rate:.2f}%")
        print()
    
    print("Проблемные случаи:")
    print(f"  - Нет значимых полей (всего): {stats['no_significant_fields']}")
    print(f"  - Блокировка + нет значимых полей: {stats['banned_no_significant']}")
    print()
    
    # Анализ по car_id
    lost_cars = [car_id for car_id, data in stats['car_ids'].items() if data['lost']]
    banned_cars = [car_id for car_id, data in stats['car_ids'].items() if data['banned']]
    unique_banned = len(set(banned_cars))
    unique_lost = len(set(lost_cars))
    
    print(f"Уникальные car_id:")
    print(f"  - С блокировкой: {unique_banned}")
    print(f"  - С потерей is_banned: {unique_lost}")
    if unique_banned > 0:
        unique_lost_rate = (unique_lost / unique_banned) * 100
        print(f"  - Процент потерь (уникальные): {unique_lost_rate:.2f}%")
    print()
    
    if lost_cars:
        print(f"Примеры car_id с потерянным is_banned (первые 10): {list(set(lost_cars))[:10]}")
        print()
    
    if stats['banned_detected'] > 0:
        print("=" * 80)
        print("ВЫВОДЫ:")
        print("=" * 80)
        if stats['banned_lost'] > 0:
            print(f"⚠️  Обнаружено {stats['banned_lost']} случаев потери is_banned")
            print(f"   Это {lost_rate:.2f}% от всех блокировок")
            print()
            print("Проблема: Когда бан + нет significant полей → return None → is_banned теряется")
            print("Решение: Добавить is_banned на уровень CarDetailResponse")
        else:
            print("✅ Потерь is_banned не обнаружено в логах")
        print()

if __name__ == '__main__':
    log_file = sys.argv[1] if len(sys.argv) > 1 else '/home/alex/CarsParser/test_results/output.log'
    
    print(f"Анализ логов из: {log_file}")
    print()
    
    stats = analyze_logs(log_file)
    print_stats(stats)

