#!/usr/bin/env python3
"""
Скрипт для проверки разницы между блокировкой и недоступностью машины
"""
import re
import sys
from collections import defaultdict

def analyze_ban_vs_unavailable(log_file_path):
    """Анализирует логи и различает блокировку от недоступности"""
    
    stats = {
        'total_parsed': 0,
        'http_403': 0,
        'http_514': 0,
        'returncode_error': 0,
        'result_empty': 0,
        'car_ids': defaultdict(lambda: {
            'status_codes': [],
            'returncode_errors': [],
            'result_empty': False,
            'is_banned_set': False
        })
    }
    
    with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        current_car_id = None
        for line in f:
            # Ищем начало парсинга
            if '[API] Парсинг car_id:' in line:
                match = re.search(r'car_id:\s*(\d+)', line)
                if match:
                    current_car_id = match.group(1)
                    stats['total_parsed'] += 1
            
            if current_car_id:
                # HTTP статусы
                if 'вернул 403' in line:
                    stats['http_403'] += 1
                    stats['car_ids'][current_car_id]['status_codes'].append(403)
                    stats['car_ids'][current_car_id]['is_banned_set'] = True
                
                if 'вернул 514' in line:
                    stats['http_514'] += 1
                    stats['car_ids'][current_car_id]['status_codes'].append(514)
                    stats['car_ids'][current_car_id]['is_banned_set'] = True
                
                # Ошибки returncode (машина может быть недоступна)
                if 'returncode != 0' in line:
                    stats['returncode_error'] += 1
                    match = re.search(r'returnmsg[:\s]+(.+?)(?:\n|$)', line)
                    if match:
                        msg = match.group(1).strip()
                        stats['car_ids'][current_car_id]['returncode_errors'].append(msg)
                
                # Пустой result (машина может быть недоступна)
                if 'result is empty' in line:
                    stats['result_empty'] += 1
                    stats['car_ids'][current_car_id]['result_empty'] = True
    
    return stats

def print_analysis(stats):
    """Выводит анализ"""
    print("=" * 80)
    print("АНАЛИЗ: БЛОКИРОВКА vs НЕДОСТУПНОСТЬ МАШИНЫ")
    print("=" * 80)
    print()
    
    print(f"Всего попыток парсинга: {stats['total_parsed']}")
    print()
    
    print("HTTP статусы (блокировка API):")
    print(f"  - 403 Forbidden: {stats['http_403']}")
    print(f"  - 514 Frequency Capped: {stats['http_514']}")
    print(f"  - Всего блокировок: {stats['http_403'] + stats['http_514']}")
    print()
    
    print("Ошибки API (может быть недоступность машины):")
    print(f"  - returncode != 0: {stats['returncode_error']}")
    print(f"  - result is empty: {stats['result_empty']}")
    print()
    
    # Анализ по car_id
    banned_only = []
    unavailable_only = []
    both = []
    
    for car_id, data in stats['car_ids'].items():
        has_ban = data['is_banned_set']
        has_unavailable = data['result_empty'] or len(data['returncode_errors']) > 0
        
        if has_ban and not has_unavailable:
            banned_only.append(car_id)
        elif has_unavailable and not has_ban:
            unavailable_only.append(car_id)
        elif has_ban and has_unavailable:
            both.append(car_id)
    
    print("Анализ по car_id:")
    print(f"  - Только блокировка (403/514): {len(banned_only)}")
    print(f"  - Только недоступность (returncode/empty): {len(unavailable_only)}")
    print(f"  - И то, и другое: {len(both)}")
    print()
    
    if banned_only:
        print(f"Примеры car_id с блокировкой: {banned_only[:5]}")
        print()
    
    if unavailable_only:
        print(f"Примеры car_id с недоступностью: {unavailable_only[:5]}")
        print()
    
    print("=" * 80)
    print("ВЫВОДЫ:")
    print("=" * 80)
    
    if stats['http_403'] + stats['http_514'] > 0:
        print(f"✅ 403/514 - это точно БЛОКИРОВКА API (не машина)")
        print(f"   - 403 Forbidden: блокировка доступа")
        print(f"   - 514 Frequency Capped: блокировка по частоте (Cloudflare)")
        print()
    
    if stats['returncode_error'] > 0 or stats['result_empty'] > 0:
        print(f"⚠️  returncode != 0 или result is empty - может быть НЕДОСТУПНОСТЬ машины")
        print(f"   - Нужно проверить returnmsg для точного определения")
        print()
    
    if len(banned_only) > 0:
        print(f"📊 {len(banned_only)} car_id имеют только блокировку API (не недоступность)")
    if len(unavailable_only) > 0:
        print(f"📊 {len(unavailable_only)} car_id имеют только недоступность (не блокировку)")
    if len(both) > 0:
        print(f"📊 {len(both)} car_id имеют и блокировку, и недоступность")
    print()

if __name__ == '__main__':
    log_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/full_api_logs.txt'
    
    print(f"Анализ логов из: {log_file}")
    print()
    
    stats = analyze_ban_vs_unavailable(log_file)
    print_analysis(stats)

