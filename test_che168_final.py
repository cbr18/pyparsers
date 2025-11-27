#!/usr/bin/env python3
"""
Финальный тест - проверка обоих решений на множестве машин
"""

import json
import re
import time
import os
import requests
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Тестовые ID машин
TEST_CAR_IDS = [
    56305293,   # Tuang 2023 (первая тестовая)
    56915531,   # Ещё одна
    56915528,   # 
    56915533,   #
    56915495,   #
    56915530,   #
]


def extract_from_api(car_id: int, timeout: int = 15) -> Dict[str, Any]:
    """
    РЕШЕНИЕ 1: Извлечение из API getparamtypeitems
    """
    url = "https://apiuscdt.che168.com/api/v1/car/getparamtypeitems"
    params = {
        "infoid": car_id,
        "deviceid": f"test_{car_id}",
        "_appid": "2sc.m"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
        "Referer": f"https://m.che168.com/cardetail/index?infoid={car_id}"
    }
    
    extracted = {'car_id': car_id, 'method': 'api'}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        data = resp.json()
        
        if data.get('returncode') != 0:
            extracted['error'] = data.get('message')
            return extracted
        
        result = data.get('result', [])
        
        for section in result:
            title = section.get('title', '')
            items = section.get('data', [])
            
            for item in items:
                name = item.get('name', '').strip()
                content = item.get('content', '').strip()
                
                if not content or content == '-':
                    continue
                
                # Мощность
                if '最大马力' in name and 'power' not in extracted:
                    extracted['power'] = content + 'Ps'
                
                # Мощность из engine строки
                if '发动机' == name and '马力' in content and 'power' not in extracted:
                    power_match = re.search(r'(\d+)\s*马力', content)
                    if power_match:
                        extracted['power'] = power_match.group(1) + 'Ps'
                    extracted['engine_info'] = content
                
                # Крутящий момент
                if '最大扭矩' in name and 'torque' not in extracted:
                    torque_match = re.search(r'(\d+)', content)
                    if torque_match:
                        extracted['torque'] = torque_match.group(1) + 'N·m'
                
                # Трансмиссия
                if '变速箱' == name:
                    extracted['transmission'] = content
                
                # Размеры
                if '长度' in name:
                    extracted['length'] = content
                if '宽度' in name:
                    extracted['width'] = content
                if '高度' in name:
                    extracted['height'] = content
                if '轴距' in name:
                    extracted['wheelbase'] = content
                
                # Вес
                if '整备质量' in name:
                    extracted['curb_weight'] = content
                
                # Расход
                if 'WLTC' in name and '油耗' in name:
                    extracted['fuel_consumption'] = content
                elif '综合油耗' in name and 'fuel_consumption' not in extracted:
                    extracted['fuel_consumption'] = content
                
                # Разгон
                if '0-100' in name:
                    extracted['acceleration'] = content
                
                # Название
                if '车型名称' in name:
                    extracted['car_name'] = content
        
        extracted['success'] = 'power' in extracted
        
    except requests.exceptions.Timeout:
        extracted['error'] = 'timeout'
    except Exception as e:
        extracted['error'] = str(e)
    
    return extracted


def extract_from_desktop(car_id: int) -> Dict[str, Any]:
    """
    РЕШЕНИЕ 2: Извлечение из десктопной версии сайта
    """
    extracted = {'car_id': car_id, 'method': 'desktop'}
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN'
            )
            
            page = context.new_page()
            
            # Пробуем разные URL
            urls = [
                f"https://www.che168.com/dealer/557461/{car_id}.html",
                f"https://www.che168.com/{car_id}.html",
            ]
            
            for url in urls:
                try:
                    response = page.goto(url, wait_until='networkidle', timeout=30000)
                    time.sleep(2)
                    
                    title = page.title()
                    if '访问出错' in title or '404' in title:
                        continue
                    
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    page_text = soup.get_text()
                    
                    # Ищем мощность
                    power_match = re.search(r'(\d+)\s*马力', page_text)
                    if power_match:
                        extracted['power'] = power_match.group(1) + 'Ps'
                    
                    # Ищем название из title
                    title_match = re.search(r'【[^】]+】(.+?)_', title)
                    if title_match:
                        extracted['car_name'] = title_match.group(1)
                    
                    # Ищем другие данные
                    torque_match = re.search(r'(\d+)\s*N·m', page_text)
                    if torque_match:
                        extracted['torque'] = torque_match.group(1) + 'N·m'
                    
                    extracted['success'] = 'power' in extracted
                    extracted['url'] = url
                    break
                    
                except Exception as e:
                    continue
            
            browser.close()
            
        except Exception as e:
            extracted['error'] = str(e)
    
    return extracted


