#!/usr/bin/env python3
"""
Тестовый скрипт для проверки различных методов получения image_gallery для che168
"""

import requests
import json
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
import time
import sys

# Тестовые car_id
TEST_CAR_IDS = [
    56674209,  # Из логов
    57012762,
    56847514,
    56954019,
    55966793,  # Из успешных парсингов
    56599200,
    56624912,
]

def test_direct_api_getcarinfo(car_id: int) -> Dict[str, Any]:
    """Тест 1: Прямой запрос к API getcarinfo"""
    print(f"\n{'='*70}")
    print(f"ТЕСТ 1: Прямой запрос к API getcarinfo для car_id={car_id}")
    print(f"{'='*70}")
    
    url = "https://apiuscdt.che168.com/apic/v2/car/getcarinfo"
    params = {
        "infoid": car_id,
        "deviceid": f"api_parser_{car_id}",
        "_appid": "2sc.m"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://m.che168.com/",
    }
    
    result = {
        "method": "direct_api_getcarinfo",
        "car_id": car_id,
        "status": None,
        "has_images": False,
        "image_fields": {},
        "image_gallery": None,
        "error": None
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        result["status"] = response.status_code
        
        if response.status_code == 403:
            print(f"   ❌ API заблокирован (403 Forbidden)")
            result["error"] = "403 Forbidden"
            return result
        
        if response.status_code != 200:
            print(f"   ❌ Статус: {response.status_code}")
            result["error"] = f"HTTP {response.status_code}"
            return result
        
        data = response.json()
        
        if data.get('returncode') != 0:
            print(f"   ❌ returncode != 0: {data.get('returnmsg')}")
            result["error"] = data.get('returnmsg', 'returncode != 0')
            return result
        
        result_data = data.get('result', {})
        
        # Проверяем все возможные поля с изображениями
        image_fields = ['piclist', 'head_images', 'images', 'picurl', 'imageurl', 'carimage']
        found_fields = {}
        
        for field in image_fields:
            value = result_data.get(field)
            if value:
                found_fields[field] = {
                    "type": type(value).__name__,
                    "value_preview": str(value)[:200] if isinstance(value, (str, list)) else str(value),
                    "length": len(value) if isinstance(value, (list, str)) else None
                }
                if isinstance(value, list) and len(value) > 0:
                    print(f"   ✅ Найдено поле {field}: {len(value)} элементов")
                    if isinstance(value[0], str):
                        print(f"      Пример: {value[0][:80]}...")
                    elif isinstance(value[0], dict):
                        print(f"      Структура: {list(value[0].keys())}")
                elif isinstance(value, str):
                    print(f"   ✅ Найдено поле {field} (строка): {value[:80]}...")
        
        result["image_fields"] = found_fields
        
        # Пробуем извлечь изображения
        images = None
        
        if 'piclist' in result_data and isinstance(result_data['piclist'], list):
            images = result_data['piclist']
        elif 'head_images' in result_data and isinstance(result_data['head_images'], list):
            images = result_data['head_images']
        elif 'images' in result_data and isinstance(result_data['images'], list):
            images = result_data['images']
        elif 'picurl' in result_data:
            if isinstance(result_data['picurl'], list):
                images = result_data['picurl']
            elif isinstance(result_data['picurl'], str):
                images = [result_data['picurl']]
        
        if images and len(images) > 0:
            result["has_images"] = True
            result["image_gallery"] = ' '.join(str(img) for img in images[:10])  # Первые 10
            print(f"   ✅ Найдено {len(images)} изображений")
        else:
            print(f"   ❌ Изображения не найдены в полях: {list(found_fields.keys())}")
            print(f"   Доступные поля в result: {list(result_data.keys())[:20]}")
        
        return result
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        result["error"] = str(e)
        return result

def test_mobile_requests(car_id: int) -> Dict[str, Any]:
    """Тест 2: Мобильная версия через requests"""
    print(f"\n{'='*70}")
    print(f"ТЕСТ 2: Мобильная версия через requests для car_id={car_id}")
    print(f"{'='*70}")
    
    url = f"https://m.che168.com/cardetail/index?infoid={car_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    
    result = {
        "method": "mobile_requests",
        "car_id": car_id,
        "status": None,
        "has_next_data": False,
        "has_head_images": False,
        "image_gallery": None,
        "error": None
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        result["status"] = response.status_code
        
        if response.status_code != 200:
            print(f"   ❌ Статус: {response.status_code}")
            result["error"] = f"HTTP {response.status_code}"
            return result
        
        print(f"   ✅ Статус: {response.status_code}")
        print(f"   Размер HTML: {len(response.text)} байт")
        
        if '__NEXT_DATA__' not in response.text:
            print(f"   ❌ __NEXT_DATA__ не найден")
            result["error"] = "__NEXT_DATA__ not found"
            return result
        
        result["has_next_data"] = True
        print(f"   ✅ __NEXT_DATA__ найден")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tags = soup.find_all('script')
        
        for script in script_tags:
            if script.string and '__NEXT_DATA__' in script.string:
                try:
                    json_start = script.string.find('{')
                    if json_start == -1:
                        continue
                    
                    json_data = script.string[json_start:]
                    brace_count = 0
                    json_end = 0
                    for i, char in enumerate(json_data):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    
                    if json_end == 0:
                        continue
                    
                    json_str = json_data[:json_end]
                    data = json.loads(json_str)
                    
                    if 'props' in data and 'pageProps' in data['props']:
                        page_props = data['props']['pageProps']
                        if 'skuDetail' in page_props:
                            sku_detail = page_props['skuDetail']
                            
                            head_images = sku_detail.get('head_images', [])
                            if head_images and isinstance(head_images, list) and len(head_images) > 0:
                                result["has_head_images"] = True
                                result["image_gallery"] = ' '.join(head_images[:10])
                                print(f"   ✅ Найдено head_images: {len(head_images)} изображений")
                                print(f"      Пример: {head_images[0][:80]}...")
                                return result
                    
                    print(f"   ❌ head_images не найден в skuDetail")
                    return result
                    
                except Exception as e:
                    print(f"   ❌ Ошибка парсинга: {e}")
                    continue
        
        print(f"   ❌ Не удалось распарсить __NEXT_DATA__")
        result["error"] = "Failed to parse __NEXT_DATA__"
        return result
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        result["error"] = str(e)
        return result

def test_selenium_parsing(car_id: int) -> Dict[str, Any]:
    """Тест 3: Selenium парсинг (аналогично parser.py)"""
    print(f"\n{'='*70}")
    print(f"ТЕСТ 3: Selenium парсинг для car_id={car_id}")
    print(f"{'='*70}")
    
    result = {
        "method": "selenium",
        "car_id": car_id,
        "has_head_images": False,
        "image_gallery": None,
        "error": None
    }
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from bs4 import BeautifulSoup
        import os
        import tempfile
        import shutil
        
        # Пробуем сначала десктопную, потом мобильную
        urls_to_try = [
            f"https://www.che168.com/dealer/{car_id}.html",
            f"https://www.che168.com/cardetail/{car_id}.html",
            f"https://m.che168.com/cardetail/index?infoid={car_id}",
        ]
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        
        driver = None
        try:
            driver_path = os.environ.get("CHROMEDRIVER_PATH")
            if driver_path:
                driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            
            driver.set_page_load_timeout(60)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"   📡 Загружаю: {url}")
            driver.get(url)
            time.sleep(5)
            
            # Прокручиваем страницу
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Пробуем получить через JavaScript
            next_data_js = driver.execute_script("""
                try {
                    return window.__NEXT_DATA__;
                } catch(e) {
                    return null;
                }
            """)
            
            if next_data_js and isinstance(next_data_js, dict):
                print(f"   ✅ __NEXT_DATA__ найден через JavaScript")
                if 'props' in next_data_js and 'pageProps' in next_data_js['props']:
                    sku_detail = next_data_js['props']['pageProps'].get('skuDetail', {})
                    head_images = sku_detail.get('head_images', [])
                    
                    if head_images and isinstance(head_images, list) and len(head_images) > 0:
                        result["has_head_images"] = True
                        result["image_gallery"] = ' '.join(head_images[:10])
                        print(f"   ✅ Найдено head_images: {len(head_images)} изображений")
                        print(f"      Пример: {head_images[0][:80]}...")
                        return result
                    else:
                        print(f"   ❌ head_images не найден в skuDetail")
                else:
                    print(f"   ❌ skuDetail не найден в pageProps")
            else:
                print(f"   ❌ __NEXT_DATA__ не найден через JavaScript, проверяю HTML...")
            
            # Если не нашли через JS, парсим HTML напрямую
            page_source = driver.page_source
            print(f"   📄 Размер HTML: {len(page_source)} байт")
            print(f"   🔍 Проверяю наличие __NEXT_DATA__ в HTML: {'__NEXT_DATA__' in page_source}")
            
            if '__NEXT_DATA__' in page_source:
                soup = BeautifulSoup(page_source, 'html.parser')
                script_tags = soup.find_all('script')
                print(f"   📜 Найдено {len(script_tags)} script тегов")
                
                for script in script_tags:
                    if script.string and '__NEXT_DATA__' in script.string:
                        try:
                            json_start = script.string.find('{')
                            if json_start == -1:
                                continue
                            
                            json_data = script.string[json_start:]
                            brace_count = 0
                            json_end = 0
                            for i, char in enumerate(json_data):
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_end = i + 1
                                        break
                            
                            if json_end == 0:
                                continue
                            
                            json_str = json_data[:json_end]
                            data = json.loads(json_str)
                            
                            if 'props' in data and 'pageProps' in data['props']:
                                page_props = data['props']['pageProps']
                                if 'skuDetail' in page_props:
                                    sku_detail = page_props['skuDetail']
                                    head_images = sku_detail.get('head_images', [])
                                    
                                    if head_images and isinstance(head_images, list) and len(head_images) > 0:
                                        result["has_head_images"] = True
                                        result["image_gallery"] = ' '.join(head_images[:10])
                                        print(f"   ✅ Найдено head_images в HTML: {len(head_images)} изображений")
                                        print(f"      Пример: {head_images[0][:80]}...")
                                        return result
                        except Exception as e:
                            print(f"   ⚠️ Ошибка парсинга script: {e}")
                            continue
            
            print(f"   ❌ head_images не найден ни через JS, ни в HTML")
            
        finally:
            if driver:
                driver.quit()
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        return result
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        result["error"] = str(e)
        return result

def test_alternative_api_endpoints(car_id: int) -> Dict[str, Any]:
    """Тест 4: Альтернативные API endpoints"""
    print(f"\n{'='*70}")
    print(f"ТЕСТ 4: Альтернативные API endpoints для car_id={car_id}")
    print(f"{'='*70}")
    
    endpoints = [
        "https://apiuscdt.che168.com/api/v1/car/getparamtypeitems",
        "https://apiuscdt.che168.com/apic/v2/car/getcarinfo",
    ]
    
    result = {
        "method": "alternative_api",
        "car_id": car_id,
        "endpoints": {}
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://m.che168.com/",
    }
    
    for endpoint in endpoints:
        print(f"\n   Тестирую: {endpoint}")
        params = {
            "infoid": car_id,
            "deviceid": f"api_parser_{car_id}",
            "_appid": "2sc.m"
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=headers, timeout=15)
            endpoint_result = {
                "status": response.status_code,
                "has_images": False,
                "image_fields": []
            }
            
            if response.status_code == 200:
                data = response.json()
                result_data = data.get('result', {})
                
                # Проверяем поля с изображениями
                for field in ['piclist', 'head_images', 'images', 'picurl']:
                    if field in result_data and result_data[field]:
                        endpoint_result["image_fields"].append(field)
                        endpoint_result["has_images"] = True
                        print(f"      ✅ Найдено поле {field}")
            
            result["endpoints"][endpoint] = endpoint_result
            
        except Exception as e:
            result["endpoints"][endpoint] = {"error": str(e)}
            print(f"      ❌ Ошибка: {e}")
    
    return result

if __name__ == "__main__":
    print("="*70)
    print("ТЕСТИРОВАНИЕ ПОЛУЧЕНИЯ IMAGE_GALLERY ДЛЯ CHE168")
    print("="*70)
    
    all_results = []
    
    for car_id in TEST_CAR_IDS:
        print(f"\n\n{'#'*70}")
        print(f"ТЕСТИРОВАНИЕ car_id={car_id}")
        print(f"{'#'*70}")
        
        # Тест 1: Прямой API запрос
        result1 = test_direct_api_getcarinfo(car_id)
        all_results.append(result1)
        time.sleep(2)
        
        # Тест 2: Мобильная версия через requests
        result2 = test_mobile_requests(car_id)
        all_results.append(result2)
        time.sleep(2)
        
        # Тест 3: Selenium парсинг
        result3 = test_selenium_parsing(car_id)
        all_results.append(result3)
        time.sleep(2)
        
        # Тест 4: Альтернативные API endpoints
        result4 = test_alternative_api_endpoints(car_id)
        all_results.append(result4)
        time.sleep(2)
    
    # Сохраняем результаты
    output_file = "test_results/che168_gallery_test_results.json"
    import os
    os.makedirs("test_results", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n\n{'='*70}")
    print("ИТОГОВЫЙ ОТЧЕТ")
    print(f"{'='*70}")
    
    successful_methods = []
    for result in all_results:
        if result.get("has_images") or result.get("has_head_images"):
            successful_methods.append(f"{result['method']} (car_id={result['car_id']})")
    
    if successful_methods:
        print("\n✅ МЕТОДЫ, КОТОРЫЕ НАШЛИ ИЗОБРАЖЕНИЯ:")
        for method in successful_methods:
            print(f"   - {method}")
    else:
        print("\n❌ НИ ОДИН МЕТОД НЕ НАШЕЛ ИЗОБРАЖЕНИЯ")
    
    print(f"\n📁 Результаты сохранены в: {output_file}")

