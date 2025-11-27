#!/usr/bin/env python3
"""
Тестовый скрипт для анализа парсинга che168.com
Проверяет разные способы извлечения данных о мощности
"""

import json
import re
import time
import os
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup

# Тестовые car_id (реальные машины с che168)
TEST_CAR_IDS = [56305293, 56915531, 56915528, 56915533]

def test_mobile_playwright(car_id: int) -> Dict[str, Any]:
    """Тест мобильной версии с Playwright"""
    from playwright.sync_api import sync_playwright
    
    mobile_url = f"https://m.che168.com/cardetail/index?infoid={car_id}"
    result = {
        "method": "mobile_playwright",
        "car_id": car_id,
        "url": mobile_url,
        "success": False,
        "api_responses": [],
        "power": None,
        "engine_info": None,
        "fields_found": {},
        "errors": []
    }
    
    print(f"\n{'='*60}")
    print(f"[MOBILE] Тестирование car_id: {car_id}")
    print(f"URL: {mobile_url}")
    print('='*60)
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                viewport={'width': 390, 'height': 844},
                locale='zh-CN',
                timezone_id='Asia/Shanghai'
            )
            
            page = context.new_page()
            
            # Перехватываем API ответы
            api_responses = []
            
            def handle_response(response):
                try:
                    url = response.url
                    if any(kw in url.lower() for kw in ['api', 'getparam', 'carinfo', 'detail']):
                        try:
                            content_type = response.headers.get('content-type', '')
                            if 'json' in content_type or 'application' in content_type:
                                json_data = response.json()
                                api_responses.append({
                                    'url': url,
                                    'data': json_data,
                                    'size': len(str(json_data))
                                })
                                print(f"  ✓ Перехвачен API: {url[:80]}... ({len(str(json_data))} bytes)")
                        except:
                            pass
                except:
                    pass
            
            page.on("response", handle_response)
            
            # Загружаем страницу
            response = page.goto(mobile_url, wait_until='networkidle', timeout=60000)
            time.sleep(5)
            
            # Прокрутка
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
            html = page.content()
            result["html_size"] = len(html)
            result["api_responses"] = api_responses
            
            # Анализируем API ответы
            print(f"\n  Всего API ответов: {len(api_responses)}")
            for api in api_responses:
                print(f"\n  --- Анализ API: {api['url'][:60]}...")
                analyze_api_response(api['data'], result)
            
            # Анализируем HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем мощность в HTML
            page_text = soup.get_text()
            power_patterns = [
                (r'(\d+)\s*马力', '马力'),
                (r'(\d+)\s*Ps', 'Ps'),
                (r'(\d+)\s*kW', 'kW'),
                (r'最大马力[^0-9]*(\d+)', '最大马力'),
                (r'最大功率[^0-9]*(\d+)', '最大功率'),
            ]
            
            for pattern, label in power_patterns:
                match = re.search(pattern, page_text)
                if match:
                    print(f"  ✓ Найдено в HTML: {label} = {match.group(1)}")
                    result["power"] = match.group(1)
                    break
            
            if not result["power"]:
                print(f"  ✗ Мощность НЕ найдена в HTML")
                # Проверяем наличие ключевых слов
                for kw in ['马力', '功率', 'power', 'Ps', 'kW']:
                    if kw in page_text:
                        print(f"    - Найдено ключевое слово '{kw}' в тексте")
            
            result["success"] = True
            browser.close()
            
        except Exception as e:
            result["errors"].append(str(e))
            print(f"  ✗ Ошибка: {e}")
    
    return result