def main():
    """Тестирование обоих решений"""
    
    print("\n" + "="*80)
    print("ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ РЕШЕНИЙ ДЛЯ CHE168")
    print("="*80)
    
    api_results = []
    desktop_results = []
    
    # Тест API
    print("\n" + "="*60)
    print("ТЕСТ 1: API getparamtypeitems")
    print("="*60)
    
    for car_id in TEST_CAR_IDS:
        print(f"\ncar_id: {car_id}...", end=" ")
        result = extract_from_api(car_id)
        api_results.append(result)
        
        if result.get('success'):
            print(f"✓ power={result.get('power')}")
        else:
            print(f"✗ error={result.get('error', 'no power')}")
    
    # Тест Desktop (только первые 3 для скорости)
    print("\n" + "="*60)
    print("ТЕСТ 2: Desktop версия (первые 3)")
    print("="*60)
    
    for car_id in TEST_CAR_IDS[:3]:
        print(f"\ncar_id: {car_id}...", end=" ")
        result = extract_from_desktop(car_id)
        desktop_results.append(result)
        
        if result.get('success'):
            print(f"✓ power={result.get('power')}, name={result.get('car_name', '')[:20]}")
        else:
            print(f"✗ error={result.get('error', 'no power')}")
    
    # Итоги
    print("\n" + "="*80)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*80)
    
    api_success = sum(1 for r in api_results if r.get('success'))
    desktop_success = sum(1 for r in desktop_results if r.get('success'))
    
    print(f"\nAPI getparamtypeitems: {api_success}/{len(api_results)} успешно")
    print(f"Desktop версия: {desktop_success}/{len(desktop_results)} успешно")
    
    print("\n" + "="*60)
    print("ДЕТАЛИ API РЕЗУЛЬТАТОВ:")
    print("="*60)
    
    for r in api_results:
        if r.get('success'):
            print(f"\ncar_id: {r['car_id']}")
            print(f"  power: {r.get('power')}")
            print(f"  torque: {r.get('torque')}")
            print(f"  car_name: {r.get('car_name', '')[:40]}")
            print(f"  fuel_consumption: {r.get('fuel_consumption')}")
    
    # Рекомендации
    print("\n" + "="*80)
    print("РЕКОМЕНДАЦИИ:")
    print("="*80)
    
    print("""
1. РЕКОМЕНДУЕМОЕ РЕШЕНИЕ: API getparamtypeitems
   - Быстрее (1-2 сек vs 10+ сек для desktop)
   - Структурированные данные
   - Все характеристики доступны

2. АЛЬТЕРНАТИВА: Desktop версия
   - Работает, но медленнее
   - Требует Playwright
   - Можно использовать как fallback

3. ИЗМЕНЕНИЯ В ПАРСЕРЕ:
   - Добавить парсинг структуры result[N].data[M].name/content
   - Искать '最大马力(Ps)' в секции '发动机'
   - Искать мощность в поле '发动机' (например "2.0T 220马力 L4")
    """)
    
    # Сохраняем результаты
    all_results = {
        'api_results': api_results,
        'desktop_results': desktop_results
    }
    
    with open('/tmp/che168_final_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nРезультаты сохранены в /tmp/che168_final_results.json")


if __name__ == "__main__":
    main()

