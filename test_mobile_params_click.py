#!/usr/bin/env python3
"""
Тест клика на параметры в мобильной версии и парсинг данных
"""

import json
import re
import time
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

CAR_ID = 56305293


def test_params_page():
    """Тест прямого открытия страницы параметров"""
    
    print("="*80)
    print("ТЕСТ: Прямое открытие страницы параметров в мобильной версии")
    print("="*80)
    
    extracted_data = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            viewport={'width': 390, 'height': 844},
            locale='zh-CN'
        )
        
        page = context.new_page()
        
        # Перехватываем API ответы
        api_data = {}
        
        def handle_response(response):
            url = response.url
            if 'getparamtypeitems' in url.lower():
                try:
                    data = response.json()
                    if data.get('returncode') == 0:
                        api_data['params'] = data.get('result', [])
                        print(f"\n✓ Перехвачен API getparamtypeitems ({len(str(data))} bytes)")
                except:
                    pass
        
        page.on("response", handle_response)
        
        # Открываем страницу параметров напрямую
        params_url = f"https://m.che168.com/cardetail/params?infoid={CAR_ID}"
        print(f"\n1. Открываем: {params_url}")
        
        page.goto(params_url, wait_until='networkidle', timeout=60000)
        time.sleep(3)
        
        # Сохраняем скриншот
        page.screenshot(path='/app/params_page.png')
        print("   Скриншот: /app/params_page.png")
        
        # Парсим данные из API
        if 'params' in api_data:
            print("\n2. Извлечённые данные из API:")
            
            for section in api_data['params']:
                title = section.get('title', '')
                items = section.get('data', [])
                
                for item in items:
                    name = item.get('name', '')
                    content = item.get('content', '')
                    
                    if not content or content == '-':
                        continue
                    
                    # Извлекаем ключевые поля
                    if '最大马力' in name:
                        extracted_data['power'] = content + 'Ps'
                        print(f"   ★ power: {content}Ps")
                    elif '最大扭矩' in name:
                        extracted_data['torque'] = content + 'N·m'
                        print(f"   ★ torque: {content}N·m")
                    elif '最高车速' in name:
                        extracted_data['max_speed'] = content + 'km/h'
                        print(f"   ★ max_speed: {content}km/h")
                    elif '0-100' in name:
                        extracted_data['acceleration'] = content + 's'
                        print(f"   ★ acceleration: {content}s")
                    elif '油耗' in name and 'L' not in extracted_data.get('fuel_consumption', ''):
                        extracted_data['fuel_consumption'] = content + 'L/100km'
                        print(f"   ★ fuel_consumption: {content}L/100km")
                    elif '变速箱' == name:
                        extracted_data['transmission'] = content
                        print(f"   ★ transmission: {content}")
                    elif '驱动方式' in name:
                        extracted_data['drive_type'] = content
                        print(f"   ★ drive_type: {content}")
                    elif name == '长度(mm)':
                        extracted_data['length'] = content
                    elif name == '宽度(mm)':
                        extracted_data['width'] = content
                    elif name == '高度(mm)':
                        extracted_data['height'] = content
                    elif name == '轴距(mm)':
                        extracted_data['wheelbase'] = content
                    elif '排量(mL)' in name:
                        extracted_data['engine_volume_ml'] = content
                    elif '气缸数' in name:
                        extracted_data['cylinder_count'] = content
                    elif '进气形式' in name:
                        extracted_data['turbo_type'] = content
                    elif '座位数' in name:
                        extracted_data['seat_count'] = content
                    elif '车门数' in name:
                        extracted_data['door_count'] = content
                    elif '前悬架' in name:
                        extracted_data['front_suspension'] = content
                    elif '后悬架' in name:
                        extracted_data['rear_suspension'] = content
        
        browser.close()
    
    print(f"\n3. Всего извлечено полей: {len(extracted_data)}")
    print("\nИзвлечённые данные:")
    for k, v in extracted_data.items():
        print(f"   {k}: {v}")
    
    return extracted_data


def test_click_params():
    """Тест клика на секцию параметров"""
    
    print("\n" + "="*80)
    print("ТЕСТ: Клик на секцию '参数' в мобильной версии")
    print("="*80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            viewport={'width': 390, 'height': 844},
            locale='zh-CN'
        )
        
        page = context.new_page()
        
        # Перехватываем переходы
        navigations = []
        def on_request(request):
            if request.resource_type == 'document':
                navigations.append(request.url)
        page.on("request", on_request)
        
        # Открываем главную страницу
        main_url = f"https://m.che168.com/cardetail/index?infoid={CAR_ID}"
        print(f"\n1. Открываем: {main_url}")
        
        page.goto(main_url, wait_until='networkidle', timeout=60000)
        time.sleep(3)
        
        # Скриншот до клика
        page.screenshot(path='/app/before_click.png')
        print("   Скриншот до клика: /app/before_click.png")
        
        # Прокручиваем страницу чтобы найти секцию параметров
        print("\n2. Ищем секцию '参数'...")
        
        # Прокручиваем вниз
        for scroll in range(5):
            page.evaluate(f"window.scrollTo(0, {300 * (scroll + 1)})")
            time.sleep(0.5)
            
            # Делаем скриншот каждого скролла
            page.screenshot(path=f'/app/scroll_{scroll}.png')
        
        # Ищем элемент с текстом "参数"
        try:
            param_elements = page.locator("text=参数")
            count = param_elements.count()
            print(f"   Найдено элементов '参数': {count}")
            
            if count > 0:
                # Берём первый элемент
                el = param_elements.first
                el.scroll_into_view_if_needed()
                time.sleep(0.5)
                
                page.screenshot(path='/app/before_param_click.png')
                print("   Скриншот перед кликом: /app/before_param_click.png")
                
                # Кликаем
                el.click(timeout=5000)
                print("   ✓ Клик выполнен!")
                
                time.sleep(3)
                
                # Скриншот после клика
                page.screenshot(path='/app/after_click.png')
                print("   Скриншот после клика: /app/after_click.png")
                
                # Проверяем URL
                current_url = page.url
                print(f"\n3. Текущий URL: {current_url}")
                
                if 'params' in current_url:
                    print("   ✓ Перешли на страницу параметров!")
                
        except Exception as e:
            print(f"   Ошибка: {e}")
        
        # Выводим все переходы
        print(f"\n4. Все переходы:")
        for nav in navigations:
            print(f"   - {nav}")
        
        browser.close()


if __name__ == "__main__":
    # Тест прямого открытия страницы параметров
    data = test_params_page()
    
    # Тест клика на параметры
    test_click_params()
    
    print("\n" + "="*80)
    print("ИТОГ")
    print("="*80)
    print("""
ВЫВОД: 
1. Страница параметров существует: /cardetail/params?infoid={car_id}
2. При открытии страницы параметров вызывается API getparamtypeitems
3. API содержит ВСЕ технические характеристики включая power

РЕКОМЕНДАЦИЯ ДЛЯ ПАРСЕРА:
- Использовать прямой URL m.che168.com/cardetail/params?infoid={car_id}
  ИЛИ
- Делать прямой API запрос к getparamtypeitems (быстрее и надёжнее)
""")