def test_desktop_playwright(car_id: int) -> Dict[str, Any]:
    """Тест десктопной версии с Playwright"""
    from playwright.sync_api import sync_playwright
    
    desktop_url = f"https://www.che168.com/dealer/557461/{car_id}.html"
    result = {
        "method": "desktop_playwright",
        "car_id": car_id,
        "url": desktop_url,
        "success": False,
        "api_responses": [],
        "power": None,
        "engine_info": None,
        "fields_found": {},
        "errors": []
    }
    
    print(f"\n{'='*60}")
    print(f"[DESKTOP] Тестирование car_id: {car_id}")
    print(f"URL: {desktop_url}")
    print('='*60)
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai'
            )
            
            page = context.new_page()
            
            api_responses = []
            
            def handle_response(response):
                try:
                    url = response.url
                    if any(kw in url.lower() for kw in ['api', 'getparam', 'carinfo', 'detail', 'config']):
                        try:
                            content_type = response.headers.get('content-type', '')
                            if 'json' in content_type or 'application' in content_type:
                                json_data = response.json()
                                api_responses.append({
                                    'url': url,
                                    'data': json_data,
                                    'size': len(str(json_data))
                                })
                                print(f"  ✓ Перехвачен API: {url[:80]}... ({len(str(json_data))} bytes)")
                        except:
                            pass
                except:
                    pass
            
            page.on("response", handle_response)
            
            response = page.goto(desktop_url, wait_until='networkidle', timeout=60000)
            time.sleep(5)
            
            # Проверяем на ошибку
            page_title = page.title()
            page_content = page.content()
            
            if '访问出错了' in page_title or '出错' in page_content[:1000]:
                print(f"  ⚠ Страница показывает ошибку: {page_title}")
                result["errors"].append(f"Page error: {page_title}")
            else:
                print(f"  Страница загружена: {page_title[:50]}")
            
            html = page.content()
            result["html_size"] = len(html)
            result["api_responses"] = api_responses
            result["page_title"] = page_title
            
            # Анализируем API ответы
            print(f"\n  Всего API ответов: {len(api_responses)}")
            for api in api_responses:
                print(f"\n  --- Анализ API: {api['url'][:60]}...")
                analyze_api_response(api['data'], result)
            
            # Анализируем HTML
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            # Ищем мощность
            power_patterns = [
                (r'(\d+)\s*马力', '马力'),
                (r'(\d+)\s*Ps', 'Ps'),
                (r'(\d+)\s*kW', 'kW'),
                (r'最大马力[^0-9]*(\d+)', '最大马力'),
            ]
            
            for pattern, label in power_patterns:
                match = re.search(pattern, page_text)
                if match:
                    print(f"  ✓ Найдено в HTML: {label} = {match.group(1)}")
                    result["power"] = match.group(1)
                    break
            
            if not result["power"]:
                print(f"  ✗ Мощность НЕ найдена в HTML")
            
            result["success"] = True
            browser.close()
            
        except Exception as e:
            result["errors"].append(str(e))
            print(f"  ✗ Ошибка: {e}")
    
    return result


def test_params_page(car_id: int) -> Dict[str, Any]:
    """Тест страницы параметров (全部参数配置)"""
    from playwright.sync_api import sync_playwright
    
    # Пробуем разные URL для страницы параметров
    params_urls = [
        f"https://m.che168.com/cardetail/params?infoid={car_id}",
        f"https://m.che168.com/v9/car/carparams.html?infoid={car_id}",
        f"https://www.che168.com/usedcar/info/detail/{car_id}.html",
    ]
    
    result = {
        "method": "params_page",
        "car_id": car_id,
        "success": False,
        "api_responses": [],
        "power": None,
        "errors": []
    }
    
    print(f"\n{'='*60}")
    print(f"[PARAMS PAGE] Тестирование car_id: {car_id}")
    print('='*60)
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
                viewport={'width': 390, 'height': 844},
                locale='zh-CN'
            )
            
            page = context.new_page()
            
            api_responses = []
            
            def handle_response(response):
                try:
                    url = response.url
                    if 'getparamtypeitems' in url.lower() or 'param' in url.lower():
                        try:
                            json_data = response.json()
                            api_responses.append({
                                'url': url,
                                'data': json_data,
                                'size': len(str(json_data))
                            })
                            print(f"  ✓ Перехвачен PARAMS API: {url[:80]}...")
                        except:
                            pass
                except:
                    pass
            
            page.on("response", handle_response)
            
            for url in params_urls:
                print(f"\n  Пробуем URL: {url}")
                try:
                    response = page.goto(url, wait_until='networkidle', timeout=30000)
                    if response and response.status == 200:
                        time.sleep(3)
                        html = page.content()
                        if '访问出错' not in html and len(html) > 5000:
                            print(f"    ✓ Страница загружена ({len(html)} bytes)")
                            result["url"] = url
                            result["html_size"] = len(html)
                            
                            # Ищем мощность
                            soup = BeautifulSoup(html, 'html.parser')
                            page_text = soup.get_text()
                            
                            power_match = re.search(r'(\d+)\s*(?:马力|Ps|kW)', page_text)
                            if power_match:
                                result["power"] = power_match.group(1)
                                print(f"    ✓ Мощность найдена: {power_match.group(0)}")
                            
                            result["success"] = True
                            break
                        else:
                            print(f"    ✗ Страница с ошибкой или пустая")
                    else:
                        print(f"    ✗ Статус: {response.status if response else 'None'}")
                except Exception as e:
                    print(f"    ✗ Ошибка: {e}")
            
            result["api_responses"] = api_responses
            
            # Анализируем API ответы
            for api in api_responses:
                print(f"\n  --- Детальный анализ PARAMS API ---")
                analyze_api_response(api['data'], result, verbose=True)
            
            browser.close()
            
        except Exception as e:
            result["errors"].append(str(e))
            print(f"  ✗ Ошибка: {e}")
    
    return result


