import os
import time
import random
import logging
from typing import Optional, Tuple
from .models.car import Che168Car
from .models.response import Che168ApiResponse, Che168Data
from ..base_parser import BaseCarParser

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium не установлен. Установите: pip install selenium")

class Che168Parser(BaseCarParser):
    """Selenium парсер для сайта Che168"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None

    def _build_url(self, page: int = 1) -> str:
        """Строит URL с номером страницы для che168"""
        # Базовая ссылка: https://www.che168.com/china/a0_0msdgscncgpi1lto8csp{pagenumber}exx0/
        logger.info(f"Формирование URL для страницы {page}")
        return f'https://www.che168.com/china/a0_0msdgscncgpi1lto8csp{page}exx0/?pvareaid=102179'

    def _setup_driver(self):
        """Настройка Chrome драйвера"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium не установлен")

        chrome_options = Options()

        if self.headless:
            # Use new headless for modern Chromium
            chrome_options.add_argument("--headless=new")

        # Настройки для обхода обнаружения
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # ОТКЛЮЧАЕМ ЗАГРУЗКУ ИЗОБРАЖЕНИЙ И МЕДИА (значительно ускоряет)
        prefs = {
            "profile.managed_default_content_settings.images": 2,  # Блокировать изображения
            "profile.managed_default_content_settings.media_stream": 2,  # Блокировать медиа
            "profile.managed_default_content_settings.plugins": 2,  # Блокировать плагины
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # ДОПОЛНИТЕЛЬНЫЕ ОПТИМИЗАЦИИ
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")

        # Случайное разрешение экрана
        resolutions = ["1920x1080", "1366x768", "1440x900", "1536x864"]
        chrome_options.add_argument(f"--window-size={random.choice(resolutions)}")

        # User-Agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

        try:
            # Respect CHROME_BIN and CHROMEDRIVER_PATH if provided
            import os
            chrome_bin = os.environ.get("CHROME_BIN")
            if chrome_bin:
                chrome_options.binary_location = chrome_bin

            # Добавляем уникальный user-data-dir для избежания конфликтов
            import tempfile
            temp_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")

            driver_path = os.environ.get("CHROMEDRIVER_PATH")
            if driver_path:
                self.driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)

            # Скрываем признаки автоматизации
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Устанавливаем случайные размеры окна
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            self.driver.set_window_size(width, height)

        except WebDriverException as e:
            print(f"Ошибка создания драйвера: {e}")
            print("Убедитесь, что Chrome установлен и chromedriver доступен")
            raise

    def _wait_for_page_load(self, timeout: int = 20):  # Уменьшаем timeout с 30 до 20
        """Ожидание загрузки страницы"""
        if self.driver is None:
            return False

        try:
            # Ждем появления элементов с машинами
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.content.card-wrap ul.viewlist_ul li.cards-li"))
            )
            return True
        except TimeoutException:
            return False

    def _scroll_page(self):
        """Прокрутка страницы для загрузки всего контента"""
        if self.driver is None:
            return

        # УМЕНЬШАЕМ КОЛИЧЕСТВО ПРОКРУТОК И ЗАДЕРЖЕК
        for i in range(2):  # Было 3, стало 2
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(0.5, 1))  # Было 1-2, стало 0.5-1

            # Прокручиваем обратно
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.3, 0.5))  # Было 0.5-1, стало 0.3-0.5

    def fetch_cars(self, source: Optional[str] = 'url') -> Che168ApiResponse:
        """
        Selenium парсер с полной имитацией браузера
        По умолчанию загружает первую страницу
        """
        return self.fetch_cars_by_page(1, source)

    def fetch_cars_by_page(self, page: int, source: Optional[str] = 'url') -> Che168ApiResponse:
        """
        Selenium парсер для конкретной страницы

        Args:
            page: Номер страницы (начиная с 1)
            source: Источник данных ('url' или путь к файлу)
        """
        # Ограничение: максимум 100 страниц
        if page > 100:
            return Che168ApiResponse(
                data=Che168Data(has_more=False, search_sh_sku_info_list=[], total=0),
                message=f"Страница {page} не найдена",
                status=404
            )
        if source == 'url':
            try:
                self._setup_driver()

                if self.driver is None:
                    return Che168ApiResponse(
                        data=Che168Data(has_more=False, search_sh_sku_info_list=[], total=0),
                        message="Не удалось создать драйвер",
                        status=500
                    )

                # Строим URL с номером страницы
                url = self._build_url(page)
                logger.info(f"Загружаем страницу {page}: {url}")

                self.driver.get(url)

                # УМЕНЬШАЕМ ЗАДЕРЖКУ ДЛЯ УСКОРЕНИЯ
                time.sleep(random.uniform(1, 2))  # Было 2-4, стало 1-2

                # Ожидаем загрузки страницы
                if not self._wait_for_page_load():
                    return Che168ApiResponse(
                        data=Che168Data(has_more=False, search_sh_sku_info_list=[], total=0),
                        message=f"Страница {page} не найдена",
                        status=404
                    )

                # Прокручиваем страницу
                self._scroll_page()

                # Получаем HTML после полной загрузки
                page_source = self.driver.page_source

                # Парсим HTML (используем lxml для ускорения, fallback на html.parser)
                from bs4 import BeautifulSoup
                try:
                    soup = BeautifulSoup(page_source, 'lxml')
                except:
                    soup = BeautifulSoup(page_source, 'html.parser')

                cars_elements = soup.select('div.content.card-wrap ul.viewlist_ul li.cards-li')
                cars = [self._parse_li_to_car(li) for li in cars_elements]

                # Фильтруем рекламные блоки (car_id == None)
                cars = [car for car in cars if car.car_id is not None]

                # Если данных нет или список пуст, считаем что страницы не существует
                if not cars:
                    return Che168ApiResponse(
                        data=Che168Data(has_more=False, search_sh_sku_info_list=[], total=0),
                        message=f"Страница {page} не найдена",
                        status=404
                    )

                # МИНИМИЗИРУЕМ ЛОГИ ДЛЯ УСКОРЕНИЯ
                logger.info(f"Страница {page}: найдено {len(cars)} автомобилей")

                # Проверяем, есть ли еще страницы (ищем пагинацию)
                try:
                    has_more = self._check_has_more_pages(soup)
                except Exception as e:
                    logger.warning(f"Ошибка при анализе пагинации: {e}")
                    has_more = False

                data = Che168Data(
                    has_more=has_more,
                    search_sh_sku_info_list=cars,
                    total=len(cars)
                )

                return Che168ApiResponse(
                    data=data,
                    message="Success",
                    status=200
                )

            except Exception as e:
                logger.error(f"Ошибка при парсинге страницы {page}: {e}")
                try:
                    # Если успели распарсить хотя бы часть данных, вернем их
                    cars_elements = soup.select('div.content.card-wrap ul.viewlist_ul li.cards-li') if 'soup' in locals() else []
                    cars = [self._parse_li_to_car(li) for li in cars_elements] if cars_elements else []
                    cars = [car for car in cars if getattr(car, 'car_id', None) is not None]
                    return Che168ApiResponse(
                        data=Che168Data(has_more=False, search_sh_sku_info_list=cars, total=len(cars)),
                        message=f"Partial success on page {page}: returned {len(cars)} cars; error: {e}",
                        status=200 if cars else 404
                    )
                except Exception as inner:
                    logger.error(f"Ошибка при формировании частичного ответа: {inner}")
                    return Che168ApiResponse(
                        data=Che168Data(has_more=False, search_sh_sku_info_list=[], total=0),
                        message=f"Страница {page} не найдена",
                        status=404
                    )
            finally:
                if self.driver:
                    self.driver.quit()
        else:
            # Для локального файла используем обычный парсинг
            try:
                if source and source not in ('url',):
                    with open(source, 'r', encoding='utf-8') as f:
                        from bs4 import BeautifulSoup
                        try:
                            soup = BeautifulSoup(f, 'lxml')
                        except:
                            soup = BeautifulSoup(f, 'html.parser')
                else:
                    return Che168ApiResponse(
                        data=Che168Data(has_more=False, search_sh_sku_info_list=[], total=0),
                        message="Не указан файл для парсинга",
                        status=400
                    )

                cars_elements = soup.select('div.content.card-wrap ul.viewlist_ul li.cards-li')
                cars = []
                for li in cars_elements:
                    car = self._parse_li_to_car(li)
                    if car.car_id is not None:
                        cars.append(car)

                # Если данных нет или список пуст, считаем что страницы не существует
                if not cars:
                    return Che168ApiResponse(
                        data=Che168Data(has_more=False, search_sh_sku_info_list=[], total=0),
                        message=f"Страница {page} не найдена",
                        status=404
                    )

                data = Che168Data(
                    has_more=False,
                    search_sh_sku_info_list=cars,
                    total=len(cars)
                )

                return Che168ApiResponse(
                    data=data,
                    message="Success",
                    status=200
                )
            except Exception as e:
                return Che168ApiResponse(
                    data=Che168Data(has_more=False, search_sh_sku_info_list=[], total=0),
                    message=f"Страница {page} не найдена",
                    status=404
                )

    def _check_has_more_pages(self, soup) -> bool:
        """Проверяет, есть ли еще страницы"""
        try:
            # Ищем пагинацию
            pagination = soup.select_one('div.pagination')
            if pagination:
                # Ищем кнопку "следующая страница"
                next_button = pagination.select_one('a.next')
                if next_button and not 'disabled' in next_button.get('class', []):
                    # Проверяем, что это действительно кнопка "следующая страница", а не другой элемент
                    if next_button.get_text(strip=True) in ['下一页', '>', 'Next', '下一頁']:
                        logger.info(f"Найдена кнопка следующей страницы: {next_button.get_text(strip=True)}")
                        return True

                # Проверяем наличие других индикаторов пагинации
                page_links = pagination.select('a')
                for link in page_links:
                    # Если есть ссылка на страницу с номером больше текущей, значит есть еще страницы
                    link_text = link.get_text(strip=True)
                    if link_text.isdigit() and int(link_text) > 1:
                        logger.info(f"Найдена ссылка на страницу {link_text}")
                        return True

            # Если не нашли явных признаков пагинации, проверяем альтернативные элементы
            # Например, может быть кнопка "загрузить еще" или другие элементы пагинации
            load_more = soup.select_one('[class*="load-more"], [class*="loadMore"], .more, .next-page')
            if load_more:
                logger.info(f"Найдена кнопка 'загрузить еще': {load_more.get_text(strip=True)}")
                return True

            # Если не нашли никаких признаков пагинации, считаем что это последняя страница
            logger.info("Не найдено признаков наличия следующих страниц")
            return False

        except Exception as e:
            logger.warning(f"Ошибка при проверке пагинации: {e}")
            return False

    def _parse_li_to_car(self, li) -> Che168Car:
        """Приватный метод для парсинга элемента li в объект Che168Car"""
        attrs = li.attrs.copy()

        # Извлекаем основную информацию
        a = li.select_one('a.carinfo')
        link = a['href'] if a and a.has_attr('href') else None
        if link and link.startswith('/'):
            link = 'https://www.che168.com' + link

        # Извлекаем изображение
        img = li.select_one('img')
        image = None
        if img:
            image = img.get('src2') or img.get('src')
            if image and image.startswith('//'):
                image = 'https:' + image

        # Извлекаем заголовок
        h4 = li.select_one('h4.card-name')
        title = h4.get_text(strip=True) if h4 else attrs.get('carname')

        # Извлекаем цену
        price_tag = li.select_one('span.pirce em')
        sh_price = price_tag.get_text(strip=True) if price_tag else attrs.get('price')

        # Извлекаем информацию о пробеге, дате регистрации и городе
        unit = li.select_one('p.cards-unit')
        milage, regdate, city, car_year = None, None, None, None

        if unit:
            unit_text = unit.get_text(strip=True)
            parts = unit_text.split('／')
            if len(parts) >= 3:
                milage = parts[0].replace('万公里', '').strip()
                regdate = parts[1].strip()
                city = parts[2].strip()

        # Извлекаем год из даты регистрации
        if regdate:
            try:
                car_year = int(regdate.split('-')[0])
            except (ValueError, IndexError):
                car_year = None

        # Извлекаем теги
        tags = []
        tags_box = li.select_one('div.cards-tags-box')
        if tags_box:
            for tag in tags_box.select('i, span, em'):
                tag_text = tag.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)

        # Извлекаем название модели из заголовка
        car_name = title
        brand_name = None
        series_name = None

        if title:
            # Пытаемся извлечь марку и модель из заголовка
            title_parts = title.split()
            if len(title_parts) >= 2:
                brand_name = title_parts[0]  # Первое слово - обычно марка
                series_name = ' '.join(title_parts[1:3]) if len(title_parts) >= 3 else title_parts[1]

        # Формируем данные для Che168Car
        data = {
            'title': title,
            'sh_price': sh_price,
            'image': image,
            'car_mileage': milage,
            'car_year': car_year,
            'car_source_city_name': city,
            'link': link,
            'car_name': car_name,
            'brand_name': brand_name,
            'series_name': series_name,
            'brand_id': int(attrs.get('brandid')) if attrs.get('brandid') and attrs.get('brandid').isdigit() else None,
            'series_id': int(attrs.get('seriesid')) if attrs.get('seriesid') and attrs.get('seriesid').isdigit() else None,
            'shop_id': attrs.get('dealerid'),
            'car_id': int(attrs.get('infoid')) if attrs.get('infoid') and attrs.get('infoid').isdigit() else None,
            'tags_v2': ', '.join(tags) if tags else None,
        }

        return Che168Car(**data)

    def fetch_car_detail(self, car_url: str):
        """
        Парсит детальную информацию о машине по car_url через selenium/beautifulsoup.
        Возвращает (Che168Car | None, meta: dict)
        """
        import time
        import random
        import json
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from selenium.common.exceptions import TimeoutException, WebDriverException
        from bs4 import BeautifulSoup
        clean_url = car_url.split('?')[0].split('#')[0]
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.media_stream": 2,
            "profile.managed_default_content_settings.plugins": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        # Добавляем уникальный user-data-dir для избежания конфликтов
        import tempfile
        temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        driver = None
        soup = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.get(clean_url)
            time.sleep(random.uniform(2, 3))
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                pass
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
        finally:
            if driver:
                driver.quit()
        if soup is None:
            return None, {"is_available": False, "error": "Не удалось загрузить страницу", "status": 500}
        car_info = {
            "title": None,
            "sh_price": None,
            "image": None,
            "link": clean_url,
            "car_name": None,
            "car_year": None,
            "car_mileage": None,
            "car_source_city_name": None,
            "brand_name": None,
            "series_name": None,
            "brand_id": None,
            "series_id": None,
            "shop_id": None,
            "car_id": None,
            "tags_v2": None,
            "sku_id": None,
            "sort_number": 1,
            "source": "che168"
        }
        title_tag = soup.find('title')
        if title_tag:
            car_info['title'] = title_tag.get_text().strip()
            car_info['car_name'] = title_tag.get_text().strip()
        price_selectors = [
            'b.num-price',
            '.num-price',
            '[class*="price"]',
            '.price',
            'span[class*="price"]',
            'p[class*="price"]',
            '.font-zmQZz5CrbrbHudeQ',
            '[class*="font-zmQZz5CrbrbHudeQ"]'
        ]
        for selector in price_selectors:
            price_elements = soup.select(selector)
            if price_elements:
                for elem in price_elements:
                    price_text = elem.get_text().strip()
                    if any(char in price_text for char in ['万', '元', '¥', '￥', '.']):
                        car_info['sh_price'] = price_text
                        break
                if car_info['sh_price']:
                    break
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description and hasattr(meta_description, 'get'):
            content = meta_description.get('content', '')
            if content:
                car_info['tags_v2'] = content
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
                                    if 'car_info' in sku_detail:
                                        car_data = sku_detail['car_info']
                                        if 'car_name' in car_data:
                                            car_info['car_name'] = car_data['car_name']
                                        if 'car_price' in car_data:
                                            car_info['sh_price'] = car_data['car_price']
                                        if 'year' in car_data:
                                            car_info['car_year'] = car_data['year']
                                        if 'mileage' in car_data:
                                            car_info['car_mileage'] = car_data['mileage']
                                        if 'brand_name' in car_data:
                                            car_info['brand_name'] = car_data['brand_name']
                                        if 'series_name' in car_data:
                                            car_info['series_name'] = car_data['series_name']
                                        if 'brand_id' in car_data:
                                            car_info['brand_id'] = car_data['brand_id']
                                        if 'series_id' in car_data:
                                            car_info['series_id'] = car_data['series_id']
                                    if 'shop_info' in sku_detail:
                                        shop_data = sku_detail['shop_info']
                                        if 'shop_name' in shop_data:
                                            car_info['car_source_city_name'] = shop_data['shop_name']
                                        if 'shop_id' in shop_data:
                                            car_info['shop_id'] = shop_data['shop_id']
                                        if 'shop_address' in shop_data:
                                            car_info['car_source_city_name'] = shop_data['shop_address']
                                    if 'head_images' in sku_detail and sku_detail['head_images']:
                                        car_info['image'] = sku_detail['head_images'][0]
                                    if 'sh_car_desc' in sku_detail:
                                        car_info['tags_v2'] = sku_detail['sh_car_desc']
                                    if 'sku_id' in sku_detail:
                                        car_info['car_id'] = sku_detail['sku_id']
                                        car_info['sku_id'] = sku_detail['sku_id']
                except Exception as e:
                    continue
        year_input = soup.find('input', {'id': 'hiddealerYear'})
        if year_input and year_input.get('value'):
            try:
                car_info['car_year'] = int(year_input.get('value'))
            except (ValueError, TypeError):
                pass
        mileage_input = soup.find('input', {'id': 'car_mileage'})
        if mileage_input and mileage_input.get('value'):
            try:
                mileage_value = mileage_input.get('value')
                car_info['car_mileage'] = f"{mileage_value}万公里"
            except (ValueError, TypeError):
                pass
        brand_input = soup.find('input', {'id': 'car_brandid'})
        if brand_input and brand_input.get('value'):
            try:
                car_info['brand_id'] = int(brand_input.get('value'))
            except (ValueError, TypeError):
                pass
        series_input = soup.find('input', {'id': 'car_seriesid'})
        if series_input and series_input.get('value'):
            try:
                car_info['series_id'] = int(series_input.get('value'))
            except (ValueError, TypeError):
                pass
        dealer_input = soup.find('input', {'id': 'car_dealerid'})
        if dealer_input and dealer_input.get('value'):
            car_info['shop_id'] = dealer_input.get('value')
        else:
            url_parts = clean_url.split('/')
            if len(url_parts) >= 4:
                car_info['shop_id'] = url_parts[3]
        img_elements = soup.find_all('img')
        for img in img_elements:
            src = img.get('src') or img.get('data-src')
            if src and ('car' in src.lower() or 'auto' in src.lower() or '2sc' in src):
                if src.startswith('//'):
                    src = 'https:' + src
                car_info['image'] = src
                break
        dealer_selectors = [
            'span.merchant-name',
            '.merchant-name',
            '[class*="merchant"]',
            '.dealer-name',
            '[class*="dealer"]'
        ]
        for selector in dealer_selectors:
            dealer_elem = soup.select_one(selector)
            if dealer_elem:
                dealer_text = dealer_elem.get_text().strip()
                if dealer_text and len(dealer_text) < 100:
                    car_info['car_source_city_name'] = dealer_text
                    break
        address_selectors = [
            'div.merchant-address',
            '.merchant-address',
            '[class*="address"]',
            '.dealer-address'
        ]
        for selector in address_selectors:
            address_elem = soup.select_one(selector)
            if address_elem:
                address_text = address_elem.get_text().strip()
                if address_text and len(address_text) < 200:
                    car_info['car_source_city_name'] = address_text
                    break
        car_id = clean_url.split('/')[-1].replace('.html', '')
        car_info['car_id'] = car_id
        car_info['sku_id'] = car_id
        if car_info['title']:
            title_parts = car_info['title'].split()
            if len(title_parts) >= 2:
                for part in title_parts[:3]:
                    if len(part) > 1 and not any(char in part for char in ['【', '】', '年', '款', 'km']):
                        car_info['brand_name'] = part
                        break
                if car_info['brand_name']:
                    brand_index = -1
                    for i, part in enumerate(title_parts):
                        if part == car_info['brand_name']:
                            brand_index = i
                            break
                    if brand_index >= 0 and brand_index + 1 < len(title_parts):
                        series_part = title_parts[brand_index + 1]
                        if len(series_part) > 1 and not any(char in series_part for char in ['【', '】', '年', '款', 'km']):
                            car_info['series_name'] = series_part
        page_text = soup.get_text()
        available_indicators = [
            "我要询价", "查看电话", "询价", "联系", "电话", "咨询",
            "askprice", "phone", "contact", "inquiry"
        ]
        unavailable_indicators = [
            "已售", "售出", "已卖出", "下架", "已下架", "已成交",
            "sold", "sale", "unavailable", "not available"
        ]
        is_available = False
        if any(indicator in page_text for indicator in available_indicators):
            is_available = True
        elif any(indicator in page_text for indicator in unavailable_indicators):
            is_available = False
        else:
            is_available = car_info['sh_price'] is not None and car_info['sh_price'] != ''
        car_info['is_available'] = is_available
        try:
            car_obj = Che168Car(**{k: v for k, v in car_info.items() if k in Che168Car.__fields__})
        except Exception as e:
            return None, {"is_available": False, "error": str(e), "status": 500}
        return car_obj, {"is_available": is_available, "status": 200, "link": clean_url}
