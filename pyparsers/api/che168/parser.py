import os
import time
import random
import re
import logging
from typing import Optional, Tuple
from .models.car import Che168Car
from .models.response import Che168ApiResponse, Che168Data
from ..base_parser import BaseCarParser
from ..date_utils import normalize_first_registration_date
from ..dongchedi.parser import normalize_power_value

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
            import shutil
            temp_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            # Сохраняем путь для последующего удаления
            self._temp_dir = temp_dir

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
        # Инициализируем soup = None в начале функции для использования в except
        soup = None
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

                    result = Che168ApiResponse(
                        data=data,
                        message="Success",
                        status=200
                    )
                    
                    # Освобождаем память от soup
                    if soup:
                        soup.decompose()
                        del soup
                    del page_source
                    
                    return result
                finally:
                    # Дополнительная очистка на случай исключения
                    if 'soup' in locals() and soup is not None:
                        try:
                            soup.decompose()
                            del soup
                        except:
                            pass
                    if 'page_source' in locals():
                        try:
                            del page_source
                        except:
                            pass

            except Exception as e:
                logger.error(f"Ошибка при парсинге страницы {page}: {e}")
                try:
                    # Если успели распарсить хотя бы часть данных, вернем их
                    # Проверяем, что soup был создан и доступен
                    cars_elements = []
                    if soup is not None:
                        try:
                            cars_elements = soup.select('div.content.card-wrap ul.viewlist_ul li.cards-li')
                        except:
                            pass
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
                # Гарантируем закрытие драйвера и очистку ресурсов
                if self.driver:
                    try:
                        self.driver.quit()
                    except Exception:
                        pass
                    self.driver = None
                # Удаляем временную директорию
                if hasattr(self, '_temp_dir') and self._temp_dir:
                    try:
                        import os
                        import shutil
                        if os.path.exists(self._temp_dir):
                            shutil.rmtree(self._temp_dir, ignore_errors=True)
                    except Exception:
                        pass
                    delattr(self, '_temp_dir')
                # Освобождаем память от soup
                if 'soup' in locals():
                    try:
                        soup.decompose()
                        del soup
                    except Exception:
                        pass
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
        
        # Получаем car_id из атрибутов
        car_id = attrs.get('infoid')
        
        # Нормализуем ссылку: всегда используем формат как в details
        # https://m.che168.com/cardetail/index?infoid={car_id}
        if car_id and car_id.isdigit():
            link = f'https://m.che168.com/cardetail/index?infoid={car_id}'
        elif link:
            # Если есть ссылка, но нет car_id, пытаемся извлечь car_id из ссылки
            # Пытаемся извлечь car_id из ссылок вида /dealer/{dealer_id}/{car_id}.html
            match = re.search(r'/(\d+)\.html', link)
            if match:
                car_id_from_link = match.group(1)
                link = f'https://m.che168.com/cardetail/index?infoid={car_id_from_link}'
            elif link.startswith('/'):
                # Относительная ссылка - дополняем до полной, но всё равно нормализуем
                if car_id and car_id.isdigit():
                    link = f'https://m.che168.com/cardetail/index?infoid={car_id}'
                else:
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
        first_registration_time = None

        if unit:
            unit_text = unit.get_text(strip=True)
            # Пробуем разные разделители: ／, /, |
            parts = None
            for separator in ['／', '/', '|', ' ']:
                if separator in unit_text:
                    parts = unit_text.split(separator)
                    if len(parts) >= 2:
                        break
            
            if parts and len(parts) >= 2:
                # Первая часть - пробег
                milage = parts[0].replace('万公里', '').replace('公里', '').strip()
                # Вторая часть - дата регистрации
                regdate = parts[1].strip()
                # Третья часть (если есть) - город
                if len(parts) >= 3:
                    city = parts[2].strip()
                elif len(parts) == 2:
                    # Если только 2 части, вторая может быть городом, а дата может быть в другом месте
                    # Проверяем, похожа ли вторая часть на дату
                    if re.search(r'\d{4}', parts[1]):
                        regdate = parts[1].strip()
                    else:
                        city = parts[1].strip()

        # Также проверяем data-атрибуты элемента li для даты регистрации
        if not regdate:
            # Проверяем различные возможные атрибуты
            regdate = attrs.get('regdate') or attrs.get('reg_date') or attrs.get('registration_date') or attrs.get('first_registration_time')
            # Также проверяем год, если есть
            if not regdate and attrs.get('year'):
                year = attrs.get('year')
                if year and year.isdigit():
                    regdate = f"{year}-01-01"
        
        # Если regdate все еще нет, ищем в тексте элемента li
        if not regdate:
            li_text = li.get_text()
            # Ищем паттерны дат: "2011-03", "2011年", "2011年3月"
            date_match = re.search(r'(\d{4})[-年](\d{1,2})?', li_text)
            if date_match:
                year = date_match.group(1)
                month = date_match.group(2) if date_match.group(2) else '01'
                regdate = f"{year}-{month.zfill(2)}"

        # Нормализуем дату регистрации и извлекаем год
        if regdate:
            # Сначала очищаем regdate от лишнего текста (например, "2011年 / 11.5万公里" -> "2011年")
            # Ищем паттерн даты в начале строки
            date_match = re.search(r'(\d{4}[-年/]?\d{0,2}[-月/]?\d{0,2})', regdate)
            if date_match:
                clean_date = date_match.group(1)
            else:
                clean_date = regdate
            
            # Нормализуем дату регистрации в формат YYYY-MM-DD
            first_registration_time = normalize_first_registration_date(clean_date)
            if not first_registration_time:
                # Если нормализация не удалась, пытаемся извлечь только год
                year_match = re.search(r'(\d{4})', regdate)
                if year_match:
                    try:
                        year = int(year_match.group(1))
                        if 1900 <= year <= 2100:
                            first_registration_time = f"{year}-01-01"
                            logger.debug(f"Извлечен только год из '{regdate}': {first_registration_time}")
                    except (ValueError, TypeError):
                        pass
                if not first_registration_time:
                    logger.debug(f"Не удалось нормализовать дату регистрации: '{regdate}'")
            
            # Извлекаем год из даты регистрации
            if first_registration_time:
                try:
                    car_year = int(first_registration_time.split('-')[0])
                except (ValueError, IndexError):
                    car_year = None
        elif attrs.get('year'):
            # Если есть только год в атрибутах, создаем дату
            try:
                year = int(attrs.get('year'))
                if 1900 <= year <= 2100:
                    car_year = year
                    first_registration_time = f"{year}-01-01"
            except (ValueError, TypeError):
                pass

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
        # При парсинге списка машин is_available по умолчанию True
        # Детальная проверка доступности выполняется в fetch_car_detail
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
            'is_available': True,  # По умолчанию True при парсинге списка
            'first_registration_time': first_registration_time,
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
        import shutil
        import os
        temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        driver = None
        soup = None
        page_source = None
        soup_created = False
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(10)
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
            soup_created = True
            
            # Инициализируем car_info внутри try, чтобы можно было использовать после finally
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
                "source": "che168",
                "first_registration_time": None,
                "power": None
            }
            
            # Парсим данные из soup (весь парсинг внутри try)
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
                                                # Если есть год, но нет даты, создаем дату из года
                                                if not car_info.get('first_registration_time') and car_data['year']:
                                                    try:
                                                        year = int(car_data['year'])
                                                        if 1900 <= year <= 2100:
                                                            car_info['first_registration_time'] = f"{year}-01-01"
                                                    except (ValueError, TypeError):
                                                        pass
                                            if 'mileage' in car_data:
                                                car_info['car_mileage'] = car_data['mileage']
                                            # Ищем дату регистрации в различных полях
                                            if 'first_registration_time' in car_data:
                                                car_info['first_registration_time'] = normalize_first_registration_date(car_data['first_registration_time'])
                                            elif 'registration_date' in car_data:
                                                car_info['first_registration_time'] = normalize_first_registration_date(car_data['registration_date'])
                                            elif 'regdate' in car_data:
                                                car_info['first_registration_time'] = normalize_first_registration_date(car_data['regdate'])
                                            elif 'reg_date' in car_data:
                                                car_info['first_registration_time'] = normalize_first_registration_date(car_data['reg_date'])
                                            elif 'first_reg_date' in car_data:
                                                car_info['first_registration_time'] = normalize_first_registration_date(car_data['first_reg_date'])
                                            # Также проверяем другие возможные поля с датой
                                            for date_field in ['register_date', 'register_time', 'onboard_date', 'onboard_time']:
                                                if date_field in car_data and not car_info.get('first_registration_time'):
                                                    car_info['first_registration_time'] = normalize_first_registration_date(car_data[date_field])
                                                    if car_info['first_registration_time']:
                                                        break
                                            if 'brand_name' in car_data:
                                                car_info['brand_name'] = car_data['brand_name']
                                            if 'series_name' in car_data:
                                                car_info['series_name'] = car_data['series_name']
                                            if 'brand_id' in car_data:
                                                car_info['brand_id'] = car_data['brand_id']
                                            if 'series_id' in car_data:
                                                car_info['series_id'] = car_data['series_id']
                                            # Парсинг мощности из JSON
                                            # Ищем в engine_info (формат: "2.0T 252马力 L4")
                                            if 'engine_info' in car_data:
                                                engine_text = str(car_data['engine_info'])
                                                logger.debug(f"che168: Найден engine_info: {engine_text}")
                                                power_match = re.search(r'(\d+)\s*马力', engine_text)
                                                if power_match:
                                                    raw_power = power_match.group(1) + '马力'
                                                    normalized_power = normalize_power_value(raw_power)
                                                    if normalized_power:
                                                        car_info['power'] = normalized_power
                                                        logger.info(f"che168: Найдена мощность из engine_info: {raw_power} -> {normalized_power} л.с.")
                                                else:
                                                    logger.debug(f"che168: В engine_info '{engine_text}' не найдено паттерна мощности")
                                            else:
                                                logger.debug(f"che168: Поле engine_info не найдено в car_data. Доступные поля: {list(car_data.keys())}")
                                            # Ищем прямое поле power
                                            if 'power' in car_data and not car_info.get('power'):
                                                raw_power = str(car_data['power'])
                                                logger.debug(f"che168: Найдено поле power: {raw_power}")
                                                normalized_power = normalize_power_value(raw_power)
                                                if normalized_power:
                                                    car_info['power'] = normalized_power
                                                    logger.info(f"che168: Найдена мощность из power: {raw_power} -> {normalized_power} л.с.")
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
                                        if 'sku_id' in sku_detail:
                                            car_info['car_id'] = sku_detail['sku_id']
                                            car_info['sku_id'] = sku_detail['sku_id']
                    except Exception as e:
                        continue
            year_input = soup.find('input', {'id': 'hiddealerYear'})
            if year_input and year_input.get('value'):
                try:
                    year_value = int(year_input.get('value'))
                    car_info['car_year'] = year_value
                    # Если нет first_registration_time, создаем из года
                    if not car_info.get('first_registration_time'):
                        car_info['first_registration_time'] = f"{year_value}-01-01"
                except (ValueError, TypeError):
                    pass
            
            # Парсим first_registration_time из HTML
            if not car_info.get('first_registration_time'):
                try:
                    # 1. Ищем секцию "档案" и "上牌时间"
                    archive_section = soup.find('div', string=lambda text: text and '档案' in str(text))
                    if not archive_section:
                        archive_section = soup.find('div', class_=lambda x: x and 'archive' in str(x).lower())
                    
                    if archive_section:
                        archive_parent = archive_section.find_parent('div')
                        if archive_parent:
                            # Ищем "上牌时间" (дата регистрации)
                            registration_elem = archive_parent.find('div', string=lambda text: text and '上牌时间' in str(text))
                            if not registration_elem:
                                registration_elem = archive_parent.find('span', string=lambda text: text and '上牌时间' in str(text))
                            
                            if registration_elem:
                                # Ищем значение даты
                                parent = registration_elem.find_parent('div')
                                if parent:
                                    date_text = parent.get_text()
                                    date_pattern = re.compile(r'(\d{4})[^\d]{0,3}(\d{1,2})?[^\d]{0,3}(\d{1,2})?')
                                    match = date_pattern.search(date_text)
                                    if match:
                                        normalized_date = normalize_first_registration_date(match.group(0))
                                        if normalized_date:
                                            car_info['first_registration_time'] = normalized_date
                                            # Если нет car_year, извлекаем из даты
                                            if not car_info.get('car_year'):
                                                try:
                                                    car_info['car_year'] = int(normalized_date.split('-')[0])
                                                except (ValueError, IndexError):
                                                    pass
                    
                    # 2. Если не нашли, ищем паттерны дат в тексте HTML (форматы: "2011-03", "2011年", "2011-03-15")
                    if not car_info.get('first_registration_time'):
                        page_text = soup.get_text()
                        # Ищем паттерны: YYYY-MM, YYYY年, YYYY-MM-DD
                        date_patterns = [
                            r'(\d{4})-(\d{1,2})(?:-(\d{1,2}))?',  # 2011-03 или 2011-03-15
                            r'(\d{4})年(?:(\d{1,2})月)?',  # 2011年 или 2011年3月
                        ]
                        for pattern in date_patterns:
                            matches = re.finditer(pattern, page_text)
                            for match in matches:
                                # Проверяем, что это не просто случайное число (например, не цена)
                                context_start = max(0, match.start() - 20)
                                context_end = min(len(page_text), match.end() + 20)
                                context = page_text[context_start:context_end].lower()
                                # Пропускаем, если это похоже на цену или другой контекст
                                if any(word in context for word in ['万', '元', 'price', '￥', '¥']):
                                    continue
                                # Пропускаем, если это год выпуска модели (например, "2010款")
                                if '款' in context:
                                    continue
                                
                                # Пытаемся нормализовать найденную дату
                                date_str = match.group(0)
                                normalized_date = normalize_first_registration_date(date_str)
                                if normalized_date:
                                    # Проверяем, что год разумный
                                    year = int(normalized_date.split('-')[0])
                                    if 1900 <= year <= 2100:
                                        car_info['first_registration_time'] = normalized_date
                                        if not car_info.get('car_year'):
                                            car_info['car_year'] = year
                                        logger.debug(f"Найдена дата регистрации в тексте: {date_str} -> {normalized_date}")
                                        break
                            if car_info.get('first_registration_time'):
                                break
                except Exception as e:
                    logger.debug(f"Ошибка при парсинге first_registration_time из HTML: {e}")
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
                'span.address',
                '.address',
                '[class*="address"]',
                '.location',
                '[class*="location"]'
            ]
            for selector in address_selectors:
                address_elem = soup.select_one(selector)
                if address_elem:
                    address_text = address_elem.get_text().strip()
                    if address_text and len(address_text) < 200:
                        car_info['car_source_city_name'] = address_text
                        break
            # Парсим brand_name и series_name из title
            if car_info.get('title') and not car_info.get('brand_name'):
                title = car_info['title']
                import re
                title_parts = re.split(r'[\s\-_]+', title)
                brand_keywords = ['奔驰', '宝马', '奥迪', '大众', '丰田', '本田', '日产', '现代', '起亚', '福特', '雪佛兰', '别克', '凯迪拉克', '林肯', '雷克萨斯', '英菲尼迪', '讴歌', '沃尔沃', '路虎', '捷豹', '保时捷', '玛莎拉蒂', '法拉利', '兰博基尼', '宾利', '劳斯莱斯', 'MINI', 'Smart', 'DS', '标致', '雪铁龙', '雷诺', '菲亚特', '阿尔法·罗密欧', 'Jeep', '道奇', 'RAM', 'GMC', '特斯拉', '比亚迪', '吉利', '长城', '奇瑞', '长安', '上汽', '一汽', '东风', '广汽', '北汽', '江淮', '众泰', '海马', '力帆', '华晨', '东南', '陆风', '猎豹', '野马', '金杯', '五菱', '宝骏', '启辰', '理念', '思铭', '开瑞', '威麟', '瑞麒', '观致', '纳智捷', '华泰', '永源', '青年', '黄海', '中兴', '双环', '中顺', '新凯', '天马', '大迪', '新大地', '奥克斯', '万丰', '通田', '美鹿', '飞碟', '新雅途', '跃进', '南汽', '昌河', '哈飞', '松花江', '昌河铃木', '哈飞赛豹', '哈飞路宝', '哈飞民意', '哈飞中意', '松花江中意', '松花江民意', '松花江路宝', '松花江赛豹']
                for part in title_parts:
                    for keyword in brand_keywords:
                        if keyword in part:
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
            
            # Парсинг мощности из HTML (если не нашли в JSON)
            if not car_info.get('power'):
                logger.debug("che168: Мощность не найдена в JSON, ищем в HTML")
                try:
                    # Ищем метки мощности в HTML
                    power_labels = ['最大马力', '最大马力(Ps)', '最大功率', '最大功率(kW)', '功率', '马力']
                    for label in power_labels:
                        # Ищем элементы с меткой
                        label_elem = soup.find(string=lambda text: text and label in str(text))
                        if label_elem:
                            # Ищем родительский элемент
                            parent = label_elem.find_parent()
                            if parent:
                                # Ищем значение в соседних элементах
                                parent_text = parent.get_text()
                                # Ищем число с единицами измерения
                                power_patterns = [
                                    r'(\d+)\s*马力',
                                    r'(\d+)\s*Ps',
                                    r'(\d+)\s*kW',
                                    r'(\d+)\s*功率',
                                    r'最大马力[^0-9]*(\d+)',
                                    r'最大功率[^0-9]*(\d+)',
                                ]
                                for pattern in power_patterns:
                                    match = re.search(pattern, parent_text)
                                    if match:
                                        raw_power = match.group(1)
                                        # Если нашли kW, конвертируем
                                        if 'kW' in parent_text or '功率' in label:
                                            raw_power = raw_power + 'kW'
                                        else:
                                            raw_power = raw_power + '马力'
                                        normalized_power = normalize_power_value(raw_power)
                                        if normalized_power:
                                            car_info['power'] = normalized_power
                                            logger.info(f"che168: Найдена мощность из HTML ({label}): {raw_power} -> {normalized_power} л.с.")
                                            break
                                if car_info.get('power'):
                                    break
                    
                    # Если не нашли через метки, ищем в тексте страницы
                    if not car_info.get('power'):
                        page_text = soup.get_text()
                        # Ищем паттерны мощности в тексте
                        power_text_patterns = [
                            r'(\d+)\s*马力',
                            r'最大马力[^0-9]*(\d+)',
                            r'(\d+)\s*Ps',
                        ]
                        for pattern in power_text_patterns:
                            match = re.search(pattern, page_text)
                            if match:
                                raw_power = match.group(1) + '马力'
                                normalized_power = normalize_power_value(raw_power)
                                if normalized_power:
                                    car_info['power'] = normalized_power
                                    logger.info(f"che168: Найдена мощность из текста страницы: {raw_power} -> {normalized_power} л.с.")
                                    break
                except Exception as e:
                    logger.debug(f"che168: Ошибка при парсинге мощности из HTML: {e}")
            else:
                logger.info(f"che168: Мощность уже найдена: {car_info.get('power')} л.с.")
            
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
        except Exception as e:
            # Логируем ошибку
            logger.error(f"Ошибка при парсинге страницы: {e}")
            soup_created = False
            car_info = None
            is_available = False
        finally:
            # Гарантируем закрытие драйвера
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = None
            # Удаляем временную директорию
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            # Освобождаем память от page_source и soup
            if page_source:
                del page_source
            if soup:
                soup.decompose()
                del soup
        
        # Проверяем, был ли создан soup и распарсены данные
        if not soup_created or car_info is None:
            return None, {"is_available": False, "error": "Не удалось загрузить или распарсить страницу", "status": 500}
        
        # Создаем объект Che168Car и возвращаем результат
        try:
            car_obj = Che168Car(**{k: v for k, v in car_info.items() if k in Che168Car.__fields__})
        except Exception as e:
            return None, {"is_available": False, "error": str(e), "status": 500}
        
        return car_obj, {"is_available": is_available, "status": 200, "link": clean_url}