def analyze_api_response(data: Any, result: Dict, verbose: bool = False, path: str = ""):
    """Рекурсивный анализ API ответа для поиска мощности"""
    
    power_keywords = ['power', 'horsepower', '马力', '功率', 'maxpower', 'hp', 'ps', 'kw']
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            key_lower = key.lower()
            
            # Ищем ключи связанные с мощностью
            if any(kw in key_lower for kw in power_keywords):
                if value and str(value) not in ['', '-', '0', 'null', 'None']:
                    print(f"    ★ НАЙДЕНО: {current_path} = {value}")
                    if result.get("power") is None:
                        # Извлекаем число
                        num_match = re.search(r'(\d+)', str(value))
                        if num_match:
                            result["power"] = num_match.group(1)
                elif verbose:
                    print(f"    - {current_path} = {value} (пусто)")
            
            # Ищем поля с техническими характеристиками
            if any(kw in key_lower for kw in ['engine', 'motor', 'spec', 'param', 'config', 'items']):
                if verbose:
                    print(f"    ? Потенциально интересный ключ: {current_path}")
            
            # Рекурсия
            if isinstance(value, (dict, list)):
                analyze_api_response(value, result, verbose, current_path)
                
    elif isinstance(data, list):
        for i, item in enumerate(data):
            analyze_api_response(item, result, verbose, f"{path}[{i}]")


def test_direct_api(car_id: int) -> Dict[str, Any]:
    """Тест прямых API запросов"""
    import requests
    
    result = {
        "method": "direct_api",
        "car_id": car_id,
        "success": False,
        "power": None,
        "errors": []
    }
    
    print(f"\n{'='*60}")
    print(f"[DIRECT API] Тестирование car_id: {car_id}")
    print('='*60)
    
    # API endpoints для тестирования
    apis = [
        {
            "name": "getparamtypeitems",
            "url": f"https://apiuscdt.che168.com/api/v1/car/getparamtypeitems",
            "params": {"infoid": car_id, "deviceid": "test123", "_appid": "2sc.m"}
        },
        {
            "name": "getcarinfo",
            "url": f"https://apiuscdt.che168.com/apic/v2/car/getcarinfo",
            "params": {"infoid": car_id, "deviceid": "test123", "_appid": "2sc.m"}
        },
        {
            "name": "getcarinfoext",
            "url": f"https://apiuscdt.che168.com/apic/v2/car/getcarinfoext",
            "params": {"infoid": car_id, "deviceid": "test123", "_appid": "2sc.m"}
        },
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "Accept": "application/json",
        "Referer": f"https://m.che168.com/cardetail/index?infoid={car_id}"
    }
    
    for api in apis:
        print(f"\n  Тестируем API: {api['name']}")
        try:
            resp = requests.get(api['url'], params=api['params'], headers=headers, timeout=10)
            print(f"    Status: {resp.status_code}")
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"    Response size: {len(str(data))} bytes")
                    
                    if data.get('returncode') == 0 or data.get('result'):
                        print(f"    ✓ Успешный ответ")
                        analyze_api_response(data, result, verbose=True)
                        result["success"] = True
                    else:
                        print(f"    ✗ Ошибка: {data.get('message', 'unknown')}")
                except:
                    print(f"    ✗ Не JSON ответ")
            
        except Exception as e:
            print(f"    ✗ Ошибка: {e}")
    
    return result


