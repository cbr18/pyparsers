#!/usr/bin/env python3
"""
Анализ истории парсинга image_gallery и first_registration_time
для dongchedi и che168
"""

import subprocess
import re
from datetime import datetime, timedelta
from collections import defaultdict

def parse_logs(hours_back=24):
    """Парсит логи за указанное количество часов назад"""
    cmd = f"docker compose logs pyparsers --tail 1000000 --since {hours_back * 60}m 2>&1"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="/home/alex/CarsParser")
    return result.stdout

def analyze_parsing_patterns(logs):
    """Анализирует паттерны парсинга"""
    
    stats = {
        'dongchedi': {
            'image_gallery': {'found': 0, 'not_found': 0, 'times': []},
            'first_registration_time': {'found': 0, 'not_found': 0, 'times': []},
            'blocked': 0,
            'mobile_fallback': {'success': 0, 'failed': 0}
        },
        'che168': {
            'image_gallery': {'found': 0, 'not_found': 0, 'times': []},
            'first_registration_time': {'found': 0, 'not_found': 0, 'times': []},
            'blocked': 0,
            'api_403': 0,
            'fallback': {'success': 0, 'failed': 0}
        }
    }
    
    lines = logs.split('\n')
    
    for line in lines:
        # Dongchedi image_gallery
        if 'dongchedi' in line.lower():
            if 'найдена image_gallery' in line.lower() or '[mobile fallback].*image_gallery' in line.lower():
                stats['dongchedi']['image_gallery']['found'] += 1
                time_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
                if time_match:
                    stats['dongchedi']['image_gallery']['times'].append(time_match.group(1))
            elif 'изображения не найдены' in line.lower() or 'head_images не найден' in line.lower():
                stats['dongchedi']['image_gallery']['not_found'] += 1
            
            # first_registration_time
            if 'найдена first_registration_time' in line.lower() or '[mobile fallback].*first_registration_time' in line.lower():
                stats['dongchedi']['first_registration_time']['found'] += 1
                time_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
                if time_match:
                    stats['dongchedi']['first_registration_time']['times'].append(time_match.group(1))
            elif 'first_registration_time не заполнен' in line.lower():
                stats['dongchedi']['first_registration_time']['not_found'] += 1
            
            # Блокировки
            if 'заблокирован' in line.lower() or 'blocked' in line.lower() or '403' in line or '514' in line:
                stats['dongchedi']['blocked'] += 1
            
            # Mobile fallback
            if '[MOBILE FALLBACK]' in line:
                if 'Успешно извлечены данные' in line or 'Найдена image_gallery' in line:
                    stats['dongchedi']['mobile_fallback']['success'] += 1
                elif 'Не удалось' in line:
                    stats['dongchedi']['mobile_fallback']['failed'] += 1
        
        # Che168
        elif 'che168' in line.lower():
            if 'найдена image_gallery' in line.lower() or '[API].*Сохранена image_gallery' in line.lower():
                stats['che168']['image_gallery']['found'] += 1
                time_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
                if time_match:
                    stats['che168']['image_gallery']['times'].append(time_match.group(1))
            elif 'изображения не найдены' in line.lower():
                stats['che168']['image_gallery']['not_found'] += 1
            
            # first_registration_time
            if 'first_registration_time' in line.lower() and ('найден' in line.lower() or '=' in line):
                if 'не заполнен' not in line.lower():
                    stats['che168']['first_registration_time']['found'] += 1
            
            # 403 ошибки
            if '403' in line or 'Forbidden' in line:
                stats['che168']['api_403'] += 1
            
            # Fallback
            if 'Получены изображения через fallback' in line:
                stats['che168']['fallback']['success'] += 1
    
    return stats

def print_report(stats):
    """Печатает отчет"""
    print("=" * 80)
    print("АНАЛИЗ ПАРСИНГА IMAGE_GALLERY И FIRST_REGISTRATION_TIME")
    print("=" * 80)
    print()
    
    # Dongchedi
    print("📊 DONGCHEDI:")
    print("-" * 80)
    
    d = stats['dongchedi']
    print(f"  image_gallery:")
    print(f"    ✅ Найдено: {d['image_gallery']['found']}")
    print(f"    ❌ Не найдено: {d['image_gallery']['not_found']}")
    if d['image_gallery']['times']:
        print(f"    📅 Последнее: {d['image_gallery']['times'][-1]}")
    
    print(f"  first_registration_time:")
    print(f"    ✅ Найдено: {d['first_registration_time']['found']}")
    print(f"    ❌ Не найдено: {d['first_registration_time']['not_found']}")
    if d['first_registration_time']['times']:
        print(f"    📅 Последнее: {d['first_registration_time']['times'][-1]}")
    
    print(f"  Блокировки: {d['blocked']}")
    print(f"  Mobile fallback: успешно {d['mobile_fallback']['success']}, ошибок {d['mobile_fallback']['failed']}")
    print()
    
    # Che168
    print("📊 CHE168:")
    print("-" * 80)
    
    c = stats['che168']
    print(f"  image_gallery:")
    print(f"    ✅ Найдено: {c['image_gallery']['found']}")
    print(f"    ❌ Не найдено: {c['image_gallery']['not_found']}")
    if c['image_gallery']['times']:
        print(f"    📅 Последнее: {c['image_gallery']['times'][-1]}")
    
    print(f"  first_registration_time: найдено {c['first_registration_time']['found']}")
    print(f"  API 403 ошибки: {c['api_403']}")
    print(f"  Fallback: успешно {c['fallback']['success']}, ошибок {c['fallback']['failed']}")
    print()
    
    # Выводы
    print("=" * 80)
    print("ВЫВОДЫ:")
    print("=" * 80)
    
    if d['image_gallery']['found'] == 0 and d['image_gallery']['not_found'] > 0:
        print("❌ DONGCHEDI image_gallery: НЕ парсится")
    elif d['image_gallery']['found'] > 0:
        print(f"✅ DONGCHEDI image_gallery: парсится (найдено {d['image_gallery']['found']})")
    
    if d['first_registration_time']['found'] == 0 and d['first_registration_time']['not_found'] > 0:
        print("❌ DONGCHEDI first_registration_time: НЕ парсится")
    elif d['first_registration_time']['found'] > 0:
        print(f"✅ DONGCHEDI first_registration_time: парсится (найдено {d['first_registration_time']['found']})")
    
    if c['image_gallery']['found'] == 0:
        print("❌ CHE168 image_gallery: НЕ парсится (или не логируется)")
    elif c['image_gallery']['found'] > 0:
        print(f"✅ CHE168 image_gallery: парсится (найдено {c['image_gallery']['found']})")
    
    if c['api_403'] > 100:
        print(f"⚠️  CHE168: Много 403 ошибок ({c['api_403']}) - возможно блокировка")

if __name__ == '__main__':
    print("Загрузка логов за последние 24 часа...")
    logs_24h = parse_logs(24)
    
    print("Загрузка логов за последние 6 часов...")
    logs_6h = parse_logs(6)
    
    print("\nАнализ за 24 часа:")
    stats_24h = analyze_parsing_patterns(logs_24h)
    print_report(stats_24h)
    
    print("\n" + "=" * 80)
    print("\nАнализ за 6 часов (последние):")
    stats_6h = analyze_parsing_patterns(logs_6h)
    print_report(stats_6h)






