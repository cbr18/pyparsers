#!/usr/bin/env python3
"""
Тестовый скрипт для проверки альтернативных способов парсинга dongchedi
Проверяет различные методы получения галереи изображений и даты регистрации
"""

import os
import sys
import time
import json
import re
import random
import tempfile
import shutil
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
import requests

# Попробуем импортировать selenium и playwright
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium не установлен")

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright не установлен")


def test_url_variants(car_id: str) -> List[str]:
    """Тестирует различные варианты URL для dongchedi"""
    urls = [
        f"https://www.dongchedi.com/usedcar/{car_id}",
        f"https://m.dongchedi.com/usedcar/{car_id}",
        f"https://www.dongchedi.com/auto/params-carIds-{car_id}",
        f"https://m.dongchedi.com/auto/params-carIds-{car_id}",
    ]
    return urls


def test_requests_parsing(car_id: str) -> Dict[str, Any]:
    """Тест парсинга через requests (без браузера)"""
    print("\n" + "="*70)
    print("ТЕСТ 1: Парсинг через requests (без браузера)")
    print("="*70)
    
    results = {}
    urls = test_url_variants(car_id)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.dongchedi.com/",
    }
    
    for url in urls:
        print(f"\n📡 Тестирую URL: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            print(f"   Статус: {response.status_code}")
            print(f"   Размер HTML: {len(response.text)} байт")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Проверяем наличие __NEXT_DATA__
                has_next_data = '__NEXT_DATA__' in response.text
                print(f"   ✅ __NEXT_DATA__ найден: {has_next_data}")
                
                if has_next_data:
                    # Пробуем извлечь данные
                    script_tags = soup.find_all('script')
                    for script in script_tags:
                        if script.string and '__NEXT_DATA__' in script.string:
                            try:
                                json_start = script.string.find('{')
                                if json_start != -1:
                                    json_data = script.string[json_start:]
                                    # Упрощенный парсинг - находим первый полный JSON объект
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
                                    if json_end > 0:
                                        json_str = json_data[:json_end]
                                        data = json.loads(json_str)
                                        if 'props' in data and 'pageProps' in data['props']:
                                            page_props = data['props']['pageProps']
                                            if 'skuDetail' in page_props:
                                                sku_detail = page_props['skuDetail']
                                                
                                                # Проверяем галерею
                                                head_images = sku_detail.get('head_images', [])
                                                if head_images:
                                                    results[url] = {
                                                        'method': 'requests',
                                                        'image_gallery': head_images,
                                                        'image_count': len(head_images),
                                                        'has_data': True
                                                    }
                                                    print(f"   ✅ Найдено {len(head_images)} изображений")
                                                
                                                # Проверяем дату регистрации
                                                other_params = sku_detail.get('other_params', [])
                                                for param in other_params:
                                                    if param.get('name') in ('上牌时间', '首次上牌', '首次上牌时间'):
                                                        results[url]['first_registration_time'] = param.get('value')
                                                        print(f"   ✅ Найдена дата регистрации: {param.get('value')}")
                                                        break
                                                
                                                if url not in results:
                                                    results[url] = {'method': 'requests', 'has_data': True, 'no_images': True}
                            except Exception as e:
                                print(f"   ❌ Ошибка парсинга JSON: {e}")
                
                # Проверяем CSS селекторы для изображений
                image_selectors = [
                    'img[src*="car"]',
                    'img[src*="dongchedi"]',
                    'img[data-src*="car"]',
                    '.car-image img',
                    '[class*="gallery"] img',
                ]
                images_found = []
                for selector in image_selectors:
                    imgs = soup.select(selector)
                    for img in imgs:
                        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                        if src and 'http' in src and src not in images_found:
                            images_found.append(src)
                
                if images_found and url not in results:
                    results[url] = {
                        'method': 'requests',
                        'image_gallery': images_found,
                        'image_count': len(images_found),
                        'source': 'css_selectors'
                    }
                    print(f"   ✅ Найдено {len(images_found)} изображений через CSS селекторы")
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            results[url] = {'method': 'requests', 'error': str(e)}
    
    return results


def test_selenium_stealth(car_id: str) -> Dict[str, Any]:
    """Тест парсинга через Selenium с улучшенным stealth режимом"""
    if not SELENIUM_AVAILABLE:
        print("\n⚠️ Selenium не доступен, пропускаю тест")
        return {}
    
    print("\n" + "="*70)
    print("ТЕСТ 2: Парсинг через Selenium с улучшенным stealth режимом")
    print("="*70)
    
    url = f"https://www.dongchedi.com/usedcar/{car_id}"
    results = {}
    
    chrome_options = Options()
    
    # Улучшенный stealth режим
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Дополнительные опции для обхода детекции
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    chrome_options.add_argument("--disable-site-isolation-trials")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    
    # User-Agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    # Отключаем блокировку изображений для этого теста
    prefs = {
        "profile.managed_default_content_settings.images": 1,  # Разрешаем изображения
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
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
        driver.implicitly_wait(10)
        
        # Скрываем webdriver
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
            '''
        })
        
        print(f"\n📡 Загружаю страницу: {url}")
        driver.get(url)
        
        # Имитация человеческого поведения
        time.sleep(random.uniform(2, 4))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 2))
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(random.uniform(1, 2))
        
        # Проверяем, не заблокирована ли страница
        page_source = driver.page_source
        if '验证' in page_source or 'captcha' in page_source.lower() or 'blocked' in page_source.lower():
            print("   ⚠️ Страница может быть заблокирована (найдены ключевые слова блокировки)")
            results['blocked'] = True
        
        # Пробуем получить __NEXT_DATA__ через JavaScript
        try:
            next_data_js = driver.execute_script("return typeof window.__NEXT_DATA__ !== 'undefined' ? window.__NEXT_DATA__ : null;")
            if next_data_js:
                print("   ✅ __NEXT_DATA__ найден через JavaScript")
                if 'props' in next_data_js and 'pageProps' in next_data_js['props']:
                    page_props = next_data_js['props']['pageProps']
                    if 'skuDetail' in page_props:
                        sku_detail = page_props['skuDetail']
                        head_images = sku_detail.get('head_images', [])
                        if head_images:
                            results['image_gallery'] = head_images
                            results['image_count'] = len(head_images)
                            print(f"   ✅ Найдено {len(head_images)} изображений")
        except Exception as e:
            print(f"   ⚠️ Ошибка получения через JS: {e}")
        
        # Парсим из HTML
        soup = BeautifulSoup(page_source, 'html.parser')
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and '__NEXT_DATA__' in script.string:
                try:
                    json_start = script.string.find('{')
                    if json_start != -1:
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
                        if json_end > 0:
                            json_str = json_data[:json_end]
                            data = json.loads(json_str)
                            if 'props' in data and 'pageProps' in data['props']:
                                page_props = data['props']['pageProps']
                                if 'skuDetail' in page_props:
                                    sku_detail = page_props['skuDetail']
                                    
                                    if 'image_gallery' not in results:
                                        head_images = sku_detail.get('head_images', [])
                                        if head_images:
                                            results['image_gallery'] = head_images
                                            results['image_count'] = len(head_images)
                                            print(f"   ✅ Найдено {len(head_images)} изображений из HTML")
                                    
                                    # Дата регистрации
                                    other_params = sku_detail.get('other_params', [])
                                    for param in other_params:
                                        if param.get('name') in ('上牌时间', '首次上牌', '首次上牌时间'):
                                            results['first_registration_time'] = param.get('value')
                                            print(f"   ✅ Найдена дата регистрации: {param.get('value')}")
                                            break
                except Exception as e:
                    print(f"   ⚠️ Ошибка парсинга JSON: {e}")
        
        results['method'] = 'selenium_stealth'
        results['success'] = True
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        results = {'method': 'selenium_stealth', 'error': str(e)}
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
    
    return results


def test_playwright(car_id: str) -> Dict[str, Any]:
    """Тест парсинга через Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        print("\n⚠️ Playwright не доступен, пропускаю тест")
        return {}
    
    print("\n" + "="*70)
    print("ТЕСТ 3: Парсинг через Playwright")
    print("="*70)
    
    url = f"https://www.dongchedi.com/usedcar/{car_id}"
    results = {}
    
    try:
        with sync_playwright() as p:
            # Запускаем браузер с stealth режимом
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
            )
            
            # Добавляем stealth скрипт
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
            """)
            
            page = context.new_page()
            
            print(f"\n📡 Загружаю страницу: {url}")
            page.goto(url, wait_until='networkidle', timeout=60000)
            
            # Имитация человеческого поведения
            time.sleep(random.uniform(2, 4))
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 2))
            page.evaluate("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 2))
            
            # Пробуем получить __NEXT_DATA__ через JavaScript
            try:
                next_data_js = page.evaluate("() => typeof window.__NEXT_DATA__ !== 'undefined' ? window.__NEXT_DATA__ : null")
                if next_data_js:
                    print("   ✅ __NEXT_DATA__ найден через JavaScript")
                    if 'props' in next_data_js and 'pageProps' in next_data_js['props']:
                        page_props = next_data_js['props']['pageProps']
                        if 'skuDetail' in page_props:
                            sku_detail = page_props['skuDetail']
                            head_images = sku_detail.get('head_images', [])
                            if head_images:
                                results['image_gallery'] = head_images
                                results['image_count'] = len(head_images)
                                print(f"   ✅ Найдено {len(head_images)} изображений")
                            
                            # Дата регистрации
                            other_params = sku_detail.get('other_params', [])
                            for param in other_params:
                                if param.get('name') in ('上牌时间', '首次上牌', '首次上牌时间'):
                                    results['first_registration_time'] = param.get('value')
                                    print(f"   ✅ Найдена дата регистрации: {param.get('value')}")
                                    break
            except Exception as e:
                print(f"   ⚠️ Ошибка получения через JS: {e}")
            
            # Парсим из HTML
            page_source = page.content()
            soup = BeautifulSoup(page_source, 'html.parser')
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and '__NEXT_DATA__' in script.string:
                    try:
                        json_start = script.string.find('{')
                        if json_start != -1:
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
                            if json_end > 0:
                                json_str = json_data[:json_end]
                                data = json.loads(json_str)
                                if 'props' in data and 'pageProps' in data['props']:
                                    page_props = data['props']['pageProps']
                                    if 'skuDetail' in page_props:
                                        sku_detail = page_props['skuDetail']
                                        
                                        if 'image_gallery' not in results:
                                            head_images = sku_detail.get('head_images', [])
                                            if head_images:
                                                results['image_gallery'] = head_images
                                                results['image_count'] = len(head_images)
                                                print(f"   ✅ Найдено {len(head_images)} изображений из HTML")
                                        
                                        # Дата регистрации
                                        if 'first_registration_time' not in results:
                                            other_params = sku_detail.get('other_params', [])
                                            for param in other_params:
                                                if param.get('name') in ('上牌时间', '首次上牌', '首次上牌时间'):
                                                    results['first_registration_time'] = param.get('value')
                                                    print(f"   ✅ Найдена дата регистрации: {param.get('value')}")
                                                    break
                    except Exception as e:
                        print(f"   ⚠️ Ошибка парсинга JSON: {e}")
            
            results['method'] = 'playwright'
            results['success'] = True
            
            browser.close()
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        results = {'method': 'playwright', 'error': str(e)}
    
    return results


def test_network_interception(car_id: str) -> Dict[str, Any]:
    """Тест перехвата Network requests для поиска API endpoints"""
    if not PLAYWRIGHT_AVAILABLE:
        print("\n⚠️ Playwright не доступен, пропускаю тест")
        return {}
    
    print("\n" + "="*70)
    print("ТЕСТ 4: Перехват Network requests для поиска API endpoints")
    print("="*70)
    
    url = f"https://www.dongchedi.com/usedcar/{car_id}"
    results = {}
    api_requests = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            
            page = context.new_page()
            
            # Перехватываем все запросы
            def handle_request(request):
                if 'api' in request.url.lower() or 'json' in request.url.lower() or request.resource_type == 'xhr' or request.resource_type == 'fetch':
                    api_requests.append({
                        'url': request.url,
                        'method': request.method,
                        'headers': request.headers,
                    })
            
            def handle_response(response):
                if 'api' in response.url.lower() or 'json' in response.url.lower() or response.request.resource_type in ('xhr', 'fetch'):
                    try:
                        content_type = response.headers.get('content-type', '')
                        if 'json' in content_type:
                            body = response.body()
                            if body:
                                data = json.loads(body)
                                api_requests[-1]['response'] = data
                                api_requests[-1]['status'] = response.status
                    except:
                        pass
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            print(f"\n📡 Загружаю страницу и перехватываю запросы: {url}")
            page.goto(url, wait_until='networkidle', timeout=60000)
            time.sleep(3)  # Ждем завершения всех запросов
            
            print(f"\n   Найдено {len(api_requests)} API запросов:")
            for i, req in enumerate(api_requests[:10], 1):  # Показываем первые 10
                print(f"   {i}. {req['method']} {req['url'][:80]}...")
                if 'response' in req:
                    # Проверяем, есть ли там данные о машине
                    response_data = req['response']
                    if isinstance(response_data, dict):
                        # Ищем изображения и дату регистрации
                        if 'head_images' in str(response_data) or 'image' in str(response_data):
                            print(f"      ✅ Возможно содержит изображения")
                        if '上牌' in str(response_data) or 'registration' in str(response_data).lower():
                            print(f"      ✅ Возможно содержит дату регистрации")
            
            results['api_requests'] = api_requests
            results['method'] = 'network_interception'
            results['success'] = True
            
            browser.close()
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        results = {'method': 'network_interception', 'error': str(e)}
    
    return results


def main():
    """Главная функция для запуска всех тестов"""
    if len(sys.argv) < 2:
        print("Использование: python test_dongchedi_parsing.py <car_id>")
        print("Пример: python test_dongchedi_parsing.py 123456")
        sys.exit(1)
    
    car_id = sys.argv[1]
    print(f"\n{'='*70}")
    print(f"ТЕСТИРОВАНИЕ ПАРСИНГА DONGCHEDI ДЛЯ car_id={car_id}")
    print(f"{'='*70}")
    
    all_results = {}
    
    # Тест 1: Requests
    results1 = test_requests_parsing(car_id)
    all_results['requests'] = results1
    
    # Тест 2: Selenium stealth
    results2 = test_selenium_stealth(car_id)
    all_results['selenium_stealth'] = results2
    
    # Тест 3: Playwright
    results3 = test_playwright(car_id)
    all_results['playwright'] = results3
    
    # Тест 4: Network interception
    results4 = test_network_interception(car_id)
    all_results['network_interception'] = results4
    
    # Итоговый отчет
    print("\n" + "="*70)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*70)
    
    for method, results in all_results.items():
        print(f"\n{method.upper()}:")
        if isinstance(results, dict):
            if 'error' in results:
                print(f"  ❌ Ошибка: {results['error']}")
            elif 'image_gallery' in results:
                print(f"  ✅ Найдено изображений: {results.get('image_count', len(results['image_gallery']))}")
            elif 'image_count' in results:
                print(f"  ✅ Найдено изображений: {results['image_count']}")
            if 'first_registration_time' in results:
                print(f"  ✅ Дата регистрации: {results['first_registration_time']}")
            if 'api_requests' in results:
                print(f"  ✅ Найдено API запросов: {len(results['api_requests'])}")
        elif isinstance(results, dict) and isinstance(list(results.values())[0], dict):
            for url, data in results.items():
                if isinstance(data, dict) and 'image_count' in data:
                    print(f"  ✅ {url}: {data['image_count']} изображений")
    
    # Сохраняем результаты в файл
    with open(f'test_results_dongchedi_{car_id}.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Результаты сохранены в test_results_dongchedi_{car_id}.json")


if __name__ == "__main__":
    main()











