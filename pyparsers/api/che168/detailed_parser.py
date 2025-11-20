import os
import time
import random
import logging
import json
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from .models.detailed_car import Che168DetailedCar

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Che168DetailedParser:
    """Парсер детальной информации о машине с che168.com используя Playwright"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def parse_car_details(self, car_id: int) -> Optional[Che168DetailedCar]:
        """
        Парсит детальную информацию о машине по car_id
        
        Args:
            car_id: ID машины из URL (infoid=56481576)
            
        Returns:
            Che168DetailedCar или None при ошибке
        """
        # Упрощенный URL - используем только необходимые параметры
        url = f"https://m.che168.com/cardetail/index?infoid={car_id}"
        
        if not self._setup_driver():
            return None
        
        try:
            logger.info(f"Парсинг детальной информации для car_id: {car_id}, URL: {url}")
            self.driver.get(url)
            
            # Ждем загрузки страницы
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                logger.debug(f"Body загружен для car_id: {car_id}")
            except TimeoutException:
                logger.warning(f"Таймаут загрузки body для car_id: {car_id}")
            
            # Дополнительное ожидание для загрузки JavaScript
            time.sleep(random.uniform(3, 5))
            
            # Проверяем, что страница не ошибка 404 или другая ошибка
            page_title = self.driver.title.lower()
            if any(error_word in page_title for error_word in ['404', 'error', 'not found', '错误', '未找到', '页面不存在']):
                logger.warning(f"Страница не найдена для car_id: {car_id}, title: {self.driver.title}")
                return None
            
            # Прокручиваем страницу для загрузки динамического контента
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 2))
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(1, 2))
            
            # Еще раз прокручиваем вниз для полной загрузки
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # НОВЫЙ ПОДХОД: Просто ждем загрузки JS, без кликов
            # Selenium нужен только чтобы получить финальный HTML после React render
            # Ищем элементы с текстом "参数" (Параметры) или "发动机" (Двигатель), которые могут быть кликабельными
            try:
                logger.info("Начинаем поиск элементов для раскрытия деталей")
                
                # Сначала ждем, пока страница полностью загрузится
                time.sleep(2)
                
                # Проверяем, что страница загрузилась
                page_text = self.driver.page_source
                logger.debug(f"Размер HTML до кликов: {len(page_text)} символов")
                
                # СПОСОБ 1: Ищем элементы с текстом "参数", "档案", "发动机" и кликаем на них
                expandable_texts = ['参数', '档案', '发动机', '亮点', '配置讲解', '查看更多', '查看全部']
                clicked_count = 0
                
                for text in expandable_texts:
                    try:
                        # Ищем элементы с этим текстом (разные способы)
                        # Способ 1: XPath по тексту
                        xpath_query = f"//*[contains(text(), '{text}')]"
                        elements = self.driver.find_elements(By.XPATH, xpath_query)
                        logger.info(f"Найдено {len(elements)} элементов с текстом '{text}' (XPath)")
                        
                        # Если не нашли, пробуем другой способ
                        if len(elements) == 0:
                            # Ищем по частичному совпадению
                            elements = self.driver.find_elements(By.XPATH, f"//*[contains(., '{text}')]")
                            logger.info(f"Найдено {len(elements)} элементов с текстом '{text}' (частичное совпадение)")
                        
                        for idx, elem in enumerate(elements[:5]):  # Пробуем первые 5 элементов каждого типа
                            try:
                                # Проверяем, видим ли элемент
                                try:
                                    if not elem.is_displayed():
                                        logger.debug(f"Элемент {idx} с текстом '{text}' не виден")
                                        continue
                                except Exception:
                                    logger.debug(f"Не удалось проверить видимость элемента {idx} с текстом '{text}'")
                                    # Пробуем кликнуть все равно
                                
                                # Получаем текст элемента для логирования
                                try:
                                    elem_text = elem.text[:50] if elem.text else "нет текста"
                                except:
                                    elem_text = "не удалось получить текст"
                                
                                logger.debug(f"Обрабатываем элемент {idx} с текстом '{text}': {elem_text}")
                                
                                # Прокручиваем к элементу
                                try:
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", elem)
                                    time.sleep(0.5)
                                except Exception as scroll_e:
                                    logger.debug(f"Ошибка прокрутки к элементу: {scroll_e}")
                                
                                # Пытаемся кликнуть через JavaScript (более надежно)
                                try:
                                    self.driver.execute_script("arguments[0].click();", elem)
                                    clicked_count += 1
                                    logger.info(f"✓ Кликнули на элемент {idx} с текстом '{text}' через JavaScript: {elem_text}")
                                    time.sleep(1.5)  # Даем время на загрузку контента
                                except Exception as js_e:
                                    # Пробуем обычный клик
                                    try:
                                        elem.click()
                                        clicked_count += 1
                                        logger.info(f"✓ Кликнули на элемент {idx} с текстом '{text}' обычным кликом: {elem_text}")
                                        time.sleep(1.5)
                                    except Exception as click_e:
                                        logger.debug(f"Не удалось кликнуть на элемент '{text}' {idx}: {click_e}")
                                        # Пробуем через ActionChains
                                        try:
                                            ActionChains(self.driver).move_to_element(elem).click().perform()
                                            clicked_count += 1
                                            logger.info(f"✓ Кликнули на элемент {idx} с текстом '{text}' через ActionChains: {elem_text}")
                                            time.sleep(1.5)
                                        except Exception as ac_e:
                                            logger.debug(f"Не удалось кликнуть через ActionChains: {ac_e}")
                                            continue
                            except Exception as e:
                                logger.debug(f"Ошибка при обработке элемента '{text}' {idx}: {e}")
                                continue
                    except Exception as e:
                        logger.warning(f"Ошибка при поиске элементов '{text}': {e}")
                        continue
                
                # СПОСОБ 2: Ищем элементы с данными (2.0T/发动机, 自动/变速箱 и т.д.) и кликаем на них
                # Эти элементы находятся в div'ах с классом css-175oi2r и содержат структуру с данными
                # Структура: <div class="css-175oi2r"><div>2.0T</div><div>发动机</div></div>
                try:
                    # Ищем div'ы, которые содержат и значение, и метку (например, "2.0T" и "发动机")
                    data_keywords = ['发动机', '变速箱', '百公里油耗', '燃料形式', '排量', '最大马力', '最大功率']
                    
                    for keyword in data_keywords:
                        try:
                            # Ищем div'ы, содержащие этот ключевое слово
                            # Ищем родительский div, который содержит несколько дочерних div'ов с данными
                            elements_with_data = self.driver.find_elements(By.XPATH, 
                                f"//div[contains(@class, 'css-175oi2r') and contains(., '{keyword}')]")
                            logger.info(f"Найдено {len(elements_with_data)} элементов с данными '{keyword}'")
                            
                            for idx, elem in enumerate(elements_with_data[:10]):  # Пробуем первые 10
                                try:
                                    # Проверяем, что элемент содержит структуру с данными
                                    elem_text = elem.text if elem.text else ""
                                    
                                    # Проверяем, что это элемент с данными (содержит и значение, и метку)
                                    # Например: "2.0T" и "发动机" в одном элементе
                                    has_value = any(char.isdigit() or char in ['T', 'L', '自动', '手动', '汽油', '柴油'] for char in elem_text)
                                    has_label = keyword in elem_text
                                    
                                    if has_value and has_label:
                                        try:
                                            # Ищем родительский элемент, который может быть кликабельным
                                            # Пробуем найти родителя с несколькими дочерними элементами
                                            parent = elem
                                            for level in range(3):  # Поднимаемся на 3 уровня вверх
                                                try:
                                                    parent = parent.find_element(By.XPATH, "./..")
                                                    parent_text = parent.text if parent.text else ""
                                                    # Проверяем, содержит ли родитель несколько элементов с данными
                                                    if any(kw in parent_text for kw in ['发动机', '变速箱', '百公里油耗', '燃料形式']):
                                                        # Это может быть контейнер с несколькими элементами данных
                                                        break
                                                except:
                                                    break
                                            
                                            # Прокручиваем к элементу
                                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", parent)
                                            time.sleep(0.5)
                                            
                                            # Кликаем через JavaScript на родительский элемент
                                            self.driver.execute_script("arguments[0].click();", parent)
                                            clicked_count += 1
                                            logger.info(f"✓ Кликнули на элемент с данными '{keyword}': {elem_text[:50]}")
                                            time.sleep(1.5)
                                            
                                            # Также пробуем кликнуть на сам элемент, если родитель не сработал
                                            try:
                                                self.driver.execute_script("arguments[0].click();", elem)
                                                clicked_count += 1
                                                logger.info(f"✓ Кликнули на дочерний элемент с данными '{keyword}'")
                                                time.sleep(1.5)
                                            except:
                                                pass
                                        except Exception as click_err:
                                            logger.debug(f"Не удалось кликнуть на элемент с данными '{keyword}': {click_err}")
                                            continue
                                except Exception as e:
                                    logger.debug(f"Ошибка при обработке элемента с данными '{keyword}': {e}")
                                    continue
                        except Exception as e:
                            logger.debug(f"Ошибка при поиске элементов с данными '{keyword}': {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Ошибка при поиске элементов с данными: {e}")
                
                # СПОСОБ 3: Ищем кликабельные элементы по классам (css-175oi2r с tabindex или role)
                try:
                    # Ищем div'ы с классом css-175oi2r и tabindex
                    clickable_selectors = [
                        "//div[contains(@class, 'css-175oi2r') and @tabindex='0']",
                        "//div[contains(@class, 'css-175oi2r') and contains(@class, 'r-1i6wzkk')]",
                        "//div[@role='button']",
                        "//button",
                        "//a[contains(@class, 'css-175oi2r')]"
                    ]
                    
                    for selector in clickable_selectors:
                        try:
                            clickable_elements = self.driver.find_elements(By.XPATH, selector)
                            logger.info(f"Найдено {len(clickable_elements)} кликабельных элементов по селектору: {selector[:50]}")
                            
                            for elem in clickable_elements[:15]:  # Пробуем первые 15
                                try:
                                    if not elem.is_displayed():
                                        continue
                                    
                                    # Проверяем, содержит ли элемент нужный текст
                                    try:
                                        elem_text = elem.text[:100] if elem.text else ""
                                    except:
                                        elem_text = ""
                                    
                                    if any(text in elem_text for text in ['参数', '档案', '发动机', '亮点', '配置', '查看', '变速箱', '百公里油耗', '燃料形式']):
                                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                                        time.sleep(0.5)
                                        self.driver.execute_script("arguments[0].click();", elem)
                                        clicked_count += 1
                                        logger.info(f"✓ Кликнули на кликабельный элемент: {elem_text[:50]}")
                                        time.sleep(1.5)
                                except Exception as e:
                                    logger.debug(f"Ошибка при клике на кликабельный элемент: {e}")
                                    continue
                        except Exception as e:
                            logger.debug(f"Ошибка при поиске по селектору {selector}: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Ошибка при поиске кликабельных элементов: {e}")
                
                logger.info(f"Всего кликнуто на {clicked_count} элементов для раскрытия деталей")
                
                # Дополнительная прокрутка и ожидание после всех кликов
                if clicked_count > 0:
                    logger.info("Ждем загрузки контента после кликов...")
                    time.sleep(3)  # Даем больше времени на загрузку
                
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"Ошибка при попытке раскрыть детальную информацию: {e}", exc_info=True)
            
            # Получаем HTML
            html = self.driver.page_source
            
            # Логируем размер HTML для отладки
            logger.debug(f"Размер HTML для car_id {car_id}: {len(html)} символов")
            
            # ОТЛАДКА: Сохраняем HTML для анализа
            debug_dir = os.getenv('CHE168_DEBUG_DIR', '/tmp/che168_debug')
            try:
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f'car_{car_id}_real.html')
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info(f"HTML сохранен для отладки: {debug_file}")
            except Exception as e:
                logger.warning(f"Не удалось сохранить HTML для отладки: {e}")
            
            # Проверяем, не продан ли автомобиль
            if '当前车源已成交' in html or '车源已下架' in html or '车源已删除' in html:
                logger.warning(f"Автомобиль car_id {car_id} УЖЕ ПРОДАН или недоступен")
                return None  # Возвращаем None для проданных машин
            
            # Проверяем, есть ли в HTML нужные данные после кликов
            if '最大马力' in html or '最大功率' in html or '发动机' in html:
                logger.debug(f"В HTML найдены ключевые метки для car_id {car_id}")
            else:
                logger.warning(f"В HTML НЕ найдены ключевые метки (最大马力, 最大功率, 发动机) для car_id {car_id}")
                # Дополнительная диагностика
                logger.info(f"Проверяем, что есть в HTML: title={'title' in html.lower()}, body={'body' in html.lower()}, div={'div' in html}")
                has_chinese = any('\u4e00' <= c <= '\u9fff' for c in html[:10000])
                logger.info(f"Китайские символы в первых 10K: {has_chinese}")
            
            # Проверяем наличие числовых значений мощности
            power_patterns = re.findall(r'(\d+)\s*(?:Ps|kW|马力|功率)', html)
            if power_patterns:
                logger.debug(f"Найдены возможные значения мощности в HTML: {power_patterns[:5]}")
            else:
                # Ищем просто числа рядом с метками
                if '最大马力' in html:
                    # Ищем числа после "最大马力"
                    matches = re.findall(r'最大马力[^0-9]*(\d+)', html)
                    if matches:
                        logger.debug(f"Найдены числа после '最大马力': {matches[:5]}")
            
            # Проверяем, что HTML не пустой и содержит контент
            if len(html) < 1000:
                logger.warning(f"HTML слишком короткий для car_id: {car_id}, возможно страница не загрузилась")
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Парсим данные
            car_data = self._extract_car_data(soup, car_id, html)
            
            if car_data:
                # Проверяем, что хотя бы какие-то данные извлечены
                data_fields = {k: v for k, v in car_data.items() if k != 'car_id' and v is not None}
                if len(data_fields) > 0:
                    logger.info(f"Успешно извлечено {len(data_fields)} полей для car_id: {car_id}")
                    # Логируем названия полей для отладки
                    field_names = list(data_fields.keys())
                    logger.info(f"Извлеченные поля для car_id {car_id}: {field_names}")  # Все поля
                    # Логируем примеры значений для отладки
                    for field_name in field_names[:10]:  # Первые 10 полей
                        value = data_fields[field_name]
                        if isinstance(value, str) and len(value) > 100:
                            logger.debug(f"  {field_name}: {value[:100]}...")
                        else:
                            logger.debug(f"  {field_name}: {value}")
                    return Che168DetailedCar(**car_data)
                else:
                    logger.warning(f"Данные извлечены, но все поля пустые для car_id: {car_id}")
                    # Сохраняем HTML для отладки, если включен режим отладки
                    debug_dir = os.environ.get('CHE168_DEBUG_DIR')
                    if debug_dir:
                        os.makedirs(debug_dir, exist_ok=True)
                        debug_file = os.path.join(debug_dir, f'che168_debug_{car_id}.html')
                        try:
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(html)
                            logger.info(f"HTML сохранен для отладки: {debug_file}")
                        except Exception as e:
                            logger.warning(f"Не удалось сохранить HTML для отладки: {e}")
            else:
                logger.warning(f"Не удалось извлечь данные для car_id: {car_id}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка парсинга car_id {car_id}: {e}", exc_info=True)
            return None
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_car_data(self, soup: BeautifulSoup, car_id: int, html: str = "") -> Optional[Dict[str, Any]]:
        """Извлекает данные о машине из HTML"""
        try:
            data = {
                'car_id': car_id
            }
            
            # Сначала пытаемся найти JSON-данные в script тегах (как в dongchedi)
            json_data_found = self._extract_from_json(soup, html, data)
            
            # Основная информация
            self._extract_basic_info(soup, data)
            
            # Технические характеристики
            self._extract_technical_specs(soup, data)
            
            # Дополнительные характеристики
            self._extract_additional_specs(soup, data)
            
            # Изображения
            self._extract_images(soup, data)
            
            # Описание
            self._extract_description(soup, data)
            
            return data
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных: {e}", exc_info=True)
            return None
    
    def _extract_from_json(self, soup: BeautifulSoup, html: str, data: Dict[str, Any]) -> bool:
        """Извлекает данные из JSON в script тегах"""
        try:
            # Ищем все script теги с JSON-данными
            script_tags = soup.find_all('script', type=lambda x: x and ('json' in x.lower() or x == 'application/json'))
            
            # Также ищем script теги с id или class, которые могут содержать данные
            for script in soup.find_all('script'):
                script_text = script.string or script.get_text()
                if not script_text:
                    continue
                
                # Ищем JSON-структуры в тексте скрипта
                # Паттерны для поиска JSON-данных о машине
                json_patterns = [
                    r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                    r'window\.__NUXT__\s*=\s*({.+?});',
                    r'var\s+carInfo\s*=\s*({.+?});',
                    r'var\s+detailData\s*=\s*({.+?});',
                    r'"carInfo"\s*:\s*({.+?})',
                    r'"detail"\s*:\s*({.+?})',
                ]
                
                for pattern in json_patterns:
                    matches = re.finditer(pattern, script_text, re.DOTALL)
                    for match in matches:
                        try:
                            json_str = match.group(1)
                            json_data = json.loads(json_str)
                            if self._parse_json_data(json_data, data):
                                logger.info("Найдены JSON-данные в script теге")
                                return True
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            continue
            
            # Ищем __NEXT_DATA__ или подобные структуры
            next_data_script = soup.find('script', {'id': '__NEXT_DATA__'})
            if next_data_script and next_data_script.string:
                try:
                    json_data = json.loads(next_data_script.string)
                    if self._parse_json_data(json_data, data):
                        logger.info("Найдены JSON-данные в __NEXT_DATA__")
                        return True
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.debug(f"Не удалось распарсить __NEXT_DATA__: {e}")
            
            return False
            
        except Exception as e:
            logger.debug(f"Ошибка поиска JSON-данных: {e}")
            return False
    
    def _parse_json_data(self, json_data: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Парсит JSON-данные и извлекает информацию о машине"""
        try:
            found_any = False
            
            # Рекурсивный поиск данных о машине в JSON
            def search_in_dict(obj, path=""):
                nonlocal found_any
                if isinstance(obj, dict):
                    # Ищем ключевые поля
                    if 'title' in obj or 'carName' in obj or 'name' in obj:
                        title = obj.get('title') or obj.get('carName') or obj.get('name')
                        if title and not data.get('title'):
                            data['title'] = str(title)
                            found_any = True
                    
                    if 'price' in obj or 'carPrice' in obj:
                        price = obj.get('price') or obj.get('carPrice')
                        if price and not data.get('price'):
                            data['price'] = str(price)
                            found_any = True
                    
                    if 'year' in obj or 'carYear' in obj:
                        year = obj.get('year') or obj.get('carYear')
                        if year and not data.get('year'):
                            try:
                                data['year'] = int(year)
                                found_any = True
                            except (ValueError, TypeError):
                                pass
                    
                    if 'mileage' in obj or 'carMileage' in obj:
                        mileage = obj.get('mileage') or obj.get('carMileage')
                        if mileage and not data.get('mileage'):
                            data['mileage'] = str(mileage)
                            found_any = True
                    
                    if 'images' in obj or 'imageList' in obj or 'headImages' in obj:
                        images = obj.get('images') or obj.get('imageList') or obj.get('headImages')
                        if isinstance(images, list) and images:
                            image_urls = [str(img) for img in images if img]
                            if image_urls and not data.get('image_gallery'):
                                data['image_gallery'] = ' '.join(image_urls)
                                data['image_count'] = len(image_urls)
                                found_any = True
                    
                    # Рекурсивно ищем в вложенных объектах
                    for key, value in obj.items():
                        search_in_dict(value, f"{path}.{key}" if path else key)
                        
                elif isinstance(obj, list):
                    for item in obj:
                        search_in_dict(item, path)
            
            search_in_dict(json_data)
            return found_any
            
        except Exception as e:
            logger.debug(f"Ошибка парсинга JSON-данных: {e}")
            return False
    
    def _extract_basic_info(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает основную информацию о машине"""
        logger.debug("Начало извлечения основной информации")
        try:
            # Вспомогательная функция для безопасной проверки класса
            def class_contains(search_term):
                def check_class(x):
                    if x is None:
                        return False
                    if isinstance(x, list):
                        return any(search_term in str(cls).lower() for cls in x if cls)
                    return search_term in str(x).lower()
                return check_class
            
            # Заголовок - ищем в разных местах
            if not data.get('title'):
                # Ищем заголовок в структуре с CSS-in-JS классами (обычно жирный текст)
                title_elem = (soup.find('h1') or 
                             soup.find('h2', class_=class_contains('title')) or
                             soup.find('div', class_=class_contains('title')) or
                             soup.find('title'))
                
                # Также ищем в div'ах с жирным текстом (font-weight: bold)
                if not title_elem:
                    bold_divs = soup.find_all('div', style=lambda x: x and 'font-weight' in str(x) and 'bold' in str(x))
                    for bold_div in bold_divs:
                        title_text = bold_div.get_text(strip=True)
                        # Заголовок обычно содержит марку и модель
                        if title_text and len(title_text) > 5 and len(title_text) < 100:
                            # Проверяем, что это похоже на заголовок (содержит год или марку)
                            if any(keyword in title_text for keyword in ['款', '年', '系', '型']) or \
                               any(char.isdigit() for char in title_text):
                                data['title'] = title_text
                                break
                
                if title_elem and not data.get('title'):
                    title_text = title_elem.get_text(strip=True)
                    if title_text and len(title_text) > 0:
                        data['title'] = title_text
            
            # Цена - ищем в разных форматах
            if not data.get('price'):
                # Ищем элементы с классом price или содержащие символы цены
                price_selectors = [
                    {'class': class_contains('price')},
                    {'class': class_contains('money')},
                    {'id': lambda x: x and 'price' in str(x).lower()},
                ]
                for selector in price_selectors:
                    price_elem = soup.find('div', selector) or soup.find('span', selector)
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        if price_text and ('万' in price_text or '元' in price_text):
                            data['price'] = price_text
                            break
                
                # Если не нашли, ищем по тексту (формат "26.8万" или "12.8万")
                if not data.get('price'):
                    # Ищем div'ы с ценой в формате "XX.XX万"
                    price_pattern = re.compile(r'[\d.]+万')
                    price_divs = soup.find_all('div', string=price_pattern)
                    for price_div in price_divs:
                        price_text = price_div.get_text(strip=True)
                        if price_text:
                            # Берем родительский элемент для получения полной цены
                            parent = price_div.find_parent('div')
                            if parent:
                                full_price = parent.get_text(strip=True)
                                # Ищем паттерн цены
                                price_match = re.search(r'[\d.]+万', full_price)
                                if price_match:
                                    data['price'] = price_match.group(0)
                                    break
                
                # Если все еще не нашли, ищем по тексту
                if not data.get('price'):
                    price_text_elem = soup.find(text=lambda t: t and ('万' in str(t) or '元' in str(t)) and any(c.isdigit() for c in str(t)))
                    if price_text_elem:
                        parent = price_text_elem.parent
                        if parent:
                            data['price'] = parent.get_text(strip=True)
            
            # Год - ищем 4-значные числа в контексте года
            if not data.get('year'):
                # Ищем в тексте года
                year_pattern = re.compile(r'(19|20)\d{2}')
                year_elem = soup.find(text=year_pattern)
                if year_elem:
                    match = year_pattern.search(year_elem)
                    if match:
                        try:
                            year = int(match.group())
                            if 1900 <= year <= 2100:  # Разумный диапазон
                                data['year'] = year
                        except ValueError:
                            pass
            
            # Пробег - ищем в разных форматах
            if not data.get('mileage'):
                mileage_selectors = [
                    {'class': class_contains('mileage')},
                    {'class': class_contains('里程')},
                ]
                for selector in mileage_selectors:
                    mileage_elem = soup.find('div', selector) or soup.find('span', selector)
                    if mileage_elem:
                        mileage_text = mileage_elem.get_text(strip=True)
                        if mileage_text and ('万公里' in mileage_text or '公里' in mileage_text):
                            data['mileage'] = mileage_text
                            break
                
                # Если не нашли, ищем по тексту
                if not data.get('mileage'):
                    mileage_text_elem = soup.find(text=lambda t: t and ('万公里' in str(t) or '公里' in str(t)) and any(c.isdigit() for c in str(t)))
                    if mileage_text_elem:
                        parent = mileage_text_elem.parent
                        if parent:
                            data['mileage'] = parent.get_text(strip=True)
            
            # Город - ищем в разных местах
            if not data.get('city'):
                city_selectors = [
                    {'class': class_contains('city')},
                    {'class': class_contains('城市')},
                ]
                for selector in city_selectors:
                    city_elem = soup.find('div', selector) or soup.find('span', selector)
                    if city_elem:
                        city_text = city_elem.get_text(strip=True)
                        if city_text and '市' in city_text:
                            data['city'] = city_text
                            break
                
                # Если не нашли, ищем по тексту
                if not data.get('city'):
                    city_text_elem = soup.find(text=lambda t: t and '市' in str(t) and len(str(t).strip()) < 20)
                    if city_text_elem:
                        data['city'] = city_text_elem.strip()
            
            # Марка и модель
            if not data.get('brand_name'):
                brand_elem = soup.find('div', class_=class_contains('brand')) or \
                           soup.find('span', class_=class_contains('brand'))
                if brand_elem:
                    data['brand_name'] = brand_elem.get_text(strip=True)
            
            if not data.get('series_name'):
                def series_class_check(x):
                    if x is None:
                        return False
                    if isinstance(x, list):
                        x_str = ' '.join(str(cls) for cls in x if cls)
                    else:
                        x_str = str(x)
                    return 'series' in x_str.lower() or 'model' in x_str.lower()
                
                series_elem = soup.find('div', class_=series_class_check) or \
                            soup.find('span', class_=series_class_check)
                if series_elem:
                    data['series_name'] = series_elem.get_text(strip=True)
            
            # НОВЫЙ СПОСОБ: Ищем данные в секции "档案" (Архив)
            # Ищем разными способами
            archive_section = None
            # Способ 1: поиск по тексту
            for text_node in soup.find_all(string=True):
                if '档案' in str(text_node).strip():
                    archive_section = text_node.find_parent('div')
                    if archive_section:
                        break
            
            # Способ 2: поиск по div с текстом
            if not archive_section:
                archive_section = soup.find('div', string=lambda text: text and '档案' in str(text))
            
            if archive_section:
                logger.debug("Найдена секция '档案'")
                archive_parent = archive_section.find_parent('div')
                if archive_parent:
                    # Ищем "上牌时间" (дата регистрации) - может содержать год
                    registration_elem = archive_parent.find('div', string=lambda text: text and '上牌时间' in str(text))
                    if registration_elem and not data.get('year'):
                        # Ищем значение даты
                        parent = registration_elem.find_parent('div')
                        if parent:
                            # Ищем текст с датой (формат YYYY-MM или YYYY年)
                            date_pattern = re.compile(r'(\d{4})[-年](\d{1,2})?')
                            date_text = parent.get_text()
                            match = date_pattern.search(date_text)
                            if match:
                                try:
                                    year = int(match.group(1))
                                    if 1900 <= year <= 2100:
                                        data['year'] = year
                                        data['inspection_date'] = match.group(0)
                                except ValueError:
                                    pass
                    
                    # Ищем "表显里程" (пробег)
                    mileage_elem = archive_parent.find('div', string=lambda text: text and '表显里程' in str(text))
                    if mileage_elem and not data.get('mileage'):
                        parent = mileage_elem.find_parent('div')
                        if parent:
                            # Ищем текст с пробегом
                            mileage_text = parent.get_text()
                            # Ищем паттерн типа "5.85万公里"
                            mileage_match = re.search(r'[\d.]+万?公里', mileage_text)
                            if mileage_match:
                                data['mileage'] = mileage_match.group(0)
                    
                    # Ищем "所在地区" (город)
                    city_elem = archive_parent.find('div', string=lambda text: text and '所在地区' in str(text))
                    if city_elem and not data.get('city'):
                        parent = city_elem.find_parent('div')
                        if parent:
                            # Ищем текст города (обычно короткий текст без цифр)
                            city_texts = parent.find_all(string=True, recursive=True)
                            for text in city_texts:
                                text_str = str(text).strip()
                                if text_str and '所在地区' not in text_str and len(text_str) < 20:
                                    # Город обычно содержит иероглиф "市" или короткий текст
                                    if '市' in text_str or (len(text_str) <= 10 and not any(c.isdigit() for c in text_str)):
                                        data['city'] = text_str
                                        break
                    
                    # Ищем "排放标准" (стандарт выбросов)
                    emission_elem = archive_parent.find('div', string=lambda text: text and '排放标准' in str(text))
                    if emission_elem and not data.get('emission_standard'):
                        parent = emission_elem.find_parent('div')
                        if parent:
                            emission_text = parent.get_text()
                            # Ищем стандарт (如 "国V", "国VI")
                            emission_match = re.search(r'国[IVX]+', emission_text)
                            if emission_match:
                                data['emission_standard'] = emission_match.group(0)
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения основной информации: {e}")
    
    def _extract_technical_specs(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает технические характеристики"""
        logger.debug("Начало извлечения технических характеристик")
        try:
            # Полный маппинг китайских меток на поля модели
            field_mapping = {
                # Основные характеристики
                '排量': 'engine_volume',
                '排量(L)': 'engine_volume',
                '排量(mL)': 'engine_volume',
                '发动机': 'engine_type',
                '燃料类型': 'fuel_type',
                '燃料形式': 'fuel_type',
                '变速箱': 'transmission',
                '驱动方式': 'drive_type',
                '车身结构': 'body_type',
                '颜色': 'color',
                '车况': 'condition',
                
                # Мощность и производительность
                '最大马力': 'power',
                '最大马力(Ps)': 'power',
                '最大功率': 'power',
                '最大功率(kW)': 'power',
                '功率': 'power',
                '马力': 'power',
                '最大扭矩': 'torque',
                '最大扭矩(N·m)': 'torque',
                '扭矩': 'torque',
                '加速时间': 'acceleration',
                '百公里加速': 'acceleration',
                '百公里加速时间': 'acceleration',
                '官方百公里加速时间(s)': 'acceleration',
                '最高车速': 'max_speed',
                '最高车速(km/h)': 'max_speed',
                
                # Расход и экология
                '油耗': 'fuel_consumption',
                '百公里油耗': 'fuel_consumption',
                '百公里耗电量': 'fuel_consumption',
                '百公里耗电量(kWh/100km)': 'fuel_consumption',
                '排放标准': 'emission_standard',
                
                # Размеры
                '长': 'length',
                '长(mm)': 'length',
                '宽': 'width',
                '宽(mm)': 'width',
                '高': 'height',
                '高(mm)': 'height',
                '长x宽x高': 'dimensions',  # Специальная обработка
                '长x宽x高(mm)': 'dimensions',
                '轴距': 'wheelbase',
                '轴距(mm)': 'wheelbase',
                
                # Масса
                '整备质量': 'curb_weight',
                '整备质量(kg)': 'curb_weight',
                '总质量': 'gross_weight',
                '总质量(kg)': 'gross_weight',
                
                # Двигатель (детали)
                '发动机型号': 'engine_code',
                '气缸数': 'cylinder_count',
                '每缸气门数': 'valve_count',
                '压缩比': 'compression_ratio',
                '涡轮增压': 'turbo_type',
                
                # Трансмиссия
                '变速箱类型': 'transmission_type',
                '挡位个数': 'gear_count',
                
                # Подвеска и тормоза
                '前悬架类型': 'front_suspension',
                '后悬架类型': 'rear_suspension',
                '前制动器类型': 'front_brakes',
                '后制动器类型': 'rear_brakes',
                '制动系统': 'brake_system',
                
                # Колеса и шины
                '轮胎规格': 'tire_size',
                '轮毂规格': 'wheel_size',
                '轮毂类型': 'wheel_type',
                '轮胎类型': 'tire_type',
                
                # Электромобили
                '电池容量': 'battery_capacity',
                '电池容量(kWh)': 'battery_capacity',
                '纯电续航里程': 'electric_range',
                '纯电续航里程(km)': 'electric_range',
                '充电时间': 'charging_time',
                '充电时间(小时)': 'charging_time',
                '快充时间': 'fast_charge_time',
                '快充时间(小时)': 'fast_charge_time',
                '充电接口类型': 'charge_port_type',
                
                # Дифференциал
                '差速器类型': 'differential_type',
                '差速锁': 'differential_type',
                
                # Безопасность
                '安全气囊': 'airbag_count',
                '主/副驾驶座安全气囊': 'airbag_count',
                '前排安全气囊': 'airbag_count',
                '后排安全气囊': 'airbag_count',
                '侧安全气囊': 'airbag_count',
                '头部气囊': 'airbag_count',
                'ABS防抱死': 'abs',
                'ABS': 'abs',
                'ESP车身稳定系统': 'esp',
                'ESP': 'esp',
                'TCS牵引力控制系统': 'tcs',
                'TCS': 'tcs',
                '上坡辅助': 'hill_assist',
                '坡道辅助': 'hill_assist',
                '盲区监测': 'blind_spot_monitor',
                '盲点监测': 'blind_spot_monitor',
                '车道偏离预警': 'lane_departure',
                '车道保持': 'lane_departure',
                
                # Комфорт
                '空调': 'air_conditioning',
                '手动空调': 'air_conditioning',
                '自动空调': 'climate_control',
                '双区自动空调': 'climate_control',
                '三区自动空调': 'climate_control',
                '座椅加热': 'seat_heating',
                '前排座椅加热': 'seat_heating',
                '后排座椅加热': 'seat_heating',
                '座椅通风': 'seat_ventilation',
                '前排座椅通风': 'seat_ventilation',
                '座椅按摩': 'seat_massage',
                '方向盘加热': 'steering_wheel_heating',
                
                # Мультимедиа
                '导航系统': 'navigation',
                'GPS导航': 'navigation',
                '中控屏幕': 'audio_system',
                '音响系统': 'audio_system',
                '扬声器数量': 'speakers_count',
                '扬声器': 'speakers_count',
                '蓝牙': 'bluetooth',
                '蓝牙/车载电话': 'bluetooth',
                'USB接口': 'usb',
                'USB': 'usb',
                'AUX接口': 'aux',
                'AUX': 'aux',
                
                # Освещение
                '前大灯类型': 'headlight_type',
                '大灯类型': 'headlight_type',
                '前大灯': 'headlight_type',
                '雾灯': 'fog_lights',
                '前雾灯': 'fog_lights',
                '后雾灯': 'fog_lights',
                'LED大灯': 'led_lights',
                'LED日间行车灯': 'daytime_running',
                '日间行车灯': 'daytime_running',
                
                # Цвета и отделка
                '内饰颜色': 'interior_color',
                '内饰': 'interior_color',
                '外观颜色': 'exterior_color',
                '车身颜色': 'exterior_color',
                '座椅材质': 'upholstery',
                '座椅': 'upholstery',
                '天窗': 'sunroof',
                '电动天窗': 'sunroof',
                '全景天窗': 'panoramic_roof',
                '全景天窗': 'panoramic_roof',
                
                # Дополнительные характеристики
                '座位数': 'seat_count',
                '座位': 'seat_count',
                '车门数': 'door_count',
                '车门': 'door_count',
                '行李箱容积': 'trunk_volume',
                '后备箱容积': 'trunk_volume',
                '油箱容积': 'fuel_tank_volume',
                '油箱容量': 'fuel_tank_volume',
            }
            
            # Ищем таблицы с характеристиками (старый способ)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        
                        if key in field_mapping and not data.get(field_mapping[key]):
                            data[field_mapping[key]] = value
            
            # НОВЫЙ СПОСОБ: Ищем данные в структуре с CSS-in-JS классами
            # Структура: <div class="css-175oi2r" style="flex-direction: row; align-items: center;">
            #   <div class="css-175oi2r" style="width: 610px;...">
            #     <div>2.0T</div>  <!-- значение -->
            #     <div>发动机</div>  <!-- метка -->
            #   </div>
            # </div>
            
            # СПОСОБ 1: Ищем родительский контейнер с несколькими элементами данных
            # Структура: <div class="css-175oi2r" style="flex-direction: row;...">
            #   <div class="css-175oi2r" style="width: 610px;...">
            #     <div class="css-1rynq56">2.0T</div>  <!-- значение -->
            #     <div class="css-1rynq56">发动机</div>  <!-- метка -->
            #   </div>
            # </div>
            try:
                logger.debug("Начинаем поиск данных - способ 1 (css-1rynq56, метка после значения)")
                
                # СПОСОБ 1: Ищем все div'ы с классом css-1rynq56 (текстовые элементы)
                # Структура: <div><div>2.0T</div><div class="css-1rynq56">发动机</div></div>
                # Значение может быть БЕЗ класса css-1rynq56, поэтому ищем среди ВСЕХ прямых потомков родителя
                all_text_divs = soup.find_all('div', class_=lambda x: x and 'css-1rynq56' in str(x))
                logger.debug(f"Найдено {len(all_text_divs)} div'ов с классом css-1rynq56")
                
                # Расширенный список меток для Способа 1
                способ1_метки = ['发动机', '变速箱', '百公里油耗', '燃料形式', '排量', 
                               '上牌时间', '表显里程', '排放标准', '所在地区']
                
                for div in all_text_divs:
                    div_text = div.get_text(strip=True)
                    
                    # Проверяем, является ли это меткой
                    if div_text in способ1_метки:
                        # Ищем родителя
                        parent = div.find_parent('div')
                        if parent:
                            # Ищем ВСЕ прямые потомки-div'ы родителя (не только с css-1rynq56!)
                            children = parent.find_all('div', recursive=False)
                            
                            try:
                                label_idx = children.index(div)
                                # Если метка не первая, берем предыдущего потомка как значение
                                if label_idx > 0:
                                    value_div = children[label_idx - 1]
                                    value_text = value_div.get_text(strip=True)
                                    label_text = div_text
                                    
                                    logger.info(f"Найдена пара (способ 1): значение='{value_text}', метка='{label_text}'")
                                    
                                    # Ищем соответствующее поле
                                    for mapping_label, field_name in field_mapping.items():
                                        if data.get(field_name):
                                            continue
                                        if label_text == mapping_label or label_text in mapping_label or mapping_label in label_text:
                                            data[field_name] = value_text
                                            logger.info(f"✓ Найдено {field_name}: {value_text} по метке {label_text} (способ 1)")
                                            break
                            except ValueError:
                                pass
                
                logger.debug("Начинаем поиск данных - способ 2 (любые div, метка перед значением)")
                
                # СПОСОБ 2: Ищем div'ы, содержащие метки (без требования к классу css-1rynq56)
                # Структура: <div class="css-175oi2r"><div>最大马力(Ps)</div><div>184</div></div>
                all_divs = soup.find_all('div')
                logger.debug(f"Проверяем все {len(all_divs)} div'ов на наличие меток")
                
                found_count = 0
                for div in all_divs:
                    div_text = div.get_text(strip=True)
                    
                    # Проверяем, является ли это меткой (метка может быть с единицами в скобках)
                    label_matches = [
                        # Мощность и производительность
                        ('最大马力(Ps)', 'power'),
                        ('最大马力', 'power'),
                        ('最大功率(kW)', 'power_kw'),
                        ('最大功率', 'power_kw'),
                        ('最大扭矩(N·m)', 'torque'),
                        ('最大扭矩', 'torque'),
                        ('加速时间', 'acceleration'),
                        ('0-100km/h加速', 'acceleration'),
                        ('最高车速', 'max_speed'),
                        
                        # Двигатель
                        ('排量(L)', 'engine_volume'),
                        ('排量', 'engine_volume'),
                        ('发动机型号', 'engine_code'),
                        ('气缸数', 'cylinder_count'),
                        ('气缸排列形式', 'cylinder_arrangement'),
                        ('每缸气门数', 'valve_count'),
                        ('压缩比', 'compression_ratio'),
                        ('进气形式', 'turbo_type'),
                        
                        # Размеры
                        ('长x宽x高', 'dimensions'),
                        ('长*宽*高', 'dimensions'),
                        ('长×宽×高', 'dimensions'),
                        ('车身尺寸', 'dimensions'),
                        ('轴距', 'wheelbase'),
                        ('轴距(mm)', 'wheelbase'),
                        ('整备质量', 'curb_weight'),
                        ('整备质量(kg)', 'curb_weight'),
                        ('总质量', 'gross_weight'),
                        
                        # Трансмиссия и привод
                        ('变速箱类型', 'transmission_type'),
                        ('档位个数', 'gear_count'),
                        ('驱动方式', 'drive_type'),
                        ('四驱形式', 'differential_type'),
                        
                        # Подвеска и тормоза
                        ('前悬架类型', 'front_suspension'),
                        ('后悬架类型', 'rear_suspension'),
                        ('前制动器类型', 'front_brakes'),
                        ('后制动器类型', 'rear_brakes'),
                        ('驻车制动类型', 'brake_system'),
                        
                        # Колеса
                        ('轮胎规格', 'tire_size'),
                        ('前轮胎规格', 'front_tire_size'),
                        ('后轮胎规格', 'rear_tire_size'),
                        ('轮圈材质', 'wheel_type'),
                        
                        # Безопасность
                        ('安全气囊数量', 'airbag_count'),
                        ('主/副驾驶座安全气囊', 'airbag_front'),
                        ('ABS防抱死', 'abs'),
                        ('车身稳定控制', 'esp'),
                        ('牵引力控制', 'tcs'),
                        ('上坡辅助', 'hill_assist'),
                        ('陡坡缓降', 'hill_descent'),
                        ('并线辅助', 'blind_spot_monitor'),
                        ('车道偏离预警', 'lane_departure'),
                        
                        # Электро (для EV)
                        ('电池容量', 'battery_capacity'),
                        ('纯电续航', 'electric_range'),
                        ('快充时间', 'fast_charge_time'),
                        ('慢充时间', 'charging_time'),
                        
                        # Комфорт
                        ('空调', 'air_conditioning'),
                        ('空调类型', 'climate_control'),
                        ('座椅加热', 'seat_heating'),
                        ('座椅通风', 'seat_ventilation'),
                        ('座椅按摩', 'seat_massage'),
                        ('方向盘加热', 'steering_wheel_heating'),
                        
                        # Мультимедиа
                        ('GPS导航', 'navigation'),
                        ('导航系统', 'navigation'),
                        ('音响品牌', 'audio_system'),
                        ('扬声器数量', 'speakers_count'),
                        ('蓝牙', 'bluetooth'),
                        ('蓝牙/车载电话', 'bluetooth'),
                        ('车载电话', 'bluetooth'),
                        ('USB接口', 'usb'),
                        ('AUX接口', 'aux'),
                        
                        # Освещение
                        ('大灯类型', 'headlight_type'),
                        ('前大灯', 'headlight_type'),
                        ('前大灯类型', 'headlight_type'),
                        ('雾灯', 'fog_lights'),
                        ('LED日间行车灯', 'daytime_running'),
                        
                        # Интерьер и экстерьер
                        ('内饰颜色', 'interior_color'),
                        ('外观颜色', 'exterior_color'),
                        ('车身颜色', 'exterior_color'),
                        ('座椅材质', 'upholstery'),
                        ('天窗类型', 'sunroof'),
                        ('全景天窗', 'panoramic_roof'),
                        
                        # Дополнительные
                        ('座位数', 'seat_count'),
                        ('座椅数', 'seat_count'),
                        ('门数', 'door_count'),
                        ('行李箱容积', 'trunk_volume'),
                        ('后备箱容积', 'trunk_volume'),
                        ('油箱容积', 'fuel_tank_volume'),
                    ]
                    
                    for label_pattern, field_name in label_matches:
                        if div_text == label_pattern:  # Точное совпадение
                            if data.get(field_name):  # Уже найдено
                                continue
                            
                            # Ищем родителя
                            parent = div.find_parent('div')
                            if parent:
                                # Ищем всех прямых потомков-div'ов родителя
                                children = parent.find_all('div', recursive=False)
                                
                                # Находим индекс текущего div'а (с меткой)
                                try:
                                    label_idx = children.index(div)
                                    # Следующий div - это значение
                                    if label_idx + 1 < len(children):
                                        value_div = children[label_idx + 1]
                                        value_text = value_div.get_text(strip=True)
                                        
                                        # Проверяем, что значение не является другой меткой
                                        if value_text and value_text not in [lp for lp, _ in label_matches]:
                                            data[field_name] = value_text
                                            logger.info(f"✓ Найдено {field_name}: {value_text} по метке {label_pattern} (способ 2)")
                                            found_count += 1
                                except ValueError:
                                    pass
                
                logger.debug(f"Способ 2: найдено {found_count} новых полей")
                
            except Exception as e:
                logger.warning(f"Ошибка при поиске в контейнере: {e}", exc_info=True)
            
            # ПОСТ-ОБРАБОТКА: обрабатываем специальные поля
            try:
                # 1. Обработка dimensions (длина x ширина x высота)
                if 'dimensions' in data:
                    dims_text = data['dimensions']
                    dims = re.findall(r'(\d+)', dims_text)
                    if len(dims) >= 3:
                        data['length'] = dims[0] + 'mm'
                        data['width'] = dims[1] + 'mm'
                        data['height'] = dims[2] + 'mm'
                        logger.info(f"✓ Размеры разобраны: {data['length']} x {data['width']} x {data['height']}")
                
                # 2. Обработка mileage (преобразование "万公里" в км)
                if 'mileage' in data:
                    mileage_text = data['mileage']
                    match = re.search(r'(\d+\.?\d*)万公里', mileage_text)
                    if match:
                        mileage_wan = float(match.group(1))
                        mileage_km = int(mileage_wan * 10000)
                        data['mileage'] = str(mileage_km)
                        logger.info(f"✓ Пробег преобразован: {mileage_text} -> {mileage_km} км")
                
                # 3. Обработка year (из даты регистрации)
                if 'registration_date' in data and 'year' not in data:
                    reg_date = data['registration_date']
                    year_match = re.search(r'(\d{4})', reg_date)
                    if year_match:
                        data['year'] = int(year_match.group(1))
                        logger.info(f"✓ Год извлечен из даты регистрации: {data['year']}")
                
            except Exception as e:
                logger.warning(f"Ошибка при пост-обработке полей: {e}", exc_info=True)
            
            # СПОСОБ 3: Ищем данные по меткам (старый способ, но улучшенный)
            for label_text, field_name in field_mapping.items():
                if data.get(field_name):  # Пропускаем, если уже найдено
                    continue
                
                # Ищем все возможные варианты метки
                label_variants = [label_text]
                # Добавляем варианты без скобок
                if '(' in label_text:
                    label_variants.append(label_text.split('(')[0])
                # Добавляем варианты без единиц измерения
                label_clean = re.sub(r'\([^)]*\)', '', label_text).strip()
                if label_clean != label_text:
                    label_variants.append(label_clean)
                
                label_elem = None
                for variant in label_variants:
                    # СПОСОБ 1: Ищем точное совпадение в тексте div'а
                    label_elem = soup.find('div', string=lambda text: text and variant in str(text).strip())
                    if label_elem:
                        break
                    
                    # СПОСОБ 2: Ищем в текстовых узлах
                    for text_node in soup.find_all(string=True):
                        if variant in str(text_node).strip():
                            label_elem = text_node.find_parent('div')
                            if label_elem:
                                break
                    if label_elem:
                        break
                    
                    # СПОСОБ 3: Ищем в div'ах с классом css-175oi2r (специфичная структура che168)
                    # Структура: <div class="css-175oi2r"><div>значение</div><div>метка</div></div>
                    css_divs = soup.find_all('div', class_=lambda x: x and isinstance(x, list) and any('css-175oi2r' in str(c) for c in x))
                    for css_div in css_divs:
                        # Проверяем, содержит ли div метку
                        div_text = css_div.get_text()
                        if variant in div_text:
                            # Проверяем, есть ли дочерние div'ы
                            children = css_div.find_all('div', recursive=False)
                            if len(children) >= 2:
                                # Ищем метку в дочерних div'ах
                                for child in children:
                                    child_text = child.get_text(strip=True)
                                    if variant in child_text:
                                        label_elem = child
                                        break
                                if label_elem:
                                    break
                    if label_elem:
                        break
                
                if label_elem:
                    # Ищем значение в структуре
                    # Структура обычно: <div class="css-175oi2r"> <div>значение</div> <div>метка</div> </div>
                    # или наоборот: <div> <div>метка</div> <div>значение</div> </div>
                    parent = label_elem.find_parent('div')
                    if parent:
                        # СПОСОБ 1: Ищем в дочерних div'ах (siblings)
                        siblings = parent.find_all('div', recursive=False)
                        for sibling in siblings:
                            sib_text = sibling.get_text(strip=True)
                            # Пропускаем метку и пустые тексты
                            if not sib_text or sib_text == label_text or any(v in sib_text for v in label_variants):
                                continue
                            
                            # Проверяем, что это значение (содержит цифры, единицы измерения или известные значения)
                            has_digits = any(char.isdigit() for char in sib_text)
                            has_units = any(unit in sib_text for unit in ['L', 'T', '万', '公里', '元', '国', 'Ps', 'kW', 'N·m', 'km/h', 'kg', 'mm', 'kWh', '小时', 's', 'm'])
                            # Известные значения для полей без цифр
                            known_values = ['自动', '手动', '汽油', '柴油', '电动', '混动', '前置', '后置', '四驱', '前驱', '后驱', '有', '无', '是', '否']
                            has_known_value = any(val in sib_text for val in known_values)
                            
                            if has_digits or has_units or has_known_value:
                                # Проверяем, что это не другая метка
                                is_other_label = any(other_label in sib_text for other_label in field_mapping.keys() if other_label not in label_variants)
                                if not is_other_label and len(sib_text) < 100:
                                    # Специальная обработка для размеров "长x宽x高"
                                    if field_name == 'dimensions':
                                        # Парсим "1234x5678x9012" на отдельные значения
                                        dims = re.findall(r'(\d+)', sib_text)
                                        if len(dims) >= 3:
                                            data['length'] = dims[0] + 'mm'
                                            data['width'] = dims[1] + 'mm'
                                            data['height'] = dims[2] + 'mm'
                                    else:
                                        data[field_name] = sib_text
                                    logger.debug(f"Найдено {field_name}: {sib_text} по метке {label_text} (siblings)")
                                    break
                        
                        # СПОСОБ 2: Если не нашли в siblings, ищем в текстовых узлах родителя
                        # ВАЖНО: используем recursive=True, чтобы найти все текстовые узлы, включая вложенные
                        if not data.get(field_name):
                            # Ищем все текстовые узлы в родителе (включая вложенные)
                            # Сначала пробуем recursive=False для прямых дочерних узлов
                            all_texts_in_parent = parent.find_all(string=True, recursive=False)
                            if len(all_texts_in_parent) < 2:
                                # Если не нашли достаточно узлов, используем recursive=True
                                all_texts_in_parent = parent.find_all(string=True, recursive=True)
                            for i, text_node in enumerate(all_texts_in_parent):
                                text_str = str(text_node).strip()
                                # Проверяем, содержит ли текст метку
                                if any(v in text_str for v in label_variants):
                                    logger.debug(f"Найдена метка '{label_text}' в текстовом узле {i}: '{text_str[:50]}'")
                                    # Ищем значение - может быть до или после метки
                                    # Сначала ищем после метки (это основной случай для che168)
                                    for j in range(i + 1, min(i + 10, len(all_texts_in_parent))):
                                        value_text = str(all_texts_in_parent[j]).strip()
                                        if value_text and value_text not in label_variants and len(value_text) < 100:
                                            logger.debug(f"  Проверяем значение {j}: '{value_text}'")
                                            # Для power ищем числовые значения
                                            if field_name == 'power':
                                                # Ищем чисто числовое значение (например, "184" или "135")
                                                if value_text.isdigit() and int(value_text) > 0 and int(value_text) < 10000:
                                                    data[field_name] = value_text + 'Ps'
                                                    logger.info(f"✓ Найдено {field_name}: {value_text}Ps по метке {label_text} (текстовые узлы после)")
                                                    break
                                                # Или значение с единицами измерения
                                                elif any(unit in value_text for unit in ['Ps', 'kW', '马力', '功率']):
                                                    data[field_name] = value_text
                                                    logger.info(f"✓ Найдено {field_name}: {value_text} по метке {label_text} (текстовые узлы после)")
                                                    break
                                            else:
                                                has_digits = any(char.isdigit() for char in value_text)
                                                has_units = any(unit in value_text for unit in ['L', 'T', '万', '公里', '元', '国', 'Ps', 'kW', 'N·m', 'km/h', 'kg', 'mm', 'kWh', '小时', 's', 'm'])
                                                known_values = ['自动', '手动', '汽油', '柴油', '电动', '混动', '前置', '后置', '四驱', '前驱', '后驱', '有', '无', '是', '否']
                                                has_known_value = any(val in value_text for val in known_values)
                                                
                                                if has_digits or has_units or has_known_value:
                                                    is_other_label = any(other_label in value_text for other_label in field_mapping.keys() if other_label not in label_variants)
                                                    if not is_other_label:
                                                        if field_name == 'dimensions':
                                                            dims = re.findall(r'(\d+)', value_text)
                                                            if len(dims) >= 3:
                                                                data['length'] = dims[0] + 'mm'
                                                                data['width'] = dims[1] + 'mm'
                                                                data['height'] = dims[2] + 'mm'
                                                        else:
                                                            data[field_name] = value_text
                                                        logger.debug(f"Найдено {field_name}: {value_text} по метке {label_text} (текстовые узлы после)")
                                                        break
                                    # Если не нашли после, ищем до метки
                                    if not data.get(field_name):
                                        for j in range(max(0, i - 10), i):
                                            value_text = str(all_texts_in_parent[j]).strip()
                                            if value_text and value_text not in label_variants and len(value_text) < 100:
                                                # Для power ищем числовые значения
                                                if field_name == 'power':
                                                    if value_text.isdigit():
                                                        data[field_name] = value_text + 'Ps'
                                                        logger.debug(f"Найдено {field_name}: {value_text}Ps по метке {label_text} (текстовые узлы до)")
                                                        break
                                                    elif any(unit in value_text for unit in ['Ps', 'kW', '马力', '功率']):
                                                        data[field_name] = value_text
                                                        logger.debug(f"Найдено {field_name}: {value_text} по метке {label_text} (текстовые узлы до)")
                                                        break
                                                else:
                                                    has_digits = any(char.isdigit() for char in value_text)
                                                    has_units = any(unit in value_text for unit in ['L', 'T', '万', '公里', '元', '国', 'Ps', 'kW', 'N·m', 'km/h', 'kg', 'mm', 'kWh', '小时', 's', 'm'])
                                                    known_values = ['自动', '手动', '汽油', '柴油', '电动', '混动', '前置', '后置', '四驱', '前驱', '后驱', '有', '无', '是', '否']
                                                    has_known_value = any(val in value_text for val in known_values)
                                                    
                                                    if has_digits or has_units or has_known_value:
                                                        is_other_label = any(other_label in value_text for other_label in field_mapping.keys() if other_label not in label_variants)
                                                        if not is_other_label:
                                                            if field_name == 'dimensions':
                                                                dims = re.findall(r'(\d+)', value_text)
                                                                if len(dims) >= 3:
                                                                    data['length'] = dims[0] + 'mm'
                                                                    data['width'] = dims[1] + 'mm'
                                                                    data['height'] = dims[2] + 'mm'
                                                            else:
                                                                data[field_name] = value_text
                                                            logger.debug(f"Найдено {field_name}: {value_text} по метке {label_text} (текстовые узлы до)")
                                                            break
                                    break
                        
                        # СПОСОБ 3: Ищем в родительском контейнере (более широкий поиск)
                        if not data.get(field_name):
                            # Поднимаемся на уровень выше и ищем там
                            grandparent = parent.find_parent('div')
                            if grandparent:
                                # Ищем все текстовые узлы в дедушке
                                all_texts = grandparent.find_all(string=True, recursive=True)
                                for i, text_node in enumerate(all_texts):
                                    text_str = str(text_node).strip()
                                    if any(v in text_str for v in label_variants):
                                        # Ищем следующее значение после метки
                                        for j in range(i + 1, min(i + 10, len(all_texts))):
                                            value_text = str(all_texts[j]).strip()
                                            if value_text and value_text not in label_variants and len(value_text) < 100:
                                                # Проверяем, что это значение
                                                has_digits = any(char.isdigit() for char in value_text)
                                                has_units = any(unit in value_text for unit in ['L', 'T', '万', '公里', '元', '国', 'Ps', 'kW', 'N·m', 'km/h', 'kg', 'mm', 'kWh', '小时', 's', 'm'])
                                                known_values = ['自动', '手动', '汽油', '柴油', '电动', '混动', '前置', '后置', '四驱', '前驱', '后驱', '有', '无', '是', '否']
                                                has_known_value = any(val in value_text for val in known_values)
                                                
                                                if has_digits or has_units or has_known_value:
                                                    # Проверяем, что это не другая метка
                                                    is_other_label = any(other_label in value_text for other_label in field_mapping.keys() if other_label not in label_variants)
                                                    if not is_other_label:
                                                        if field_name == 'dimensions':
                                                            dims = re.findall(r'(\d+)', value_text)
                                                            if len(dims) >= 3:
                                                                data['length'] = dims[0] + 'mm'
                                                                data['width'] = dims[1] + 'mm'
                                                                data['height'] = dims[2] + 'mm'
                                                        else:
                                                            data[field_name] = value_text
                                                        logger.debug(f"Найдено {field_name}: {value_text} по метке {label_text} (из родительского контейнера)")
                                                        break
                                        break
                        
                        # Если не нашли в siblings, ищем в родительском контейнере
                        if not data.get(field_name):
                            all_texts = parent.find_all(string=True, recursive=True)
                            for i, text_node in enumerate(all_texts):
                                text_str = str(text_node).strip()
                                if any(v in text_str for v in label_variants):
                                    # Ищем следующее значение после метки
                                    for j in range(i + 1, len(all_texts)):
                                        value_text = str(all_texts[j]).strip()
                                        if value_text and len(value_text) < 100:
                                            # Проверяем, что это значение
                                            has_digits = any(char.isdigit() for char in value_text)
                                            has_units = any(unit in value_text for unit in ['L', 'T', '万', '公里', '元', '国', 'Ps', 'kW', 'N·m', 'km/h', 'kg', 'mm', 'kWh', '小时', 's', 'm'])
                                            known_values = ['自动', '手动', '汽油', '柴油', '电动', '混动', '前置', '后置', '四驱', '前驱', '后驱', '有', '无', '是', '否']
                                            has_known_value = any(val in value_text for val in known_values)
                                            
                                            if has_digits or has_units or has_known_value:
                                                # Проверяем, что это не другая метка
                                                if not any(other_label in value_text for other_label in field_mapping.keys() if other_label not in label_variants):
                                                    if field_name == 'dimensions':
                                                        dims = re.findall(r'(\d+)', value_text)
                                                        if len(dims) >= 3:
                                                            data['length'] = dims[0] + 'mm'
                                                            data['width'] = dims[1] + 'mm'
                                                            data['height'] = dims[2] + 'mm'
                                                    else:
                                                        data[field_name] = value_text
                                                    logger.debug(f"Найдено {field_name}: {value_text} по метке {label_text} (из текстовых узлов)")
                                                    break
                                    break
            
            # Также ищем данные в секции "参数" (Параметры)
            params_section = None
            # Способ 1: поиск по тексту
            for text_node in soup.find_all(string=True):
                if '参数' in str(text_node).strip():
                    params_section = text_node.find_parent('div')
                    if params_section:
                        break
            
            # Способ 2: поиск по div с текстом
            if not params_section:
                params_section = soup.find('div', string=lambda text: text and '参数' in str(text))
            
            if params_section:
                logger.debug("Найдена секция '参数'")
                params_parent = params_section.find_parent('div')
                if params_parent:
                    # Расширенный маппинг для секции параметров
                    params_mapping = {
                        '发动机': 'engine_type',
                        '变速箱': 'transmission',
                        '百公里油耗': 'fuel_consumption',
                        '燃料形式': 'fuel_type',
                        '排量': 'engine_volume',
                        '最大马力': 'power',
                        '最大马力(Ps)': 'power',
                        '最大功率': 'power',
                        '最大功率(kW)': 'power',
                        '最大扭矩': 'torque',
                        '最大扭矩(N·m)': 'torque',
                        '驱动方式': 'drive_type',
                    }
                    self._extract_from_section(params_parent, params_mapping, data)
            
            # Дополнительный поиск: ищем все текстовые узлы, содержащие метки
            # Это помогает найти данные, которые не находятся стандартным способом
            logger.debug(f"После стандартного поиска найдено полей: {len([k for k, v in data.items() if v is not None and k != 'car_id'])}")
            
            # Пробуем найти данные через поиск всех текстовых узлов с метками
            all_text_nodes = soup.find_all(string=True)
            for text_node in all_text_nodes:
                text_str = str(text_node).strip()
                if not text_str or len(text_str) > 50:
                    continue
                
                # Проверяем каждую метку из field_mapping
                for label_text, field_name in field_mapping.items():
                    if data.get(field_name):  # Уже найдено
                        continue
                    
                    # Проверяем, содержит ли текст метку
                    if label_text in text_str:
                        # Ищем значение в соседних узлах
                        parent = text_node.find_parent('div')
                        if parent:
                            # Ищем все текстовые узлы в родителе
                            sibling_texts = parent.find_all(string=True, recursive=True)
                            for i, sibling_text in enumerate(sibling_texts):
                                if str(sibling_text).strip() == text_str:
                                    # Берем следующий текстовый узел как значение
                                    if i + 1 < len(sibling_texts):
                                        value_text = str(sibling_texts[i + 1]).strip()
                                        if value_text and value_text != text_str and len(value_text) < 100:
                                            # Проверяем, что это значение
                                            has_digits = any(char.isdigit() for char in value_text)
                                            has_units = any(unit in value_text for unit in ['L', 'T', '万', '公里', '元', '国', 'Ps', 'kW', 'N·m', 'km/h', 'kg', 'mm', 'kWh', '小时', 's', 'm'])
                                            known_values = ['自动', '手动', '汽油', '柴油', '电动', '混动', '前置', '后置', '四驱', '前驱', '后驱', '有', '无', '是', '否']
                                            has_known_value = any(val in value_text for val in known_values)
                                            
                                            if has_digits or has_units or has_known_value:
                                                # Проверяем, что это не другая метка
                                                is_other_label = any(other_label in value_text for other_label in field_mapping.keys() if other_label != label_text)
                                                if not is_other_label:
                                                    data[field_name] = value_text
                                                    logger.debug(f"Найдено {field_name}: {value_text} через поиск текстовых узлов")
                                                    break
                                    break
                        break
            
            logger.debug(f"После дополнительного поиска найдено полей: {len([k for k, v in data.items() if v is not None and k != 'car_id'])}")
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения технических характеристик: {e}")
    
    def _extract_from_section(self, section_elem, label_mapping: Dict[str, str], data: Dict[str, Any]):
        """Извлекает данные из секции по меткам"""
        try:
            for label_text, field_name in label_mapping.items():
                if data.get(field_name):  # Пропускаем, если уже найдено
                    continue
                
                # Ищем все варианты метки
                label_variants = [label_text]
                if '(' in label_text:
                    label_variants.append(label_text.split('(')[0])
                label_clean = re.sub(r'\([^)]*\)', '', label_text).strip()
                if label_clean != label_text:
                    label_variants.append(label_clean)
                
                label_elem = None
                for variant in label_variants:
                    # Ищем метку в секции
                    label_elem = section_elem.find('div', string=lambda text: text and variant in str(text).strip())
                    if label_elem:
                        break
                    
                    # Также ищем в текстовых узлах
                    for text_node in section_elem.find_all(string=True):
                        if variant in str(text_node).strip():
                            label_elem = text_node.find_parent('div')
                            if label_elem:
                                break
                    if label_elem:
                        break
                
                if label_elem:
                    # Ищем значение - обычно в следующем div или в родительском контейнере
                    parent = label_elem.find_parent('div')
                    if parent:
                        # Сначала ищем в siblings (соседних div'ах)
                        siblings = parent.find_all('div', recursive=False)
                        for sibling in siblings:
                            sib_text = sibling.get_text(strip=True)
                            if not sib_text or any(v in sib_text for v in label_variants):
                                continue
                            
                            # Проверяем, что это значение
                            has_digits = any(char.isdigit() for char in sib_text)
                            has_units = any(unit in sib_text for unit in ['L', 'T', '万', '公里', '元', '国', 'Ps', 'kW', 'N·m', 'km/h', 'kg', 'mm', 'kWh', '小时', 's', 'm'])
                            known_values = ['自动', '手动', '汽油', '柴油', '电动', '混动', '前置', '后置', '四驱', '前驱', '后驱', '有', '无', '是', '否']
                            has_known_value = any(val in sib_text for val in known_values)
                            
                            if has_digits or has_units or has_known_value:
                                is_other_label = any(other_label in sib_text for other_label in label_mapping.keys() if other_label not in label_variants)
                                if not is_other_label and len(sib_text) < 100:
                                    data[field_name] = sib_text
                                    logger.debug(f"Найдено {field_name}: {sib_text} из секции (siblings)")
                                    break
                        
                        # Если не нашли в siblings, ищем в текстовых узлах
                        if not data.get(field_name):
                            all_texts = parent.find_all(string=True, recursive=True)
                            for i, text in enumerate(all_texts):
                                text_str = str(text).strip()
                                if any(v in text_str for v in label_variants):
                                    # Берем следующий непустой текст как значение
                                    for j in range(i + 1, len(all_texts)):
                                        value_text = str(all_texts[j]).strip()
                                        if value_text and value_text not in label_variants and len(value_text) < 100:
                                            # Проверяем, что это значение, а не другая метка
                                            has_digits = any(char.isdigit() for char in value_text)
                                            has_units = any(unit in value_text for unit in ['L', 'T', '万', '公里', '元', '国', 'Ps', 'kW', 'N·m', 'km/h', 'kg', 'mm', 'kWh', '小时', 's', 'm'])
                                            known_values = ['自动', '手动', '汽油', '柴油', '电动', '混动', '前置', '后置', '四驱', '前驱', '后驱', '有', '无', '是', '否']
                                            has_known_value = any(val in value_text for val in known_values)
                                            
                                            if has_digits or has_units or has_known_value:
                                                is_other_label = any(other_label in value_text for other_label in label_mapping.keys() if other_label not in label_variants)
                                                if not is_other_label:
                                                    data[field_name] = value_text
                                                    logger.debug(f"Найдено {field_name}: {value_text} из секции (текстовые узлы)")
                                                    break
                                    break
        except Exception as e:
            logger.debug(f"Ошибка извлечения из секции: {e}")
    
    def _extract_additional_specs(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает дополнительные характеристики"""
        try:
            # Вспомогательная функция для безопасной проверки класса
            def spec_class_check(x):
                if x is None:
                    return False
                if isinstance(x, list):
                    x_str = ' '.join(str(cls) for cls in x if cls)
                else:
                    x_str = str(x)
                return 'spec' in x_str.lower() or 'info' in x_str.lower()
            
            # Ищем div'ы с характеристиками
            spec_divs = soup.find_all('div', class_=spec_class_check)
            
            for div in spec_divs:
                text = div.get_text(strip=True)
                
                # Извлекаем информацию о владельцах
                if '手' in text and '车' in text:
                    owner_match = re.search(r'(\d+)手', text)
                    if owner_match:
                        data['owner_count'] = int(owner_match.group(1))
                
                # Извлекаем информацию о ДТП
                if '事故' in text:
                    data['accident_history'] = text
                
                # Извлекаем информацию о сервисе
                if '保养' in text or '维修' in text:
                    data['service_history'] = text
            
            # Ищем информацию о владельцах в тексте (формат "0次过户")
            if not data.get('owner_count'):
                owner_elem = soup.find('div', string=lambda text: text and '次过户' in str(text))
                if owner_elem:
                    owner_text = owner_elem.get_text(strip=True)
                    owner_match = re.search(r'(\d+)次过户', owner_text)
                    if owner_match:
                        data['owner_count'] = int(owner_match.group(1))
                
                # Также ищем в родительском элементе
                if not data.get('owner_count'):
                    owner_texts = soup.find_all(string=re.compile(r'\d+次过户'))
                    for owner_text in owner_texts:
                        owner_match = re.search(r'(\d+)次过户', str(owner_text))
                        if owner_match:
                            data['owner_count'] = int(owner_match.group(1))
                            break
            
            # Ищем информацию о сертификации и других тегах
            certification_tags = soup.find_all('div', string=lambda text: text and any(
                tag in str(text) for tag in ['4S直卖', '原厂质保', '有礼赠送', '低价豪车', '新上架']
            ))
            if certification_tags:
                cert_texts = [tag.get_text(strip=True) for tag in certification_tags]
                data['certification'] = ', '.join(cert_texts)
            
            # Ищем секцию "亮点" (особенности) и извлекаем опции
            highlights_section = soup.find('div', string=lambda text: text and '亮点' in str(text))
            if highlights_section:
                highlights_parent = highlights_section.find_parent('div')
                if highlights_parent:
                    # Ищем все текстовые элементы в секции
                    highlight_texts = highlights_parent.find_all(string=True, recursive=True)
                    highlight_features = []
                    
                    # Маппинг особенностей на поля
                    feature_mapping = {
                        'ISOFIX': 'airbag_count',  # ISOFIX儿童座椅接口
                        '自动驻车': 'hill_assist',
                        '上坡辅助': 'hill_assist',
                        '蓝牙': 'bluetooth',
                        '蓝牙/车载电话': 'bluetooth',
                        '转向辅助灯': 'fog_lights',
                        'LED': 'led_lights',
                        'LED大灯': 'led_lights',
                        '日间行车灯': 'daytime_running',
                        '导航': 'navigation',
                        'GPS': 'navigation',
                        'USB': 'usb',
                        'AUX': 'aux',
                        '座椅加热': 'seat_heating',
                        '座椅通风': 'seat_ventilation',
                        '座椅按摩': 'seat_massage',
                        '方向盘加热': 'steering_wheel_heating',
                        '空调': 'air_conditioning',
                        '自动空调': 'climate_control',
                        '天窗': 'sunroof',
                        '全景天窗': 'panoramic_roof',
                        'ABS': 'abs',
                        'ESP': 'esp',
                        'TCS': 'tcs',
                    }
                    
                    for text_node in highlight_texts:
                        text_str = str(text_node).strip()
                        if not text_str or len(text_str) > 50:
                            continue
                        
                        # Проверяем каждую особенность
                        for feature_key, field_name in feature_mapping.items():
                            if feature_key in text_str and not data.get(field_name):
                                # Для булевых полей устанавливаем "有" (есть) или название
                                if field_name in ['abs', 'esp', 'tcs', 'bluetooth', 'usb', 'aux', 'navigation']:
                                    data[field_name] = '有'  # "有" означает наличие
                                else:
                                    data[field_name] = text_str
                                highlight_features.append(text_str)
                                logger.debug(f"Найдена особенность {field_name}: {text_str}")
                                break
                    
                    # Сохраняем все особенности в certification, если они есть
                    if highlight_features and not data.get('certification'):
                        data['certification'] = ', '.join(highlight_features)
            
            # Ищем информацию о гарантии и страховке
            if not data.get('warranty_info'):
                warranty_elem = soup.find('div', string=lambda text: text and any(
                    tag in str(text) for tag in ['质保', '保修', '原厂质保', '延保']
                ))
                if warranty_elem:
                    data['warranty_info'] = warranty_elem.get_text(strip=True)
            
            if not data.get('insurance_info'):
                insurance_elem = soup.find('div', string=lambda text: text and any(
                    tag in str(text) for tag in ['保险', '交强险', '商业险']
                ))
                if insurance_elem:
                    data['insurance_info'] = insurance_elem.get_text(strip=True)
                
        except Exception as e:
            logger.warning(f"Ошибка извлечения дополнительных характеристик: {e}")
    
    def _extract_images(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает изображения"""
        try:
            # Если уже есть изображения из JSON, не перезаписываем
            if data.get('image_gallery'):
                return
            
            images = []
            seen_urls = set()
            
            # Ищем все изображения с разными атрибутами
            img_tags = soup.find_all('img')
            for img in img_tags:
                # Пробуем разные атрибуты для URL изображения
                src = (img.get('src') or 
                      img.get('data-src') or 
                      img.get('data-original') or 
                      img.get('data-lazy-src') or
                      img.get('data-url'))
                
                if src:
                    # Обрабатываем относительные URL
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://m.che168.com' + src
                    
                    # Добавляем только полные HTTP URL и избегаем дубликатов
                    if src.startswith('http') and src not in seen_urls:
                        # Фильтруем маленькие иконки и логотипы
                        if not any(skip in src.lower() for skip in ['icon', 'logo', 'avatar', 'thumb']):
                            images.append(src)
                            seen_urls.add(src)
            
            # Также ищем в data-атрибутах div'ов (для lazy loading)
            img_divs = soup.find_all('div', {'data-src': True}) + \
                       soup.find_all('div', {'data-url': True})
            for div in img_divs:
                src = div.get('data-src') or div.get('data-url')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://m.che168.com' + src
                    if src.startswith('http') and src not in seen_urls:
                        if not any(skip in src.lower() for skip in ['icon', 'logo', 'avatar', 'thumb']):
                            images.append(src)
                            seen_urls.add(src)
            
            if images:
                data['image_gallery'] = ' '.join(images)
                data['image_count'] = len(images)
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения изображений: {e}")
    
    def _extract_description(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает описание"""
        try:
            # Вспомогательная функция для безопасной проверки класса
            def desc_class_check(x):
                if x is None:
                    return False
                if isinstance(x, list):
                    x_str = ' '.join(str(cls) for cls in x if cls)
                else:
                    x_str = str(x)
                return 'desc' in x_str.lower()
            
            # Ищем описание в различных элементах
            desc_elem = soup.find('div', class_=desc_class_check) or \
                       soup.find('p', class_=desc_class_check)
            
            if desc_elem:
                data['description'] = desc_elem.get_text(strip=True)
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения описания: {e}")





