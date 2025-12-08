#!/usr/bin/env python3
"""Быстрый тест извлечения галереи и даты регистрации"""

import requests
import json
from bs4 import BeautifulSoup

def extract_from_mobile(car_id):
    """Извлечение из мобильной версии через requests"""
    url = f'https://m.dongchedi.com/usedcar/{car_id}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    print(f'\n📱 МОБИЛЬНАЯ ВЕРСИЯ: {url}')
    response = requests.get(url, headers=headers, timeout=10)
    print(f'   Статус: {response.status_code}')
    
    if response.status_code == 200 and '__NEXT_DATA__' in response.text:
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup.find_all('script'):
            if script.string and '__NEXT_DATA__' in script.string:
                try:
                    json_start = script.string.find('{')
                    json_data = script.string[json_start:]
                    brace_count = 0
                    json_end = 0
                    for i, char in enumerate(json_data):
                        if char == '{': brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    if json_end > 0:
                        data = json.loads(json_data[:json_end])
                        if 'props' in data and 'pageProps' in data['props']:
                            sku_detail = data['props']['pageProps'].get('skuDetail', {})
                            
                            # Галерея
                            head_images = sku_detail.get('head_images', [])
                            if head_images:
                                print(f'   📸 ГАЛЕРЕЯ: ✅ {len(head_images)} изображений')
                                print(f'      Пример: {head_images[0][:70]}...')
                                return {'gallery': head_images, 'method': 'mobile_requests'}
                            else:
                                print(f'   📸 ГАЛЕРЕЯ: ❌ не найдена')
                            
                            # Дата регистрации
                            other_params = sku_detail.get('other_params', [])
                            for param in other_params:
                                if param.get('name') in ('上牌时间', '首次上牌', '首次上牌时间'):
                                    print(f'   📅 ДАТА: ✅ {param.get("value")}')
                                    return {'date': param.get('value'), 'method': 'mobile_requests'}
                            
                            if other_params:
                                print(f'   📅 ДАТА: ❌ не найдена (проверено {len(other_params)} параметров)')
                            else:
                                print(f'   📅 ДАТА: ❌ other_params пуст')
                except Exception as e:
                    print(f'   ❌ Ошибка парсинга: {e}')
    
    return None

def extract_from_selenium(car_id):
    """Извлечение через Selenium"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        import os
        import time
        import tempfile
        import shutil
        
        url = f'https://www.dongchedi.com/usedcar/{car_id}'
        print(f'\n🤖 SELENIUM: {url}')
        
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        
        temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f'--user-data-dir={temp_dir}')
        
        driver = None
        try:
            driver_path = os.environ.get('CHROMEDRIVER_PATH')
            if driver_path:
                driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            
            driver.set_page_load_timeout(60)
            driver.execute_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined})')
            
            driver.get(url)
            time.sleep(3)
            
            # Получаем через JavaScript
            next_data_js = driver.execute_script('''
                try {
                    return window.__NEXT_DATA__;
                } catch(e) {
                    return null;
                }
            ''')
            
            if next_data_js and isinstance(next_data_js, dict):
                print('   ✅ __NEXT_DATA__ найден')
                if 'props' in next_data_js and 'pageProps' in next_data_js['props']:
                    sku_detail = next_data_js['props']['pageProps'].get('skuDetail', {})
                    
                    # Галерея
                    head_images = sku_detail.get('head_images', [])
                    if head_images:
                        print(f'   📸 ГАЛЕРЕЯ: ✅ {len(head_images)} изображений')
                        print(f'      Пример: {head_images[0][:70]}...')
                        result = {'gallery': head_images, 'method': 'selenium'}
                    else:
                        print(f'   📸 ГАЛЕРЕЯ: ❌ не найдена')
                        result = {'method': 'selenium'}
                    
                    # Дата регистрации
                    other_params = sku_detail.get('other_params', [])
                    for param in other_params:
                        if param.get('name') in ('上牌时间', '首次上牌', '首次上牌时间'):
                            print(f'   📅 ДАТА: ✅ {param.get("value")}')
                            result['date'] = param.get('value')
                            return result
                    
                    if other_params:
                        print(f'   📅 ДАТА: ❌ не найдена (проверено {len(other_params)} параметров)')
                    else:
                        print(f'   📅 ДАТА: ❌ other_params пуст')
                    
                    return result
            else:
                print('   ❌ __NEXT_DATA__ не найден или не dict')
                
        finally:
            if driver:
                driver.quit()
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        print(f'   ❌ Ошибка: {e}')
    
    return None

if __name__ == '__main__':
    car_id = '79372'
    print('='*70)
    print(f'ТЕСТ ИЗВЛЕЧЕНИЯ ДАННЫХ ДЛЯ car_id={car_id}')
    print('='*70)
    
    result1 = extract_from_mobile(car_id)
    result2 = extract_from_selenium(car_id)
    
    print('\n' + '='*70)
    print('ИТОГИ:')
    print('='*70)
    print(f'Мобильная версия (requests): {"✅ работает" if result1 else "❌ не работает"}')
    print(f'Selenium: {"✅ работает" if result2 else "❌ не работает"}')







