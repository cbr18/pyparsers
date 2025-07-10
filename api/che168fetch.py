import os
import time
import random
import logging
from typing import Optional
from models.car import Car
from models.response import ApiResponse, Data
from .base_parser import BaseCarParser

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

CHE168_URL = 'https://www.che168.com/china/a0_0msdgscncgpi1lto8csp3exx0/?pvareaid=102179#currengpostion'

class Che168Parser(BaseCarParser):
    """Selenium парсер для сайта Che168"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        
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
    
    def _wait_for_page_load(self, timeout: int = 30):
        """Ожидание загрузки страницы"""
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
        # Прокручиваем страницу несколько раз
        for i in range(3):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 2))
            
            # Прокручиваем обратно
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.5, 1))
    
    def fetch_cars(self, source: Optional[str] = 'url') -> ApiResponse:
        """
        Selenium парсер с полной имитацией браузера
        """
        if source == 'url':
            try:
                self._setup_driver()
                
                self.driver.get(CHE168_URL)
                
                # Случайная задержка для имитации человеческого поведения
                time.sleep(random.uniform(2, 4))
                
                # Ожидаем загрузки страницы
                if not self._wait_for_page_load():
                    return ApiResponse(
                        data=Data(has_more=False, search_sh_sku_info_list=[], total=0),
                        message="Страница не загрузилась",
                        status=404
                    )
                
                # Прокручиваем страницу
                self._scroll_page()
                
                # Получаем HTML после полной загрузки
                page_source = self.driver.page_source
                
                # Парсим HTML
                from bs4 import BeautifulSoup
                import pprint
                soup = BeautifulSoup(page_source, 'html.parser')
                
                cars_elements = soup.select('div.content.card-wrap ul.viewlist_ul li.cards-li')
                cars = [self._parse_li_to_car(li) for li in cars_elements]
                
                # Логируем данные
                logger.info("\n=== ПОЛУЧЕННЫЕ ДАННЫЕ ===")
                logger.info(f"Найдено автомобилей: {len(cars)}")
                logger.info("\nДетальная информация о автомобилях:")
                logger.info(pprint.pformat(cars, indent=2, width=120))
                
                data = Data(
                    has_more=False,
                    search_sh_sku_info_list=cars,
                    total=len(cars)
                )
                
                return ApiResponse(
                    data=data,
                    message="Success",
                    status=200
                )
                
            except Exception as e:
                return ApiResponse(
                    data=Data(has_more=False, search_sh_sku_info_list=[], total=0),
                    message=f"Ошибка: {str(e)}",
                    status=500
                )
            finally:
                if self.driver:
                    self.driver.quit()
        else:
            # Для локального файла используем обычный парсинг
            if source and source not in ('url',):  # убран 'local' из проверки
                with open(source, 'r', encoding='utf-8') as f:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(f, 'html.parser')
            else:
                with open(HTML_FILE, 'r', encoding='utf-8') as f:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(f, 'html.parser')
            
            cars_elements = soup.select('div.content.card-wrap ul.viewlist_ul li.cards-li')
            cars = [self._parse_li_to_car(li) for li in cars_elements]
            
            data = Data(
                has_more=False,
                search_sh_sku_info_list=cars,
                total=len(cars)
            )
            
            return ApiResponse(
                data=data,
                message="Success",
                status=200
            )
    
    def _parse_li_to_car(self, li) -> Car:
        """Приватный метод для парсинга элемента li в объект Car"""
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
        
        # Формируем данные для Car
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
        
        return Car(**data)

# Функция для обратной совместимости
def fetch_dongchedi_cars(source: Optional[str] = 'url') -> ApiResponse:
    """Функция для обратной совместимости"""
    parser = DongchediParser()
    return parser.fetch_cars(source)
