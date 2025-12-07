#!/usr/bin/env python3
"""
Тестирование различных методов получения image_gallery для CHE168.
Цель: найти рабочий способ получения галереи изображений.
"""

import json
import re
import time
import random
import logging
import os
from typing import Optional, Dict, Any, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Тестовые car_id (актуальные объявления, если не заданы через ENV)
TEST_CAR_IDS = [
    45678901,
    45678902,
    45678903,
]

# User-Agent варианты
USER_AGENTS = {
    'mobile_android': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'mobile_ios': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'desktop_chrome': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'desktop_firefox': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
}

results = {}


def get_real_car_ids():
    """Получает реальные car_id с сайта через поиск."""
    import requests
    
    try:
        # Пробуем получить список машин с мобильной версии
        url = "https://m.che168.com/beijing/list/"
        headers = {
            'User-Agent': USER_AGENTS['mobile_android'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        logger.info(f"Поиск машин: status={response.status_code}")
        
        if response.status_code == 200:
            # Ищем car_id в HTML
            car_ids = re.findall(r'infoid[=:](\d+)', response.text)
            if car_ids:
                unique_ids = list(set([int(cid) for cid in car_ids]))[:5]
                logger.info(f"Найдено {len(unique_ids)} реальных car_id: {unique_ids}")
                return unique_ids
    except Exception as e:
        logger.error(f"Ошибка получения списка машин: {e}")
    
    return TEST_CAR_IDS


def get_env_car_ids() -> List[int]:
    """
    Позволяет переопределить список car_id через переменную окружения CAR_IDS.
    Формат: CAR_IDS="id1,id2,id3"
    """
    raw = os.environ.get("CAR_IDS")
    if not raw:
        return []
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def test_api_direct(car_id: int) -> Dict[str, Any]:
    """Метод 1: Прямой API запрос getcarinfo."""
    import requests
    
    result = {'method': 'api_direct', 'success': False, 'gallery': None, 'count': 0, 'error': None}
    
    try:
        url = "https://apiuscdt.che168.com/apic/v2/car/getcarinfo"
        params = {
            "infoid": car_id,
            "deviceid": f"test_{car_id}_{random.randint(1000, 9999)}",
            "_appid": "2sc.m"
        }
        headers = {
            'User-Agent': USER_AGENTS['mobile_android'],
            'Accept': 'application/json',
            'Referer': f'https://m.che168.com/cardetail/index?infoid={car_id}',
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        result['status_code'] = response.status_code
        
        if response.status_code == 403:
            result['error'] = '403 Forbidden - API заблокирован'
            logger.warning(f"API Direct: 403 для car_id={car_id}")
            return result
        
        if response.status_code == 200:
            data = response.json()
            if data.get('returncode') == 0:
                res = data.get('result', {})
                
                # Ищем изображения в разных полях
                images = []
                for field in ['piclist', 'head_images', 'images', 'picurl']:
                    if field in res and res[field]:
                        if isinstance(res[field], list):
                            images = res[field]
                            break
                        elif isinstance(res[field], str):
                            images = [res[field]]
                            break
                
                if images:
                    result['success'] = True
                    result['gallery'] = ' '.join(images[:5])  # Первые 5
                    result['count'] = len(images)
                    logger.info(f"API Direct: УСПЕХ! {len(images)} изображений для car_id={car_id}")
                else:
                    result['error'] = 'Изображения не найдены в ответе API'
            else:
                result['error'] = f"returncode != 0: {data.get('returnmsg')}"
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"API Direct ошибка: {e}")
    
    return result


def test_selenium_mobile(car_id: int) -> Dict[str, Any]:
    """Метод 2: Selenium с мобильной версией + __NEXT_DATA__."""
    result = {'method': 'selenium_mobile', 'success': False, 'gallery': None, 'count': 0, 'error': None}
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        import tempfile
        import shutil
        import os
        
        url = f'https://m.che168.com/cardetail/index?infoid={car_id}'
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"--user-agent={USER_AGENTS['mobile_android']}")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        
        driver = None
        try:
            driver_path = os.environ.get("CHROMEDRIVER_PATH")
            if driver_path:
                driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            
            # Удаляем webdriver флаг
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                '''
            })
            
            driver.get(url)
            
            # Ждем загрузки
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except:
                pass
            
            time.sleep(3)
            
            # Прокрутка
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Метод 1: Через JavaScript window.__NEXT_DATA__
            try:
                next_data = driver.execute_script("return window.__NEXT_DATA__;")
                if next_data and 'props' in next_data:
                    page_props = next_data.get('props', {}).get('pageProps', {})
                    if 'skuDetail' in page_props:
                        sku_detail = page_props['skuDetail']
                        if 'head_images' in sku_detail and sku_detail['head_images']:
                            images = sku_detail['head_images']
                            if isinstance(images, list) and len(images) > 0:
                                result['success'] = True
                                result['gallery'] = ' '.join(images[:5])
                                result['count'] = len(images)
                                result['source'] = 'window.__NEXT_DATA__'
                                logger.info(f"Selenium Mobile (JS): УСПЕХ! {len(images)} изображений")
                                return result
            except Exception as e:
                logger.debug(f"JS __NEXT_DATA__ не найден: {e}")
            
            # Метод 2: Парсинг HTML
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and '__NEXT_DATA__' in script.string:
                    try:
                        json_match = re.search(r'\{.*\}', script.string, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group())
                            if 'props' in data:
                                page_props = data.get('props', {}).get('pageProps', {})
                                if 'skuDetail' in page_props:
                                    sku_detail = page_props['skuDetail']
                                    if 'head_images' in sku_detail:
                                        images = sku_detail['head_images']
                                        if isinstance(images, list) and len(images) > 0:
                                            result['success'] = True
                                            result['gallery'] = ' '.join(images[:5])
                                            result['count'] = len(images)
                                            result['source'] = 'HTML script tag'
                                            logger.info(f"Selenium Mobile (HTML): УСПЕХ! {len(images)} изображений")
                                            return result
                    except:
                        continue
            
            # Метод 3: CSS селекторы для изображений
            image_selectors = [
                'img[src*="car"]', 'img[src*="auto"]', 'img[src*="2sc"]',
                '.car-image img', '[class*="gallery"] img', '[class*="photo"] img'
            ]
            
            images_found = []
            for selector in image_selectors:
                try:
                    elements = soup.select(selector)
                    for img in elements:
                        src = img.get('src') or img.get('data-src')
                        if src and 'http' in src and src not in images_found:
                            images_found.append(src)
                except:
                    continue
            
            if images_found:
                result['success'] = True
                result['gallery'] = ' '.join(images_found[:5])
                result['count'] = len(images_found)
                result['source'] = 'CSS selectors'
                logger.info(f"Selenium Mobile (CSS): УСПЕХ! {len(images_found)} изображений")
                return result
            
            result['error'] = '__NEXT_DATA__ не найден, CSS селекторы не нашли изображений'
            
        finally:
            if driver:
                driver.quit()
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Selenium Mobile ошибка: {e}")
    
    return result


def test_selenium_desktop(car_id: int) -> Dict[str, Any]:
    """Метод 3: Selenium с десктоп версией."""
    result = {'method': 'selenium_desktop', 'success': False, 'gallery': None, 'count': 0, 'error': None}
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.by import By
        import tempfile
        import shutil
        import os
        
        # Десктоп URL
        url = f'https://www.che168.com/dealer/330776/{car_id}.html'
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"--user-agent={USER_AGENTS['desktop_chrome']}")
        chrome_options.add_argument("--window-size=1920,1080")
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
            
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
            })
            
            driver.get(url)
            
            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except:
                pass
            
            time.sleep(3)
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Ищем галерею на десктоп версии
            image_selectors = [
                '.car-thumb img', '.car-pic img', '.pic-list img',
                '.gallery img', '.photo-list img', '.slider img',
                'img[src*="autoimg"]', 'img[src*="che168"]'
            ]
            
            images_found = []
            for selector in image_selectors:
                try:
                    elements = soup.select(selector)
                    for img in elements:
                        src = img.get('src') or img.get('data-src') or img.get('data-original')
                        if src:
                            if src.startswith('//'):
                                src = 'https:' + src
                            if 'http' in src and src not in images_found:
                                images_found.append(src)
                except:
                    continue
            
            if images_found:
                result['success'] = True
                result['gallery'] = ' '.join(images_found[:5])
                result['count'] = len(images_found)
                logger.info(f"Selenium Desktop: УСПЕХ! {len(images_found)} изображений")
            else:
                result['error'] = 'Изображения не найдены на десктоп версии'
                
        finally:
            if driver:
                driver.quit()
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Selenium Desktop ошибка: {e}")
    
    return result


def test_requests_mobile(car_id: int) -> Dict[str, Any]:
    """Метод 4: Requests с мобильной версией (без Selenium)."""
    import requests
    from bs4 import BeautifulSoup
    
    result = {'method': 'requests_mobile', 'success': False, 'gallery': None, 'count': 0, 'error': None}
    
    try:
        url = f'https://m.che168.com/cardetail/index?infoid={car_id}'
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': USER_AGENTS['mobile_ios'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://m.che168.com/',
            'Connection': 'keep-alive',
        })
        
        response = session.get(url, timeout=15)
        result['status_code'] = response.status_code
        
        if response.status_code != 200:
            result['error'] = f'HTTP {response.status_code}'
            return result
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем __NEXT_DATA__
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        if script_tag and script_tag.string:
            try:
                data = json.loads(script_tag.string)
                if 'props' in data:
                    page_props = data.get('props', {}).get('pageProps', {})
                    if 'skuDetail' in page_props:
                        sku_detail = page_props['skuDetail']
                        if 'head_images' in sku_detail:
                            images = sku_detail['head_images']
                            if isinstance(images, list) and len(images) > 0:
                                result['success'] = True
                                result['gallery'] = ' '.join(images[:5])
                                result['count'] = len(images)
                                logger.info(f"Requests Mobile: УСПЕХ! {len(images)} изображений")
                                return result
            except:
                pass
        
        result['error'] = '__NEXT_DATA__ не найден в HTML'
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Requests Mobile ошибка: {e}")
    
    return result


def test_api_alternative(car_id: int) -> Dict[str, Any]:
    """Метод 5: Альтернативные API endpoints."""
    import requests
    
    result = {'method': 'api_alternative', 'success': False, 'gallery': None, 'count': 0, 'error': None}
    
    # Список альтернативных API endpoints
    endpoints = [
        {
            'url': 'https://mapi.che168.com/v1/car/getCarDetail',
            'params': {'infoid': car_id}
        },
        {
            'url': 'https://m.che168.com/Handler/usedcar/GetCarInfo.ashx',
            'params': {'infoid': car_id, 'action': 'getinfo'}
        },
        {
            'url': f'https://m.che168.com/cardetail/getCarInfo?infoid={car_id}',
            'params': {}
        },
    ]
    
    headers = {
        'User-Agent': USER_AGENTS['mobile_android'],
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': f'https://m.che168.com/cardetail/index?infoid={car_id}',
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    for endpoint in endpoints:
        try:
            response = requests.get(
                endpoint['url'],
                params=endpoint['params'],
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Ищем изображения в ответе
                    def find_images(obj, depth=0):
                        if depth > 5:
                            return []
                        images = []
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if key in ['head_images', 'piclist', 'images', 'photos', 'gallery']:
                                    if isinstance(value, list):
                                        images.extend(value)
                                else:
                                    images.extend(find_images(value, depth + 1))
                        elif isinstance(obj, list):
                            for item in obj:
                                images.extend(find_images(item, depth + 1))
                        return images
                    
                    images = find_images(data)
                    if images:
                        result['success'] = True
                        result['gallery'] = ' '.join(images[:5])
                        result['count'] = len(images)
                        result['endpoint'] = endpoint['url']
                        logger.info(f"API Alternative ({endpoint['url']}): УСПЕХ! {len(images)} изображений")
                        return result
                except:
                    pass
        except Exception as e:
            logger.debug(f"Endpoint {endpoint['url']} не работает: {e}")
            continue
    
    result['error'] = 'Все альтернативные API не вернули изображения'
    return result


def test_existing_parser(car_id: int) -> Dict[str, Any]:
    """Метод 6: Использование существующего che168/parser.py."""
    result = {'method': 'existing_parser', 'success': False, 'gallery': None, 'count': 0, 'error': None}
    
    try:
        import sys
        sys.path.insert(0, '/app')
        
        from api.che168.parser import Che168Parser
        
        parser = Che168Parser(headless=True)
        car_obj, meta = parser.fetch_car_detail(car_id)
        
        if car_obj:
            gallery = getattr(car_obj, 'image_gallery', None)
            if gallery:
                images = gallery.split(' ')
                result['success'] = True
                result['gallery'] = gallery[:200]  # Первые 200 символов
                result['count'] = len(images)
                logger.info(f"Existing Parser: УСПЕХ! {len(images)} изображений")
            else:
                result['error'] = 'car_obj получен, но image_gallery пуст'
        else:
            result['error'] = f"fetch_car_detail вернул None. Meta: {meta}"
            
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Existing Parser ошибка: {e}")
    
    return result


def main():
    """Основная функция тестирования."""
    logger.info("=" * 60)
    logger.info("ТЕСТИРОВАНИЕ МЕТОДОВ ПОЛУЧЕНИЯ ГАЛЕРЕИ CHE168")
    logger.info("=" * 60)
    
    # Получаем car_id: сначала из ENV, иначе — с сайта, иначе — тестовые
    car_ids = get_env_car_ids()
    if not car_ids:
        car_ids = get_real_car_ids()
    
    if not car_ids:
        logger.error("Не удалось получить car_id для тестирования")
        return
    
    methods = [
        ('1. API Direct (getcarinfo)', test_api_direct),
        ('2. Selenium Mobile (__NEXT_DATA__)', test_selenium_mobile),
        ('3. Selenium Desktop', test_selenium_desktop),
        ('4. Requests Mobile (без Selenium)', test_requests_mobile),
        ('5. API Alternative endpoints', test_api_alternative),
        ('6. Existing Parser (che168/parser.py)', test_existing_parser),
    ]
    
    results = []

    for test_car_id in car_ids:
        logger.info(f"\nТестирование car_id: {test_car_id}")
        logger.info("-" * 40)

        for name, method in methods:
            logger.info(f"\n>>> Тестирование: {name}")
            try:
                result = method(test_car_id)
                result['test_name'] = name
                result['car_id'] = test_car_id
                results.append(result)
                
                if result['success']:
                    logger.info(f"✅ УСПЕХ: {result['count']} изображений")
                    logger.info(f"   Галерея (первые 100 символов): {result.get('gallery', '')[:100]}...")
                else:
                    logger.warning(f"❌ НЕУДАЧА: {result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"❌ ОШИБКА: {e}")
                results.append({'test_name': name, 'car_id': test_car_id, 'success': False, 'error': str(e)})
            
            time.sleep(2)  # Пауза между тестами
    
    # Итоговый отчет
    logger.info("\n" + "=" * 60)
    logger.info("ИТОГОВЫЙ ОТЧЕТ")
    logger.info("=" * 60)
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    logger.info(f"\n✅ УСПЕШНЫХ МЕТОДОВ: {len(successful)}")
    for r in successful:
        logger.info(f"   - {r['test_name']}: {r.get('count', 0)} изображений")
    
    logger.info(f"\n❌ НЕУДАЧНЫХ МЕТОДОВ: {len(failed)}")
    for r in failed:
        logger.info(f"   - {r['test_name']}: {r.get('error', 'Unknown')}")
    
    # Сохраняем результаты
    with open('/app/test_results/che168_gallery_results.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info("\nРезультаты сохранены в /app/test_results/che168_gallery_results.json")
    
    # Рекомендации
    if successful:
        logger.info("\n" + "=" * 60)
        logger.info("РЕКОМЕНДАЦИИ")
        logger.info("=" * 60)
        logger.info("Рабочие методы для получения галереи:")
        for r in successful:
            logger.info(f"  ✅ {r['test_name']}")
    else:
        logger.warning("\n⚠️ НИ ОДИН МЕТОД НЕ РАБОТАЕТ!")
        logger.warning("Возможные причины:")
        logger.warning("  1. CHE168 полностью блокирует все запросы")
        logger.warning("  2. Нужны прокси или VPN")
        logger.warning("  3. Нужна ротация IP адресов")


if __name__ == '__main__':
    import os
    os.makedirs('/app/test_results', exist_ok=True)
    main()


