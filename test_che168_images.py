#!/usr/bin/env python3
"""
Тестовый скрипт для проверки получения image_gallery из che168
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pyparsers'))

import asyncio
import logging
from api.che168.detailed_parser_api import Che168DetailedParserAPI
from api.che168.parser import Che168Parser

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Тестовые car_id из логов
TEST_CAR_IDS = [57009439, 57009438, 57009440, 57008675, 57009442]

def test_api_parser(car_id: int):
    """Тест API парсера"""
    print(f"\n{'='*60}")
    print(f"ТЕСТ API ПАРСЕРА для car_id={car_id}")
    print(f"{'='*60}")
    
    parser = Che168DetailedParserAPI()
    try:
        result = parser.parse_car_details(car_id)
        if result:
            print(f"✅ Успешно получены данные")
            print(f"  - image: {result.image}")
            print(f"  - image_gallery: {result.image_gallery[:100] if result.image_gallery else None}...")
            print(f"  - image_count: {result.image_count}")
            print(f"  - first_registration_time: {result.first_registration_time}")
            print(f"  - power: {result.power}")
        else:
            print(f"❌ Не удалось получить данные")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        parser.close()

def test_selenium_parser(car_id: int):
    """Тест Selenium парсера"""
    print(f"\n{'='*60}")
    print(f"ТЕСТ SELENIUM ПАРСЕРА для car_id={car_id}")
    print(f"{'='*60}")
    
    car_url = f'https://m.che168.com/cardetail/index?infoid={car_id}'
    parser = Che168Parser(headless=True)
    
    try:
        car_obj, meta = parser.fetch_car_detail(car_url)
        if car_obj:
            print(f"✅ Успешно получены данные")
            print(f"  - image: {car_obj.image}")
            # Che168Car не имеет image_gallery, но проверим что есть
            print(f"  - car_id: {car_obj.car_id}")
            print(f"  - title: {car_obj.title}")
            print(f"  - first_registration_time: {car_obj.first_registration_time}")
            print(f"  - power: {car_obj.power}")
            print(f"  - meta: {meta}")
        else:
            print(f"❌ Не удалось получить данные")
            print(f"  - meta: {meta}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def test_direct_api_request(car_id: int):
    """Тест прямого запроса к API"""
    print(f"\n{'='*60}")
    print(f"ТЕСТ ПРЯМОГО API ЗАПРОСА для car_id={car_id}")
    print(f"{'='*60}")
    
    import requests
    
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
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"Статус код: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Успешный ответ")
            print(f"  - returncode: {data.get('returncode')}")
            print(f"  - returnmsg: {data.get('returnmsg')}")
            
            result = data.get('result', {})
            if result:
                print(f"  - Доступные поля: {list(result.keys())[:20]}")
                
                # Проверяем поля с изображениями
                image_fields = ['piclist', 'head_images', 'images', 'picurl', 'imageurl', 'carimage']
                for field in image_fields:
                    value = result.get(field)
                    if value:
                        if isinstance(value, list):
                            print(f"  - {field}: список из {len(value)} элементов")
                            if len(value) > 0:
                                print(f"    Первый элемент: {value[0][:100] if isinstance(value[0], str) else value[0]}")
                        else:
                            print(f"  - {field}: {str(value)[:100]}")
        elif response.status_code == 403:
            print(f"❌ 403 Forbidden - API заблокирован")
            print(f"  - Response: {response.text[:200]}")
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(f"  - Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")

def test_selenium_json_parsing(car_id: int):
    """Тест парсинга JSON из Selenium"""
    print(f"\n{'='*60}")
    print(f"ТЕСТ ПАРСИНГА JSON ИЗ SELENIUM для car_id={car_id}")
    print(f"{'='*60}")
    
    import json
    import re
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from bs4 import BeautifulSoup
    import time
    import tempfile
    import shutil
    
    car_url = f'https://m.che168.com/cardetail/index?infoid={car_id}'
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    temp_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={temp_dir}")
    
    driver = None
    try:
        driver_path = os.environ.get("CHROMEDRIVER_PATH")
        if driver_path:
            driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
        
        print(f"Загружаем страницу: {car_url}")
        driver.get(car_url)
        time.sleep(3)
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Ищем все script теги
        script_tags = soup.find_all('script')
        print(f"Найдено {len(script_tags)} script тегов")
        
        for i, script in enumerate(script_tags):
            if script.string:
                script_text = script.string
                if '__NEXT_DATA__' in script_text or 'skuDetail' in script_text:
                    print(f"\nНайден релевантный script #{i}")
                    print(f"  Длина: {len(script_text)} символов")
                    
                    # Пытаемся найти head_images
                    if 'head_images' in script_text:
                        print(f"  ✅ Найдено 'head_images' в script")
                        
                        # Пробуем разные способы извлечения
                        # Способ 1: через regex
                        head_images_match = re.search(r'"head_images"\s*:\s*\[(.*?)\]', script_text, re.DOTALL)
                        if head_images_match:
                            print(f"  ✅ Найден массив head_images через regex")
                            urls_match = re.findall(r'"([^"]+)"', head_images_match.group(1))
                            if urls_match:
                                print(f"  ✅ Извлечено {len(urls_match)} URL через regex")
                                for j, url in enumerate(urls_match[:3]):
                                    print(f"    URL {j+1}: {url[:80]}...")
                        
                        # Способ 2: через JSON парсинг
                        try:
                            json_start = script_text.find('{')
                            if json_start != -1:
                                # Пытаемся найти skuDetail
                                if 'skuDetail' in script_text:
                                    sku_detail_match = re.search(r'"skuDetail"\s*:\s*({[^}]+})', script_text, re.DOTALL)
                                    if sku_detail_match:
                                        print(f"  ✅ Найден skuDetail объект")
                                        # Пытаемся извлечь head_images из него
                                        head_images_in_sku = re.search(r'"head_images"\s*:\s*\[(.*?)\]', sku_detail_match.group(1), re.DOTALL)
                                        if head_images_in_sku:
                                            print(f"  ✅ Найден head_images в skuDetail")
                                            urls = re.findall(r'"([^"]+)"', head_images_in_sku.group(1))
                                            if urls:
                                                print(f"  ✅ Извлечено {len(urls)} URL из skuDetail")
                                                for j, url in enumerate(urls[:3]):
                                                    print(f"    URL {j+1}: {url[:80]}...")
                        except Exception as e:
                            print(f"  ❌ Ошибка JSON парсинга: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass

if __name__ == "__main__":
    print("="*60)
    print("ТЕСТИРОВАНИЕ ПОЛУЧЕНИЯ IMAGE_GALLERY ДЛЯ CHE168")
    print("="*60)
    
    # Берем первый тестовый car_id
    test_car_id = TEST_CAR_IDS[0]
    
    # Тест 1: Прямой API запрос
    test_direct_api_request(test_car_id)
    
    # Тест 2: API парсер
    test_api_parser(test_car_id)
    
    # Тест 3: Selenium парсер
    test_selenium_parser(test_car_id)
    
    # Тест 4: Парсинг JSON из Selenium
    test_selenium_json_parsing(test_car_id)
    
    print(f"\n{'='*60}")
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print(f"{'='*60}")