def test_autohome_api(car_id: int) -> Dict[str, Any]:
    """Тест API autohome.com.cn для получения спецификаций"""
    from playwright.sync_api import sync_playwright
    
    result = {
        "method": "autohome_specs",
        "car_id": car_id,
        "success": False,
        "power": None,
        "errors": []
    }
    
    print(f"\n{'='*60}")
    print(f"[AUTOHOME SPECS] Тестирование car_id: {car_id}")
    print('='*60)
    
    # Сначала получаем spec_id из страницы машины
    with sync_playwright() as p:
        try:
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
            
            # Ищем specid в API ответах
            spec_id = None
            
            def handle_response(response):
                nonlocal spec_id
                try:
                    url = response.url
                    if 'carinfo' in url.lower():
                        data = response.json()
                        # Ищем specid в ответе
                        spec_id = find_in_dict(data, ['specid', 'spec_id', 'specId'])
                        if spec_id:
                            print(f"    ✓ Найден specid: {spec_id}")
                except:
                    pass
            
            page.on("response", handle_response)
            
            mobile_url = f"https://m.che168.com/cardetail/index?infoid={car_id}"
            page.goto(mobile_url, wait_until='networkidle', timeout=30000)
            time.sleep(3)
            
            if spec_id:
                # Пробуем получить спецификации с autohome
                specs_url = f"https://car.autohome.com.cn/config/spec/{spec_id}.html"
                print(f"  Загружаем спецификации: {specs_url}")
                
                page.goto(specs_url, wait_until='networkidle', timeout=30000)
                time.sleep(2)
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                page_text = soup.get_text()
                
                # Ищем мощность
                power_match = re.search(r'最大马力[^\d]*(\d+)', page_text)
                if power_match:
                    result["power"] = power_match.group(1)
                    print(f"    ✓ Мощность из autohome: {power_match.group(1)}Ps")
                    result["success"] = True
            else:
                print(f"  ✗ specid не найден")
            
            browser.close()
            
        except Exception as e:
            result["errors"].append(str(e))
            print(f"  ✗ Ошибка: {e}")
    
    return result


def find_in_dict(data: Any, keys: List[str], path: str = "") -> Any:
    """Рекурсивный поиск ключа в словаре"""
    if isinstance(data, dict):
        for key, value in data.items():
            if key.lower() in [k.lower() for k in keys]:
                return value
            if isinstance(value, (dict, list)):
                found = find_in_dict(value, keys)
                if found:
                    return found
    elif isinstance(data, list):
        for item in data:
            found = find_in_dict(item, keys)
            if found:
                return found
    return None


def main():
    """Основная функция тестирования"""
    print("\n" + "="*80)
    print("  ТЕСТИРОВАНИЕ ПАРСИНГА CHE168.COM")
    print("  Цель: найти способ извлечения мощности (power/马力)")
    print("="*80)
    
    results = []
    car_id = TEST_CAR_IDS[0]  # Используем первый тестовый ID
    
    print(f"\nТестируем car_id: {car_id}")
    
    # Тест 1: Мобильная версия
    print("\n" + "="*80)
    print("ТЕСТ 1: МОБИЛЬНАЯ ВЕРСИЯ (m.che168.com)")
    print("="*80)
    r1 = test_mobile_playwright(car_id)
    results.append(r1)
    
    # Тест 2: Десктопная версия
    print("\n" + "="*80)
    print("ТЕСТ 2: ДЕСКТОПНАЯ ВЕРСИЯ (www.che168.com)")
    print("="*80)
    r2 = test_desktop_playwright(car_id)
    results.append(r2)
    
    # Тест 3: Страница параметров
    print("\n" + "="*80)
    print("ТЕСТ 3: СТРАНИЦА ПАРАМЕТРОВ")
    print("="*80)
    r3 = test_params_page(car_id)
    results.append(r3)
    
    # Тест 4: Прямые API запросы
    print("\n" + "="*80)
    print("ТЕСТ 4: ПРЯМЫЕ API ЗАПРОСЫ")
    print("="*80)
    r4 = test_direct_api(car_id)
    results.append(r4)
    
    # Тест 5: AutoHome спецификации
    print("\n" + "="*80)
    print("ТЕСТ 5: AUTOHOME СПЕЦИФИКАЦИИ")
    print("="*80)
    r5 = test_autohome_api(car_id)
    results.append(r5)
    
    # Итоги
    print("\n" + "="*80)
    print("  ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*80)
    
    for r in results:
        status = "✓" if r.get("power") else "✗"
        print(f"\n{status} {r['method']}:")
        print(f"   Power: {r.get('power', 'НЕ НАЙДЕНО')}")
        if r.get("errors"):
            print(f"   Errors: {r['errors'][:2]}")
    
    # Сохраняем результаты
    with open('/tmp/che168_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nРезультаты сохранены в /tmp/che168_test_results.json")


if __name__ == "__main__":
    main()

