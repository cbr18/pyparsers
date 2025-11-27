"""
Парсер детальной информации с che168.com используя Playwright для обхода детекта
"""

import os
import time
import random
import logging
import json
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout, Page
from .models.detailed_car import Che168DetailedCar
from api.date_utils import normalize_first_registration_date

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Che168DetailedParserPlaywright:
    """Парсер детальной информации используя Playwright"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
    
    def parse_car_details(self, car_id: int) -> Optional[Che168DetailedCar]:
        """
        Парсит детальную информацию используя Playwright + Desktop версию
        
        Args:
            car_id: ID машины
            
        Returns:
            Che168DetailedCar или None
        """
        # Используем mobile URL - desktop показывает ошибку "访问出错了"
        # Mobile URL работает и используется в других парсерах
        mobile_url = f"https://m.che168.com/cardetail/index?infoid={car_id}"
        
        logger.info(f"[Playwright] Парсинг car_id: {car_id}, используем mobile URL: {mobile_url}")
        
        with sync_playwright() as p:
            browser = None
            try:
                # Запускаем браузер
                logger.info("[Playwright] Запуск браузера...")
                browser = p.chromium.launch(
                    headless=self.headless,
                    executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                
                # Создаем контекст DESKTOP
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-CN',
                    timezone_id='Asia/Shanghai'
                )
                
                page = context.new_page()
                
                # Перехватываем сетевые запросы для извлечения данных из API
                api_responses = []
                all_requests = []  # Для отладки - логируем все запросы
                
                def handle_request(request):
                    """Обработчик запросов - для отладки"""
                    url = request.url
                    all_requests.append(url)
                    # Логируем только потенциально интересные запросы
                    if any(keyword in url.lower() for keyword in ['api', 'detail', 'cardetail', 'car', 'info', 'data', 'sku', 'vehicle', 'spec', 'config', 'ajax', 'json']):
                        logger.debug(f"[Playwright] Запрос: {url[:120]}")
                
                def handle_response(response):
                    """Обработчик ответов от API"""
                    try:
                        url = response.url
                        # Ищем API запросы, которые могут содержать данные о машине
                        # Расширяем список ключевых слов для поиска API
                        api_keywords = ['api', 'detail', 'cardetail', 'car', 'info', 'data', 'sku', 'vehicle', 'spec', 'config', 'ajax', 'json']
                        if any(keyword in url.lower() for keyword in api_keywords):
                            # Пробуем получить JSON из ответа
                            try:
                                # Проверяем Content-Type
                                content_type = response.headers.get('content-type', '')
                                if 'json' in content_type.lower() or 'application' in content_type.lower() or 'text' in content_type.lower():
                                    json_data = response.json()
                                    if json_data:
                                        api_responses.append({
                                            'url': url,
                                            'data': json_data
                                        })
                                        logger.info(f"[Playwright] ✓ Перехвачен API ответ: {url[:100]} (размер: {len(str(json_data))} символов)")
                            except Exception as json_error:
                                # Не JSON или ошибка парсинга, пробуем как текст
                                try:
                                    text = response.text()
                                    if text and len(text) > 100:  # Только если достаточно большой ответ
                                        # Пробуем найти JSON в тексте
                                        # Ищем JSON объекты в тексте
                                        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
                                        if json_match:
                                            json_data = json.loads(json_match.group(0))
                                            api_responses.append({
                                                'url': url,
                                                'data': json_data
                                            })
                                            logger.info(f"[Playwright] ✓ Перехвачен JSON из текста: {url[:100]}")
                                except:
                                    logger.debug(f"[Playwright] Не JSON ответ: {url[:80]}")
                    except Exception as e:
                        logger.debug(f"[Playwright] Ошибка при перехвате ответа: {e}")
                
                # Устанавливаем обработчики ДО загрузки страницы
                page.on("request", handle_request)
                page.on("response", handle_response)
                logger.info("[Playwright] Обработчики API запросов/ответов установлены")
                
                # Блокируем изображения для ускорения
                page.route("**/*.{png,jpg,jpeg,gif,svg,webp}", lambda route: route.abort())
                
                # Загружаем mobile страницу (desktop показывает ошибку)
                logger.info(f"[Playwright] Загрузка mobile страницы: {mobile_url}")
                try:
                    response = page.goto(mobile_url, wait_until='networkidle', timeout=60000)
                    if response and response.status == 200:
                        # Проверяем, не ошибка ли это
                        page_title = page.title()
                        page_content = page.content()
                        if '访问出错了' in page_title or '出错啦' in page_content or '404' in page_title or 'error' in page_title.lower():
                            logger.warning(f"[Playwright] Mobile страница показывает ошибку: title='{page_title[:50]}'")
                            return None
                        else:
                            logger.info(f"[Playwright] Mobile страница загружена (status: {response.status}, title: '{page_title[:50]}')")
                    else:
                        logger.warning(f"[Playwright] Mobile версия вернула статус: {response.status if response else 'None'}")
                        return None
                except Exception as e:
                    logger.error(f"[Playwright] Mobile версия не загрузилась: {e}")
                    return None
                
                # Ожидание для JavaScript - увеличиваем время
                logger.info("[Playwright] Ждем JavaScript...")
                time.sleep(5)  # Базовая задержка для загрузки скриптов
                
                # Ждем загрузки данных через API - проверяем, что значения не "-"
                logger.info("[Playwright] Ждем загрузки данных через API...")
                try:
                    # Ждем, пока хотя бы одно поле с данными не загрузится (не будет "-")
                    page.wait_for_function("""
                        () => {
                            // Ищем элементы с метками "发动机", "变速箱" и проверяем, что значения не "-"
                            const labels = ['发动机', '变速箱', '表显里程', '排放标准'];
                            for (let label of labels) {
                                // Ищем элемент с текстом метки
                                const elements = Array.from(document.querySelectorAll('*'));
                                for (let el of elements) {
                                    if (el.textContent && el.textContent.includes(label)) {
                                        // Ищем родительский контейнер и проверяем значение
                                        let parent = el.parentElement;
                                        if (parent) {
                                            const text = parent.textContent || '';
                                            // Проверяем, что есть значение (не только метка и "-")
                                            const parts = text.split(label);
                                            if (parts.length > 1) {
                                                const value = parts[1].trim();
                                                if (value && value !== '-' && value.length > 0) {
                                                    return true;
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            return false;
                        }
                    """, timeout=30000)  # Ждем до 30 секунд
                    logger.info("[Playwright] ✓ Данные загружены через API")
                except Exception as e:
                    logger.warning(f"[Playwright] Данные не загрузились за 30 секунд: {e}, продолжаем...")
                
                # ПРОВЕРКА DOM: Проверяем, что действительно находится в DOM после ожидания
                logger.info("[Playwright] === ПРОВЕРКА DOM ПОСЛЕ ОЖИДАНИЯ ===")
                try:
                    dom_check = page.evaluate("""
                        () => {
                            const result = {
                                found_labels: [],
                                found_values: [],
                                page_text_sample: '',
                                elements_with_engine: [],
                                elements_with_power: [],
                                all_text_with_labels: []
                            };
                            
                            // Ищем элементы с метками
                            const labels = ['发动机', '马力', '功率', '排量', '变速箱', '表显里程', '排放标准'];
                            const allElements = Array.from(document.querySelectorAll('*'));
                            
                            for (let label of labels) {
                                for (let el of allElements) {
                                    const text = el.textContent || '';
                                    if (text.includes(label)) {
                                        result.found_labels.push({
                                            label: label,
                                            element: el.tagName,
                                            className: el.className || '',
                                            text: text.substring(0, 200),
                                            parentText: el.parentElement ? (el.parentElement.textContent || '').substring(0, 200) : ''
                                        });
                                        
                                        // Проверяем, есть ли значение рядом
                                        const parent = el.parentElement;
                                        if (parent) {
                                            const parentText = parent.textContent || '';
                                            const parts = parentText.split(label);
                                            if (parts.length > 1) {
                                                const value = parts[1].trim();
                                                if (value && value !== '-' && value.length > 0) {
                                                    result.found_values.push({
                                                        label: label,
                                                        value: value.substring(0, 100)
                                                    });
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // Ищем элементы, содержащие "发动机" или "马力"
                            for (let el of allElements) {
                                const text = el.textContent || '';
                                if (text.includes('发动机') && !result.elements_with_engine.some(e => e.text === text.substring(0, 100))) {
                                    result.elements_with_engine.push({
                                        tag: el.tagName,
                                        className: el.className || '',
                                        text: text.substring(0, 200)
                                    });
                                }
                                if ((text.includes('马力') || text.includes('功率')) && !result.elements_with_power.some(e => e.text === text.substring(0, 100))) {
                                    result.elements_with_power.push({
                                        tag: el.tagName,
                                        className: el.className || '',
                                        text: text.substring(0, 200)
                                    });
                                }
                            }
                            
                            // Берем образец текста страницы
                            result.page_text_sample = document.body ? document.body.textContent.substring(0, 500) : '';
                            
                            return result;
                        }
                    """)
                    
                    logger.info(f"[Playwright] Найдено меток в DOM: {len(dom_check.get('found_labels', []))}")
                    logger.info(f"[Playwright] Найдено значений: {len(dom_check.get('found_values', []))}")
                    logger.info(f"[Playwright] Элементов с '发动机': {len(dom_check.get('elements_with_engine', []))}")
                    logger.info(f"[Playwright] Элементов с '马力'/'功率': {len(dom_check.get('elements_with_power', []))}")
                    
                    # Логируем найденные значения
                    if dom_check.get('found_values'):
                        logger.info(f"[Playwright] Найденные значения в DOM:")
                        for val in dom_check.get('found_values', [])[:10]:  # Первые 10
                            logger.info(f"[Playwright]   - {val.get('label')}: {val.get('value')}")
                    
                    # Логируем элементы с engine
                    if dom_check.get('elements_with_engine'):
                        logger.info(f"[Playwright] Элементы с '发动机' (первые 5):")
                        for el in dom_check.get('elements_with_engine', [])[:5]:
                            logger.info(f"[Playwright]   - {el.get('tag')}.{el.get('className')}: {el.get('text')[:100]}")
                    
                    # Логируем элементы с power
                    if dom_check.get('elements_with_power'):
                        logger.info(f"[Playwright] Элементы с '马力'/'功率' (первые 5):")
                        for el in dom_check.get('elements_with_power', [])[:5]:
                            logger.info(f"[Playwright]   - {el.get('tag')}.{el.get('className')}: {el.get('text')[:100]}")
                    
                    # Логируем образец текста страницы
                    if dom_check.get('page_text_sample'):
                        logger.info(f"[Playwright] Образец текста страницы (первые 200 символов): {dom_check.get('page_text_sample', '')[:200]}")
                    
                except Exception as e:
                    logger.warning(f"[Playwright] Ошибка при проверке DOM: {e}")
                
                # Дополнительное ожидание для полной загрузки всех данных
                logger.info("[Playwright] Дополнительное ожидание для полной загрузки...")
                time.sleep(3)
                
                # Прокрутка для загрузки динамического контента
                logger.info("[Playwright] Прокрутка страницы...")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(1)
                
                # Пробуем кликнуть на элементы, которые могут загрузить данные
                try:
                    # Ищем кнопки или ссылки, которые могут загрузить детали
                    detail_buttons = page.query_selector_all('button, a, [class*="more"], [class*="detail"], [class*="expand"]')
                    for btn in detail_buttons[:3]:  # Пробуем первые 3 кнопки
                        try:
                            text = btn.inner_text() if hasattr(btn, 'inner_text') else ''
                            if any(keyword in text for keyword in ['更多', '详情', '全部', '展开', '查看']):
                                btn.click()
                                time.sleep(2)
                                logger.info(f"[Playwright] Кликнули на кнопку: {text[:20]}")
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"[Playwright] Не удалось кликнуть на кнопки: {e}")
                
                # Пробуем извлечь данные из JSON в window.__INITIAL_STATE__ или window.__NUXT__
                logger.info("[Playwright] Пробуем извлечь данные из JSON...")
                try:
                    json_data = page.evaluate("""
                        () => {
                            if (window.__INITIAL_STATE__) return window.__INITIAL_STATE__;
                            if (window.__NUXT__) return window.__NUXT__;
                            if (window.__NEXT_DATA__) return window.__NEXT_DATA__;
                            // Ищем JSON в script тегах
                            const scripts = document.querySelectorAll('script[type="application/json"]');
                            for (let script of scripts) {
                                try {
                                    return JSON.parse(script.textContent);
                                } catch(e) {}
                            }
                            return null;
                        }
                    """)
                    if json_data:
                        logger.info(f"[Playwright] Найден JSON с данными: {type(json_data)}")
                        # Сохраняем для дальнейшего использования
                        self._last_json_data = json_data
                except Exception as e:
                    logger.debug(f"[Playwright] JSON не найден: {e}")
                
                # Получаем HTML
                html = page.content()
                logger.info(f"[Playwright] Размер HTML: {len(html):,} байт")
                
                # Пробуем кликнуть на "更多" / "全部参数配置" для получения детальных характеристик
                logger.info("[Playwright] Попытка клика на '更多' для деталей...")
                try:
                    # Ищем кнопку или ссылку "全部参数配置"
                    more_selectors = [
                        "text=全部参数配置",
                        "a:has-text('全部参数配置')",
                        "a:has-text('更多')",
                        ".more-params",
                        "[onclick*='showParams']",
                    ]
                    
                    clicked = False
                    for selector in more_selectors:
                        try:
                            button = page.locator(selector).first
                            if button.count() > 0:
                                logger.info(f"[Playwright] Найдена кнопка: {selector}")
                                button.click(timeout=3000)
                                logger.info("[Playwright] ✓ Клик выполнен!")
                                page.wait_for_timeout(2000)  # Ждем загрузки контента
                                clicked = True
                                break
                        except Exception as e:
                            continue
                    
                    if clicked:
                        # Получаем обновленный HTML после клика
                        html_after = page.content()
                        if len(html_after) > len(html):
                            logger.info(f"[Playwright] ✓ HTML расширен: +{len(html_after) - len(html):,} байт")
                            html = html_after
                        else:
                            logger.info("[Playwright] HTML не изменился, возможно детали уже отображены")
                    else:
                        logger.info("[Playwright] Кнопка '更多' не найдена - все данные уже отображены")
                        
                except Exception as e:
                    logger.warning(f"[Playwright] Не удалось кликнуть на '更多': {e}")
                
                # Пробуем извлечь данные из перехваченных API ответов ПЕРЕД закрытием браузера
                logger.info(f"[Playwright] Всего перехвачено запросов: {len(all_requests)}, API ответов: {len(api_responses)}")
                if api_responses:
                    logger.info(f"[Playwright] Найдено {len(api_responses)} API ответов, пробуем извлечь данные...")
                    api_data = {}
                    for response in api_responses:
                        extracted = self._extract_from_api_response(response['data'], car_id)
                        if extracted:
                            api_data.update(extracted)
                            logger.info(f"[Playwright] Извлечено {len(extracted)} полей из API: {response['url'][:80]}")
                    
                    if api_data:
                        logger.info(f"[Playwright] ✓ Всего извлечено {len(api_data)} полей из API ответов: {list(api_data.keys())}")
                        # Сохраняем для использования в _extract_car_data
                        self._api_data = api_data
                    else:
                        logger.warning(f"[Playwright] Не удалось извлечь данные из {len(api_responses)} API ответов")
                        # Логируем первые несколько URL для отладки
                        for i, resp in enumerate(api_responses[:3]):
                            logger.debug(f"[Playwright] API ответ {i+1}: {resp['url'][:100]}")
                else:
                    logger.warning(f"[Playwright] API ответы не перехвачены. Всего запросов: {len(all_requests)}")
                    # Логируем первые несколько URL для отладки
                    interesting_requests = [url for url in all_requests if any(k in url.lower() for k in ['api', 'detail', 'car', 'info', 'data'])]
                    if interesting_requests:
                        logger.debug(f"[Playwright] Интересные запросы (первые 5): {interesting_requests[:5]}")
                
                # Сохраняем для отладки
                debug_dir = os.getenv('CHE168_DEBUG_DIR', '/tmp/che168_debug')
                try:
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_file = os.path.join(debug_dir, f'playwright_{car_id}.html')
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(html)
                    logger.info(f"[Playwright] HTML сохранен: {debug_file}")
                except Exception as e:
                    logger.warning(f"[Playwright] Не удалось сохранить HTML: {e}")
                
            except Exception as e:
                logger.error(f"[Playwright] Ошибка парсинга {car_id}: {e}", exc_info=True)
                return None
            finally:
                # Гарантируем закрытие браузера в любом случае
                if browser:
                    try:
                        browser.close()
                        logger.debug(f"[Playwright] Браузер закрыт для car_id={car_id}")
                    except Exception as close_error:
                        logger.warning(f"[Playwright] Ошибка при закрытии браузера: {close_error}")
            
            # Обработка данных ПОСЛЕ закрытия браузера (html уже сохранён)
            if 'html' not in locals() or not html:
                return None
                
            # Проверяем на "продано"
            if '当前车源已成交' in html or '车源已下架' in html or '车源已删除' in html:
                logger.warning(f"[Playwright] Автомобиль {car_id} УЖЕ ПРОДАН или недоступен")
                return None
            
            # Парсим данные
            soup = BeautifulSoup(html, 'html.parser')
            car_data = self._extract_car_data(soup, car_id, html)
            
            if car_data:
                data_fields = {k: v for k, v in car_data.items() if k != 'car_id' and v is not None}
                logger.info(f"[Playwright] Успешно извлечено {len(data_fields)} полей")
                return Che168DetailedCar(**car_data)
            else:
                logger.warning(f"[Playwright] Не удалось извлечь данные для {car_id}")
                return None
    
    def _extract_from_api_response(self, json_data: Any, car_id: int) -> Dict[str, Any]:
        """Извлекает данные из JSON ответа API"""
        extracted = {}
        try:
            from ..dongchedi.parser import normalize_power_value
            
            all_keys = []  # Для отладки - собираем все ключи
            
            def search_recursive(obj, path=""):
                """Рекурсивный поиск данных в JSON"""
                if isinstance(obj, dict):
                    # Собираем ключи для отладки (только первые 2 уровня)
                    if len(path.split('.')) <= 2:
                        for key in obj.keys():
                            full_key = f"{path}.{key}" if path else key
                            if full_key not in all_keys:
                                all_keys.append(full_key)
                    
                    # Ищем мощность
                    for key, value in obj.items():
                        key_lower = key.lower()
                        if 'power' in key_lower or '马力' in str(key) or '功率' in str(key):
                            if value and str(value) != '-':
                                power_str = str(value)
                                logger.debug(f"[Playwright] Найдено поле power в API: key='{key}', value='{power_str}'")
                                # Пробуем извлечь число
                                power_match = re.search(r'(\d+)', power_str)
                                if power_match:
                                    power_value = power_match.group(1)
                                    # Проверяем, что это не 0
                                    if power_value != '0':
                                        normalized = normalize_power_value(power_value + 'Ps')
                                        if normalized and normalized != '0':
                                            extracted['power'] = normalized
                                            logger.info(f"[Playwright] ✓ Мощность из API: {normalized} (из '{power_str}')")
                                        else:
                                            logger.debug(f"[Playwright] Мощность не нормализована: '{power_value}' -> '{normalized}'")
                                    else:
                                        logger.debug(f"[Playwright] Мощность = 0, пропускаем: '{power_str}'")
                                else:
                                    # Пробуем нормализовать напрямую, если нет числа
                                    normalized = normalize_power_value(power_str)
                                    if normalized and normalized != '0':
                                        extracted['power'] = normalized
                                        logger.info(f"[Playwright] ✓ Мощность из API (прямая нормализация): {normalized} (из '{power_str}')")
                        
                        # Ищем engine_info
                        if 'engine' in key_lower and ('info' in key_lower or 'type' in key_lower):
                            if value and str(value) != '-':
                                engine_value = str(value)
                                extracted['engine_info'] = engine_value
                                logger.info(f"[Playwright] ✓ engine_info из API: {engine_value}")
                                
                                # Пробуем извлечь мощность из engine_info (например, "2.0T 252马力")
                                if 'power' not in extracted:
                                    from ..dongchedi.parser import normalize_power_value
                                    power_patterns = [
                                        r'(\d+)\s*马力',
                                        r'(\d+)\s*Ps',
                                        r'(\d+)\s*kW',
                                        r'(\d+)\s*HP',
                                        r'(\d+)\s*hp',
                                    ]
                                    for pattern in power_patterns:
                                        power_match = re.search(pattern, engine_value, re.IGNORECASE)
                                        if power_match:
                                            power_value = power_match.group(1)
                                            if power_value != '0':
                                                normalized = normalize_power_value(power_value + 'Ps')
                                                if normalized and normalized != '0':
                                                    extracted['power'] = normalized
                                                    logger.info(f"[Playwright] ✓ Мощность из engine_info API: {normalized} (из '{engine_value}')")
                                                    break
                        
                        # Ищем другие поля
                        field_mapping = {
                            'transmission': 'transmission',
                            '变速箱': 'transmission',
                            'enginevolume': 'engine_volume',
                            '排量': 'engine_volume',
                            'fueltype': 'fuel_type',
                            '燃料': 'fuel_type',
                            'drivetype': 'drive_type',
                            '驱动': 'drive_type',
                        }
                        
                        for api_key, field_name in field_mapping.items():
                            if api_key in key_lower and value and str(value) != '-':
                                if field_name not in extracted:
                                    extracted[field_name] = str(value)
                                    logger.info(f"[Playwright] ✓ {field_name} из API: {value}")
                        
                        # Рекурсивно ищем в вложенных объектах
                        if isinstance(value, (dict, list)):
                            search_recursive(value, f"{path}.{key}" if path else key)
                            
                elif isinstance(obj, list):
                    for item in obj:
                        search_recursive(item, path)
            
            search_recursive(json_data)
            
            # Логируем все найденные ключи для отладки (первые 50)
            if all_keys:
                logger.debug(f"[Playwright] Все ключи в API ответе (первые 50): {all_keys[:50]}")
                # Ищем ключи, которые могут содержать мощность
                power_related_keys = [k for k in all_keys if any(term in k.lower() for term in ['power', '马力', '功率', 'horse', 'hp', 'ps', 'kw'])]
                if power_related_keys:
                    logger.info(f"[Playwright] Найдены ключи, связанные с мощностью: {power_related_keys}")
                else:
                    logger.warning(f"[Playwright] Не найдено ключей, связанных с мощностью в API ответе")
            
        except Exception as e:
            logger.debug(f"[Playwright] Ошибка при извлечении данных из API: {e}")
        
        return extracted
    
    def _extract_car_data(self, soup: BeautifulSoup, car_id: int, html: str = "") -> Optional[Dict[str, Any]]:
        """Извлекает данные из desktop HTML"""
        try:
            data = {'car_id': car_id}
            
            # Сначала пробуем использовать данные из API
            if hasattr(self, '_api_data') and self._api_data:
                logger.info(f"[Playwright] Используем данные из API: {list(self._api_data.keys())}")
                data.update(self._api_data)
            
            # Сначала пробуем извлечь из JSON, если он был сохранен
            if hasattr(self, '_last_json_data') and self._last_json_data:
                logger.info("[Playwright] Пробуем извлечь данные из JSON...")
                json_data = self._last_json_data
                # Рекурсивный поиск в JSON
                def find_in_json(obj, keys_to_find):
                    found = {}
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if any(k in key.lower() for k in keys_to_find):
                                found[key] = value
                            if isinstance(value, (dict, list)):
                                nested = find_in_json(value, keys_to_find)
                                found.update(nested)
                    elif isinstance(obj, list):
                        for item in obj:
                            nested = find_in_json(item, keys_to_find)
                            found.update(nested)
                    return found
                
                json_power_data = find_in_json(json_data, ['power', '马力', '功率', 'engine'])
                if json_power_data:
                    logger.info(f"[Playwright] Найдены данные в JSON: {list(json_power_data.keys())}")
                    # Пробуем извлечь мощность
                    for key, value in json_power_data.items():
                        if 'power' in key.lower() or '马力' in str(value) or '功率' in str(value):
                            power_match = re.search(r'(\d+)\s*马力|(\d+)\s*Ps|(\d+)\s*kW', str(value))
                            if power_match:
                                power_value = power_match.group(1) or power_match.group(2) or power_match.group(3)
                                data['power'] = power_value + 'Ps'
                                logger.info(f"[Playwright] ✓ Мощность из JSON: {data['power']}")
                                break
            
            # ПАРСИНГ MOBILE СТРУКТУРЫ (используем mobile URL)
            logger.info("[Playwright] Парсинг mobile структуры...")
            
            # Сначала пробуем найти мощность в HTML по различным паттернам
            if not data.get('power'):
                logger.info("[Playwright] Ищем мощность в HTML мобильной версии...")
                from ..dongchedi.parser import normalize_power_value
                
                # СПОСОБ 1: Ищем в тексте страницы по паттернам мощности
                page_text = soup.get_text()
                logger.debug(f"[Playwright] Размер текста страницы: {len(page_text)} символов")
                logger.debug(f"[Playwright] Образец текста (первые 500 символов): {page_text[:500]}")
                
                # Проверяем, есть ли вообще упоминания мощности в тексте
                if '马力' in page_text or '功率' in page_text or 'Ps' in page_text or 'kW' in page_text:
                    logger.info(f"[Playwright] Найдены упоминания мощности в тексте страницы")
                else:
                    logger.warning(f"[Playwright] Не найдено упоминаний мощности ('马力', '功率', 'Ps', 'kW') в тексте страницы")
                
                power_patterns = [
                    # Приоритет: ищем "最大马力(Ps)" с числом на следующей строке или рядом
                    r'最大马力\s*\(?Ps\)?\s*[:\s\n]+(\d+)',  # "最大马力(Ps)\n258" или "最大马力(Ps): 258"
                    r'最大马力\s*\(?Ps\)?\s*[:\s]*(\d+)',  # "最大马力(Ps) 258" или "最大马力(Ps): 258"
                    # Ищем "最大功率(kW)" с числом на следующей строке или рядом
                    r'最大功率\s*\(?kW\)?\s*[:\s\n]+(\d+)',  # "最大功率(kW)\n190" или "最大功率(kW): 190"
                    r'最大功率\s*\(?kW\)?\s*[:\s]*(\d+)',  # "最大功率(kW) 190" или "最大功率(kW): 190"
                    r'最大功率[^0-9]*(\d+)',    # "最大功率 137"
                    r'最大马力[^0-9]*(\d+)',    # "最大马力 252"
                    r'后电动机最大功率[^0-9]*(\d+)',  # "后电动机最大功率(kW) 240"
                    r'前电动机最大功率[^0-9]*(\d+)',  # "前电动机最大功率(kW) 240"
                    r'电动机最大功率[^0-9]*(\d+)',  # "电动机最大功率(kW) 240"
                    r'(\d+)\s*马力',           # "252马力"
                    r'(\d+)\s*Ps',             # "252Ps"
                    r'(\d+)\s*kW',             # "137kW" или "240" после "最大功率(kW)"
                    r'(\d+)\s*HP',             # "252HP"
                    r'功率[^0-9]*(\d+)\s*(?:kW|马力|Ps)',  # "功率 137kW"
                    r'马力[^0-9]*(\d+)',        # "马力 252"
                ]
                
                for pattern in power_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        # Берем первое найденное значение
                        power_value = matches[0] if isinstance(matches[0], str) else str(matches[0])
                        if power_value != '0':
                            # Если паттерн содержит "最大马力(Ps)", это уже в л.с., используем напрямую
                            if '最大马力' in pattern and 'ps' in pattern.lower():
                                try:
                                    hp_value = int(power_value)
                                    if 50 <= hp_value <= 1000:  # Проверяем разумность значения
                                        data['power'] = str(hp_value)
                                        logger.info(f"[Playwright] ✓ Мощность из HTML (最大马力(Ps), паттерн '{pattern[:40]}'): {hp_value}Ps")
                                        break
                                except (ValueError, TypeError):
                                    pass
                            
                            # Если паттерн содержит "kW" или "最大功率", это может быть в кВт, нужно конвертировать
                            is_kw = 'kw' in pattern.lower() or ('最大功率' in pattern and 'ps' not in pattern.lower()) or '电动机' in pattern
                            if is_kw:
                                # Конвертируем из кВт в л.с.
                                try:
                                    kw_value = float(power_value)
                                    hp_value = int(kw_value * 1.35962)  # 1 кВт = 1.35962 л.с.
                                    if 50 <= hp_value <= 1000:  # Проверяем разумность значения
                                        data['power'] = str(hp_value)
                                        logger.info(f"[Playwright] ✓ Мощность из HTML (кВт->л.с., паттерн '{pattern[:40]}'): {power_value}kW = {hp_value}Ps")
                                        break
                                except (ValueError, TypeError):
                                    pass
                            
                            # Пробуем нормализовать как обычно
                            normalized = normalize_power_value(power_value + 'Ps')
                            if normalized and normalized != '0':
                                data['power'] = normalized
                                logger.info(f"[Playwright] ✓ Мощность из HTML (паттерн '{pattern[:40]}'): {normalized}")
                                break
                
                # СПОСОБ 2: Ищем элементы с текстом "马力" или "功率" и извлекаем число
                if not data.get('power'):
                    power_labels = soup.find_all(string=re.compile(r'马力|功率'))
                    for label in power_labels:
                        parent = label.parent
                        if parent:
                            # Ищем число в родительском элементе или соседних
                            parent_text = parent.get_text()
                            power_match = re.search(r'(\d{2,4})\s*(?:马力|Ps|kW|HP)', parent_text, re.IGNORECASE)
                            if power_match:
                                power_value = power_match.group(1)
                                if power_value != '0':
                                    normalized = normalize_power_value(power_value + 'Ps')
                                    if normalized and normalized != '0':
                                        data['power'] = normalized
                                        logger.info(f"[Playwright] ✓ Мощность из HTML (элемент с меткой): {normalized}")
                                        break
                        if data.get('power'):
                            break
                
                # СПОСОБ 3: Ищем в engine_info, если он есть в HTML
                if not data.get('power') and data.get('engine_info'):
                    engine_text = data['engine_info']
                    power_match = re.search(r'(\d{2,4})\s*(?:马力|Ps|kW|HP)', engine_text, re.IGNORECASE)
                    if power_match:
                        power_value = power_match.group(1)
                        if power_value != '0':
                            normalized = normalize_power_value(power_value + 'Ps')
                            if normalized and normalized != '0':
                                data['power'] = normalized
                                logger.info(f"[Playwright] ✓ Мощность из engine_info HTML: {normalized}")
            
            # Пробуем разные селекторы для поиска элементов с данными (mobile структура)
            # В мобильной версии данные могут быть в разных структурах
            items = []
            
            # СПОСОБ 1: Ищем элементы с текстом меток (приоритет для мобильной версии)
            key_labels = ['首次上牌时间', '上牌时间', '最大马力(Ps)', '最大功率(kW)', '最大马力', '最大功率', 
                         '电动机(Ps)', '后电动机最大功率(kW)', '前电动机最大功率(kW)', '发动机', '变速箱', 
                         '表显里程', '排放标准', '车辆年审时间', '交强险截止日期', 'NEDC纯电续航里程(km)',
                         '电池能量(kW)', '快充时间(小时)', '慢充时间(小时)', '长(mm)', '宽(mm)', '高(mm)',
                         '轴距(mm)', '整备质量(kg)', '最大扭矩(N·m)', '官方百公里加速时间(s)', '最高车速(km/h)']
            
            items_set = set()  # Для избежания дубликатов
            for label in key_labels:
                # Ищем элементы, содержащие текст метки (более гибкий поиск)
                label_elements = soup.find_all(string=re.compile(re.escape(label)))
                for label_elem in label_elements:
                    parent = label_elem.parent
                    if parent and id(parent) not in items_set:
                        items.append(parent)
                        items_set.add(id(parent))
                
                # Также ищем элементы, у которых текст содержит метку
                label_elements_by_text = soup.find_all(string=lambda text: text and label in str(text))
                for label_elem in label_elements_by_text:
                    parent = label_elem.parent
                    if parent and id(parent) not in items_set:
                        items.append(parent)
                        items_set.add(id(parent))
            
            # СПОСОБ 2: Стандартные селекторы
            if not items:
                items = soup.find_all('span', class_='item-name')
            if not items:
                items = soup.find_all('span', class_=lambda x: x and 'item' in x.lower() and 'name' in x.lower())
            if not items:
                # Пробуем искать по тексту меток
                items = soup.find_all(['span', 'div', 'dt'], string=lambda text: text and any(k in str(text) for k in ['发动机', '马力', '功率', '排量', '变速箱', '首次上牌', '上牌时间']))
            if not items:
                # Пробуем найти элементы с данными через структуру списка
                items = soup.find_all(['dt', 'dd', 'li'], string=lambda text: text and any(k in str(text) for k in ['发动机', '马力', '功率', '排量', '变速箱', '上牌', '里程', '排放', '首次上牌']))
            if not items:
                # Пробуем найти через data-атрибуты
                items = soup.find_all(attrs={'data-label': lambda x: x and any(k in str(x) for k in ['发动机', '马力', '功率', '首次上牌', '上牌时间'])})
            if not items:
                # Пробуем найти через любые элементы с текстом меток
                all_elements = soup.find_all(['span', 'div', 'dt', 'dd', 'p', 'td', 'th'])
                items = [elem for elem in all_elements if elem.get_text(strip=True) in ['发动机', '发  动  机', '马力', '功率', '排量', '变速箱']]
            
            logger.info(f"[Playwright] Найдено элементов для парсинга: {len(items)}")
            
            # Логируем первые несколько найденных элементов для отладки
            if items:
                logger.info(f"[Playwright] Первые 5 элементов: {[item.get_text(strip=True)[:30] for item in items[:5]]}")
            
            field_mapping = {
                # Основные данные
                '首次上牌时间': 'first_registration_time',  # Приоритет: "首次上牌时间" более точное
                '上牌时间': 'first_registration_time',
                '表显里程': 'mileage',
                '排放标准': 'emission_standard',
                '所  在  地': 'city',
                '所在地': 'city',
                '车身颜色': 'color',
                '外观颜色': 'exterior_color',
                '内饰颜色': 'interior_color',
                
                # Двигатель и трансмиссия
                '发  动  机': 'engine_info',  # "2.0T 252马力 L4"
                '变  速  箱': 'transmission',
                '排       量': 'engine_volume',
                '驱动方式': 'drive_type',
                '燃油标号': 'fuel_grade',
                '燃料形式': 'fuel_type',
                
                # Мощность и производительность
                '最大马力(Ps)': 'power',  # Приоритет: более точное
                '最大马力': 'power',
                '最大功率(kW)': 'power',  # Приоритет: более точное
                '最大功率': 'power',
                '电动机(Ps)': 'power',  # Для электромобилей
                '后电动机最大功率(kW)': 'power',  # Для электромобилей
                '前电动机最大功率(kW)': 'power',  # Для электромобилей
                '功率': 'power',
                '马力': 'power',
                '最大扭矩(N·m)': 'torque',  # Приоритет: более точное
                '最大扭矩': 'torque',
                '前电动机最大扭矩(N·m)': 'torque',
                '后电动机最大扭矩(N·m)': 'torque',
                '扭矩': 'torque',
                '加速时间': 'acceleration',
                '百公里加速': 'acceleration',
                '百公里加速时间': 'acceleration',
                '官方百公里加速时间(s)': 'acceleration',
                '最高车速': 'max_speed',
                '最高车速(km/h)': 'max_speed',
                
                # Расход и экология
                '百公里耗电量(kWh/100km)': 'fuel_consumption',  # Приоритет: более точное
                '百公里耗电量': 'fuel_consumption',
                'NEDC综合油耗(L/100km)': 'fuel_consumption',
                '油耗': 'fuel_consumption',
                '百公里油耗': 'fuel_consumption',
                
                # Размеры
                '长': 'length',
                '长(mm)': 'length',
                '宽': 'width',
                '宽(mm)': 'width',
                '高': 'height',
                '高(mm)': 'height',
                '长x宽x高': 'dimensions',
                '长x宽x高(mm)': 'dimensions',
                '轴距': 'wheelbase',
                '轴距(mm)': 'wheelbase',
                
                # Масса
                '整备质量': 'curb_weight',
                '整备质量(kg)': 'curb_weight',
                '总质量': 'gross_weight',
                '总质量(kg)': 'gross_weight',
                
                # История и статус
                '过户次数': 'owner_count',
                '车辆年审时间': 'inspection_date',  # Более точное название
                '年检到期': 'inspection_date',
                '交强险截止日期': 'insurance_info',
                '保险到期': 'insurance_info',
                '车船使用税有效日期': 'tax_info',
                '整车质保': 'warranty_info',
                '质保到期': 'warranty_info',
                '首任车主质保政策': 'warranty_info',
                '电池组质保': 'battery_warranty',
                
                # Классификация
                '车辆级别': 'vehicle_class',
                '级别': 'vehicle_class',
                '能源类型': 'energy_type',  # Для электромобилей
                '上市时间': 'launch_date',
                '厂商': 'manufacturer',
                '厂商指导价(元)': 'msrp',
                
                # Электрические характеристики
                'NEDC纯电续航里程(km)': 'electric_range',
                '纯电续航里程(km)工信部': 'electric_range',
                '纯电续航里程(km)WLTC': 'electric_range',
                '电池能量(kWh)': 'battery_capacity',
                '电池能量密度(Wh/kg)': 'battery_density',
                '快充时间(小时)': 'fast_charge_time',
                '慢充时间(小时)': 'slow_charge_time',
                '快充电量百分比': 'fast_charge_percent',
                '快充电量(%)': 'fast_charge_percent',
                '快充功能': 'fast_charge_support',
                '换电': 'battery_swap',
                '电池类型': 'battery_type',
                '电芯品牌': 'battery_brand',
                '电池冷却方式': 'battery_cooling',
                '驱动电机数': 'motor_count',
                '电机布局': 'motor_layout',
                
                # Дополнительные характеристики
                '挡位个数': 'gear_count',
                '变速箱类型': 'transmission_type',
                '简称': 'transmission_short',
                '四驱形式': 'awd_type',
                '中央差速器结构': 'differential_type',
                '前悬架类型': 'front_suspension',
                '后悬架类型': 'rear_suspension',
                '助力类型': 'steering_type',
                '车体结构': 'body_structure',
                '前制动器类型': 'front_brakes',
                '后制动器类型': 'rear_brakes',
                '驻车制动类型': 'parking_brake',
                '前轮胎规格': 'front_tires',
                '后轮胎规格': 'rear_tires',
                '备胎规格': 'spare_tire',
                
                # Дополнительные данные
                '配置亮点': 'features',  # Список функций безопасности и комфорта
                '出险查询': 'accident_query_info',
                '维修保养': 'service_query_info',
            }
            
            found_keys = []
            for item in items:
                key_raw = item.get_text(strip=True)
                # Нормализуем неразрывные пробелы (\xa0) в обычные
                key = key_raw.replace('\xa0', ' ')
                found_keys.append(key)
                
                if key in field_mapping:
                    field_name = field_mapping[key]
                    
                    # Получаем родительский элемент
                    parent = item.parent
                    if parent:
                        # Извлекаем весь текст и нормализуем пробелы
                        full_text_raw = parent.get_text(strip=True)
                        full_text = full_text_raw.replace('\xa0', ' ')
                        value = full_text.replace(key, '').strip()
                        
                        # Если значение пустое, пробуем найти в следующем элементе
                        if not value or value == '-':
                            # Ищем следующий элемент (братский или дочерний)
                            next_sibling = parent.find_next_sibling()
                            if next_sibling:
                                value = next_sibling.get_text(strip=True)
                            else:
                                # Ищем в дочерних элементах
                                children = parent.find_all(['span', 'div', 'p'], recursive=False)
                                for child in children:
                                    child_text = child.get_text(strip=True)
                                    if child_text and child_text != key and child_text != '-':
                                        value = child_text
                                        break
                        
                        # Логируем для отладки мощности
                        if field_name == 'power' or field_name == 'engine_info':
                            logger.info(f"[Playwright] DEBUG: key='{key}', field='{field_name}', value='{value}', full_text='{full_text[:100]}'")
                        
                        if value and value != '-':
                            if field_name == 'first_registration_time':
                                normalized = normalize_first_registration_date(value)
                                if normalized:
                                    data[field_name] = normalized
                                    logger.info(f"[Playwright] ✓ {key}: {normalized}")
                            else:
                                data[field_name] = value
                                logger.info(f"[Playwright] ✓ {key}: {value[:50]}")
                        elif value == '-':
                            logger.debug(f"[Playwright] Пропущено значение '-' для {key}")
            
            # Логируем какие ключи не нашли в mapping
            logger.info(f"[Playwright] Все найденные ключи ({len(found_keys)}): {found_keys[:20]}")  # Показываем первые 20
            missing_keys = [k for k in found_keys if k not in field_mapping]
            if missing_keys:
                logger.warning(f"[Playwright] Ключи без mapping ({len(missing_keys)}): {missing_keys[:10]}")  # Показываем первые 10
            
            # Проверяем, нашли ли мы engine_info
            if 'engine_info' in data:
                logger.info(f"[Playwright] ✓ engine_info найден: '{data['engine_info']}'")
            else:
                logger.warning(f"[Playwright] ✗ engine_info НЕ найден. Проверяем альтернативные способы...")
                
                # СПОСОБ 1: Ищем в тексте страницы по паттернам
                page_text = soup.get_text()
                engine_patterns = [
                    r'(\d+\.\d+T?\s+\d+马力)',  # "2.0T 252马力"
                    r'(\d+\.\d+T?\s+\d+Ps)',    # "2.0T 252Ps"
                    r'发动机[^0-9]*(\d+\.\d+T?[^0-9]*\d+马力)',  # "发动机 2.0T 252马力"
                    r'(\d+\.\d+[TL]\s+\d+马力)',  # "2.0T 252马力" (без пробела после T)
                ]
                for pattern in engine_patterns:
                    match = re.search(pattern, page_text)
                    if match:
                        engine_text = match.group(1)
                        logger.info(f"[Playwright] Найден engine_info в тексте (паттерн): '{engine_text}'")
                        data['engine_info'] = engine_text
                        break
                
                # СПОСОБ 2: Ищем элементы с текстом "发动机" и берем соседний текст
                if 'engine_info' not in data:
                    engine_labels = soup.find_all(string=re.compile(r'发动机|发\s*动\s*机'))
                    for label in engine_labels:
                        parent = label.parent
                        if parent:
                            # Ищем значение в соседних элементах
                            siblings = parent.find_next_siblings()
                            for sibling in siblings[:3]:  # Проверяем первые 3 соседних элемента
                                text = sibling.get_text(strip=True)
                                if text and re.search(r'\d+\.\d+[TL]', text):
                                    logger.info(f"[Playwright] Найден engine_info в соседнем элементе: '{text}'")
                                    data['engine_info'] = text
                                    break
                            if 'engine_info' in data:
                                break
                
                # СПОСОБ 3: Ищем в HTML напрямую по структуре
                if 'engine_info' not in data:
                    # Ищем div/span с классом, содержащим "engine" или "motor"
                    engine_elements = soup.find_all(['div', 'span'], class_=lambda x: x and ('engine' in str(x).lower() or 'motor' in str(x).lower() or '动力' in str(x)))
                    for elem in engine_elements:
                        text = elem.get_text(strip=True)
                        if text and re.search(r'\d+\.\d+[TL]', text):
                            logger.info(f"[Playwright] Найден engine_info в элементе с классом: '{text}'")
                            data['engine_info'] = text
                            break
                
                if 'engine_info' not in data:
                    logger.warning(f"[Playwright] ✗ engine_info НЕ найден ни одним способом")
            
            # СПЕЦИАЛЬНАЯ ОБРАБОТКА ПОЛЕЙ
            
            # 1. Мощность из engine_info
            if 'engine_info' in data:
                engine_text = data['engine_info']  # "2.0T 252马力 L4"
                logger.info(f"[Playwright] DEBUG engine_info: '{engine_text}'")
                
                # Мощность (число перед "马力")
                if not data.get('power'):
                    from ..dongchedi.parser import normalize_power_value
                    
                    # Пробуем разные паттерны для извлечения мощности
                    power_patterns = [
                        r'(\d+)\s*马力',  # "252马力"
                        r'(\d+)\s*Ps',   # "252Ps"
                        r'(\d+)\s*kW',   # "137kW"
                        r'(\d+)\s*HP',   # "252HP"
                        r'(\d+)\s*л\.с\.',  # "252л.с."
                    ]
                    
                    power_value = None
                    for pattern in power_patterns:
                        power_match = re.search(pattern, engine_text, re.IGNORECASE)
                        if power_match:
                            power_value = power_match.group(1)
                            # Нормализуем значение
                            normalized = normalize_power_value(power_value + 'Ps')
                            if normalized:
                                data['power'] = normalized + 'Ps'
                                logger.info(f"[Playwright] ✓ Мощность из engine_info: {data['power']} (из '{engine_text}')")
                                break
                    
                    # Если не нашли через паттерны, пробуем найти любое число (3-4 цифры)
                    if not data.get('power'):
                        power_match = re.search(r'(\d{3,4})', engine_text)
                        if power_match:
                            power_value = power_match.group(1)
                            # Проверяем, что это разумное значение мощности (50-1000)
                            power_int = int(power_value)
                            if 50 <= power_int <= 1000:
                                normalized = normalize_power_value(power_value + 'Ps')
                                if normalized:
                                    data['power'] = normalized + 'Ps'
                                    logger.info(f"[Playwright] ✓ Мощность из engine_info (по числу): {data['power']} (из '{engine_text}')")
                    
                    if not data.get('power'):
                        logger.warning(f"[Playwright] Не удалось извлечь мощность из engine_info: '{engine_text}'")
                
                # Объем двигателя
                if not data.get('engine_volume'):
                    volume_match = re.search(r'([\d.]+)[TL]', engine_text)
                    if volume_match:
                        data['engine_volume'] = volume_match.group(1) + 'L'
                        logger.debug(f"[Playwright] ✓ Объем: {data['engine_volume']}")
                
                # Тип двигателя (турбо)
                if 'T' in engine_text and not data.get('engine_type'):
                    data['engine_type'] = engine_text.split()[0] if ' ' in engine_text else engine_text
                    logger.debug(f"[Playwright] ✓ Тип двигателя: {data['engine_type']}")
                
                # Количество цилиндров
                if not data.get('cylinder_count'):
                    cyl_match = re.search(r'L(\d+)', engine_text)
                    if cyl_match:
                        data['cylinder_count'] = cyl_match.group(1)
                        logger.debug(f"[Playwright] ✓ Цилиндров: {data['cylinder_count']}")
            
            # 1.5. Обработка размеров из dimensions (если есть)
            if 'dimensions' in data and not (data.get('length') and data.get('width') and data.get('height')):
                dims_text = data['dimensions']
                # Формат: "5200x2062x1618" или "5200×2062×1618"
                dims_match = re.search(r'(\d+)[x×](\d+)[x×](\d+)', dims_text)
                if dims_match:
                    if not data.get('length'):
                        data['length'] = dims_match.group(1) + 'mm'
                    if not data.get('width'):
                        data['width'] = dims_match.group(2) + 'mm'
                    if not data.get('height'):
                        data['height'] = dims_match.group(3) + 'mm'
                    logger.debug(f"[Playwright] ✓ Размеры: {data.get('length')} x {data.get('width')} x {data.get('height')}")
            
            # 2. Пробег - преобразуем "0.4万公里" в км
            if 'mileage' in data:
                mileage_text = data['mileage']
                match = re.search(r'(\d+\.?\d*)万公里', mileage_text)
                if match:
                    mileage_wan = float(match.group(1))
                    mileage_km = int(mileage_wan * 10000)
                    data['mileage'] = str(mileage_km)
                    logger.debug(f"[Playwright] ✓ Пробег: {mileage_km} км")
            
            # 3. Год из даты первой регистрации
            if 'first_registration_time' in data:
                reg_date = data['first_registration_time']
                try:
                    data['year'] = int(str(reg_date)[:4])
                    logger.debug(f"[Playwright] ✓ Год (из первой регистрации): {data['year']}")
                except (ValueError, TypeError):
                    pass
            
            # 4. Количество владельцев из "0次"
            if 'owner_count' in data:
                owner_text = data['owner_count']
                owner_match = re.search(r'(\d+)次', owner_text)
                if owner_match:
                    data['owner_count'] = int(owner_match.group(1))
                    logger.debug(f"[Playwright] ✓ Владельцев: {data['owner_count']}")
            
            # 5. Парсинг "配置亮点" (features) - извлекаем конкретные функции
            if 'features' in data:
                features_text = data['features']
                logger.debug(f"[Playwright] Парсинг features: {features_text[:100]}")
                
                # Маппинг китайских названий функций на поля domain.Car
                feature_mapping = {
                    # Безопасность
                    '并线辅助': 'blind_spot_monitor',
                    '车道保持': 'lane_departure',
                    '车道偏离': 'lane_departure',
                    '主动刹车': 'abs',
                    '主动安全': 'esp',
                    'ABS': 'abs',
                    'ESP': 'esp',
                    'TCS': 'tcs',
                    '上坡辅助': 'hill_assist',
                    '气囊': 'airbag_count',
                    
                    # Комфорт и удобство
                    'ISOFIX': 'isofix',
                    '自动驻车': 'auto_parking',
                    '自动泊车': 'auto_parking',
                    '电动后备厢': 'power_trunk',
                    '感应后备厢': 'sensor_trunk',
                    '无钥匙启动': 'keyless_start',
                    '无钥匙进入': 'keyless_entry',
                    '座椅加热': 'seat_heating',
                    '座椅通风': 'seat_ventilation',
                    '座椅按摩': 'seat_massage',
                    '方向盘加热': 'steering_wheel_heating',
                    '自动空调': 'air_conditioning',
                    '分区空调': 'climate_control',
                    
                    # Освещение
                    'LED': 'led_lights',
                    '日间行车灯': 'daytime_running',
                    '大灯': 'headlight_type',
                    '雾灯': 'fog_lights',
                    
                    # Мультимедиа
                    '蓝牙': 'bluetooth',
                    '导航': 'navigation',
                    'USB': 'usb',
                    '音响': 'audio_system',
                    
                    # Другое
                    '天窗': 'sunroof',
                    '全景天窗': 'panoramic_roof',
                    '电动座椅': 'power_seats',
                }
                
                for keyword, field_name in feature_mapping.items():
                    if keyword in features_text:
                        # Пробуем извлечь конкретное значение, иначе просто "有" (есть)
                        if field_name == 'airbag_count' and '气囊' in keyword:
                            # Пробуем найти число перед "气囊"
                            match = re.search(r'(\d+).*?气囊', features_text)
                            if match:
                                data[field_name] = match.group(1)
                            else:
                                data[field_name] = '有'
                        else:
                            data[field_name] = '有'
                        
                        logger.debug(f"[Playwright] ✓ Feature: {keyword} → {field_name}")
            
            # 6. Body type из vehicle_class
            if 'vehicle_class' in data and not data.get('body_type'):
                vehicle_class = data['vehicle_class']
                # Маппинг китайских типов кузова
                body_mapping = {
                    '轿车': 'Sedan',
                    '中大型车': 'Full-size Sedan',
                    '中型车': 'Mid-size Sedan',
                    '紧凑型车': 'Compact',
                    '微型车': 'Mini',
                    'SUV': 'SUV',
                    '中型SUV': 'Mid-size SUV',
                    '中大型SUV': 'Full-size SUV',
                    '紧凑型SUV': 'Compact SUV',
                    'MPV': 'MPV',
                    '跑车': 'Sports Car',
                    '皮卡': 'Pickup',
                    '客车': 'Van',
                    '卡车': 'Truck',
                }
                for cn_type, en_type in body_mapping.items():
                    if cn_type in vehicle_class:
                        data['body_type'] = en_type
                        logger.debug(f"[Playwright] ✓ Body type: {en_type}")
                        break
            
            # 7. Fuel type из fuel_grade
            if 'fuel_grade' in data and not data.get('fuel_type'):
                fuel_grade = data['fuel_grade']
                if '号' in fuel_grade:  # 95号, 92号 и т.д. = бензин
                    data['fuel_type'] = '汽油'
                    logger.debug(f"[Playwright] ✓ Fuel type: 汽油 (из {fuel_grade})")
                elif '柴油' in fuel_grade:
                    data['fuel_type'] = '柴油'
                elif '电' in fuel_grade or '充电' in fuel_grade:
                    data['fuel_type'] = '纯电动'
                elif '混动' in fuel_grade or '油电' in fuel_grade:
                    data['fuel_type'] = '油电混合'
            
            # 8. Извлекаем price, brand, series из title и HTML
            self._extract_metadata(soup, html, data)
            
            # 9. Дополнительно парсим технические характеристики из HTML (если не нашли в field_mapping)
            # Используем методы из detailed_parser для извлечения дополнительных полей
            try:
                from .detailed_parser import Che168DetailedParser
                parser = Che168DetailedParser()
                # Извлекаем технические характеристики (torque, acceleration, max_speed, fuel_consumption, dimensions)
                parser._extract_technical_specs(soup, data)
                parser._extract_images(soup, data)
                parser._extract_description(soup, data)
            except Exception as e:
                logger.warning(f"[Playwright] Не удалось использовать доп. методы парсинга: {e}")
            
            logger.info(f"[Playwright] Извлечено {len([v for v in data.values() if v is not None])} полей")
            
            # ОТЛАДКА: показываем что извлекли
            logger.info(f"[Playwright] Ключевые поля:")
            for key in ['power', 'engine_type', 'engine_volume', 'transmission', 'mileage', 'year', 'first_registration_time']:
                value = data.get(key)
                if value:
                    logger.info(f"[Playwright]   {key}: {value}")
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: Если НЕТ значимых полей - возвращаем None
            # Это предотвращает ситуацию когда has_details=true но данных нет
            significant_fields = ['power', 'engine_type', 'engine_volume', 'transmission', 
                                'drive_type', 'fuel_type', 'emission_standard', 'brand_name', 'series_name']
            has_significant = any(data.get(f) and str(data.get(f)).strip() != '' for f in significant_fields)
            
            if not has_significant:
                logger.warning(f"[Playwright] Нет значимых полей для car_id {car_id} - возвращаем None")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"[Playwright] Ошибка извлечения данных: {e}", exc_info=True)
            return None
    
    def _extract_metadata(self, soup: BeautifulSoup, html: str, data: Dict[str, Any]):
        """Извлекает метаданные: price, brand, series из title и HTML"""
        try:
            # 1. Price (цена)
            price_elem = soup.find(string=re.compile(r'¥\d+'))
            if price_elem:
                # Ищем формат "¥12.87万"
                price_match = re.search(r'¥([\d.]+)万', price_elem)
                if price_match:
                    price_wan = float(price_match.group(1))
                    data['price'] = f"{price_wan}万"
                    logger.debug(f"[Playwright] ✓ Price: {data['price']}")
            
            # 2. Brand & Series из title
            title_elem = soup.find('title')
            if title_elem:
                title_text = title_elem.get_text()
                data['title'] = title_text
                
                # Парсим формат "【城市】品牌型号 年款 配置_价格_二手车之家"
                # Например: "【大连】红旗HS5 2023款 2.0T 旗领Pro版_12.8700_二手车之家"
                title_match = re.search(r'】(.+?)\s*(\d{4})款', title_text)
                if title_match:
                    full_name = title_match.group(1).strip()
                    
                    # Разделяем на бренд и серию
                    # Китайские бренды обычно 2-4 иероглифа, затем английские буквы/цифры
                    brand_series_match = re.match(r'([^\x00-\x7F]{2,4})([\x00-\x7F\d\s\-]+)', full_name)
                    if brand_series_match:
                        data['brand_name'] = brand_series_match.group(1).strip()
                        data['series_name'] = brand_series_match.group(2).strip()
                        logger.debug(f"[Playwright] ✓ Brand: {data['brand_name']}, Series: {data['series_name']}")
                    else:
                        # Альтернатива - весь full_name как car_name
                        data['car_name'] = full_name
                        logger.debug(f"[Playwright] ✓ Car name: {data['car_name']}")
            
            # 3. Fuel consumption из текста
            fuel_elem = soup.find(string=re.compile(r'油耗'))
            if fuel_elem:
                parent = fuel_elem.parent
                if parent:
                    text = parent.get_text(strip=True).replace('\xa0', ' ')
                    # Ищем формат "X.XL" или "XL/100km"
                    fuel_match = re.search(r'([\d.]+)\s*L', text)
                    if fuel_match:
                        data['fuel_consumption'] = fuel_match.group(1) + 'L/100km'
                        logger.debug(f"[Playwright] ✓ Fuel consumption: {data['fuel_consumption']}")
        
        except Exception as e:
            logger.warning(f"[Playwright] Ошибка извлечения метаданных: {e}")

