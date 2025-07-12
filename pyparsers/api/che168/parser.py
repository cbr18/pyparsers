import os
import time
import random
import logging
from typing import Optional
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
        return f'https://www.che168.com/china/a0_0msdgscncgpi1lto8csp{page}exx0/?pvareaid=102179#currengpostion'
        
    def _setup_driver(self):
        """Настройка Chrome драйвера"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium не установлен")
            
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
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
                has_more = self._check_has_more_pages(soup)
                
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
                    return True
            
            # Альтернативный способ - проверяем количество элементов
            cars_elements = soup.select('div.content.card-wrap ul.viewlist_ul li.cards-li')
            return len(cars_elements) > 0  # Если есть машины, возможно есть еще страницы
            
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