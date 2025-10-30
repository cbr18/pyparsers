import os
import time
import random
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from .models.detailed_car import Che168DetailedCar

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Che168DetailedParser:
    """Парсер детальной информации о машине с che168.com"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
    
    def _setup_driver(self):
        """Настройка Chrome драйвера"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        # Настройки для обхода обнаружения
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Блокировка изображений для ускорения
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.media_stream": 2,
            "profile.managed_default_content_settings.plugins": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Дополнительные оптимизации
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        # User agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        try:
            # Добавляем уникальный user-data-dir для избежания конфликтов
            import tempfile
            temp_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации драйвера: {e}")
            return False
    
    def parse_car_details(self, car_id: int) -> Optional[Che168DetailedCar]:
        """
        Парсит детальную информацию о машине по car_id
        
        Args:
            car_id: ID машины из URL (infoid=56481576)
            
        Returns:
            Che168DetailedCar или None при ошибке
        """
        url = f"https://m.che168.com/cardetail/index?infoid={car_id}&pvareaid=108948&cpcid=0&isrecom=1&queryid=1761079497987$0$a4752c93-ffa9-0229-2800-e4d9be87bcea$73347$1&cartype=30&cxextraparamsnew=&offertype=0&offertag=0&activitycartype=0&cstencryptinfo=&encryptinfo=&userareaid=0&adfromid=30173589&fromtag=0&ext=%7B%22urltype%22%3A%22%22%7D&otherstatisticsext=%7B%22cartype%22%3A30%2C%22eventid%22%3A%22usc_2sc_mc_mclby_cydj_click%22%2C%22history%22%3A%22%E5%88%97%E8%A1%A8%E9%A1%B5%22%2C%22is_remote%22%3A0%2C%22offertype%22%3A0%2C%22pvareaid%22%3A%220%22%2C%22srecom%22%3A%220%22%7D"
        
        if not self._setup_driver():
            return None
        
        try:
            logger.info(f"Парсинг детальной информации для car_id: {car_id}")
            self.driver.get(url)
            
            # Ждем загрузки страницы
            time.sleep(random.uniform(2, 4))
            
            # Прокручиваем страницу для загрузки динамического контента
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Получаем HTML
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Парсим данные
            car_data = self._extract_car_data(soup, car_id)
            
            if car_data:
                return Che168DetailedCar(**car_data)
            else:
                logger.warning(f"Не удалось извлечь данные для car_id: {car_id}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка парсинга car_id {car_id}: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
    
    def _extract_car_data(self, soup: BeautifulSoup, car_id: int) -> Optional[Dict[str, Any]]:
        """Извлекает данные о машине из HTML"""
        try:
            data = {
                'car_id': car_id
            }
            
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
            logger.error(f"Ошибка извлечения данных: {e}")
            return None
    
    def _extract_basic_info(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает основную информацию о машине"""
        try:
            # Заголовок
            title_elem = soup.find('h1') or soup.find('title')
            if title_elem:
                data['title'] = title_elem.get_text(strip=True)
            
            # Цена
            price_elem = soup.find(text=lambda t: '万' in str(t) and '元' in str(t))
            if price_elem:
                data['price'] = price_elem.strip()
            
            # Год
            year_elem = soup.find(text=lambda t: t and t.strip().isdigit() and len(t.strip()) == 4)
            if year_elem:
                try:
                    data['year'] = int(year_elem.strip())
                except ValueError:
                    pass
            
            # Пробег
            mileage_elem = soup.find(text=lambda t: '万公里' in str(t) or '公里' in str(t))
            if mileage_elem:
                data['mileage'] = mileage_elem.strip()
            
            # Город
            city_elem = soup.find(text=lambda t: '市' in str(t))
            if city_elem:
                data['city'] = city_elem.strip()
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения основной информации: {e}")
    
    def _extract_technical_specs(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает технические характеристики"""
        try:
            # Ищем таблицы с характеристиками
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        
                        # Маппинг ключей на поля модели
                        field_mapping = {
                            '排量': 'engine_volume',
                            '燃料类型': 'fuel_type',
                            '变速箱': 'transmission',
                            '驱动方式': 'drive_type',
                            '车身结构': 'body_type',
                            '颜色': 'color',
                            '车况': 'condition',
                            '功率': 'power',
                            '扭矩': 'torque',
                            '加速时间': 'acceleration',
                            '最高车速': 'max_speed',
                            '油耗': 'fuel_consumption',
                            '排放标准': 'emission_standard',
                            '长': 'length',
                            '宽': 'width',
                            '高': 'height',
                            '轴距': 'wheelbase',
                            '整备质量': 'curb_weight',
                            '总质量': 'gross_weight',
                        }
                        
                        if key in field_mapping:
                            data[field_mapping[key]] = value
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения технических характеристик: {e}")
    
    def _extract_additional_specs(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает дополнительные характеристики"""
        try:
            # Ищем div'ы с характеристиками
            spec_divs = soup.find_all('div', class_=lambda x: x and ('spec' in x.lower() or 'info' in x.lower()))
            
            for div in spec_divs:
                text = div.get_text(strip=True)
                
                # Извлекаем информацию о владельцах
                if '手' in text and '车' in text:
                    import re
                    owner_match = re.search(r'(\d+)手', text)
                    if owner_match:
                        data['owner_count'] = int(owner_match.group(1))
                
                # Извлекаем информацию о ДТП
                if '事故' in text:
                    data['accident_history'] = text
                
                # Извлекаем информацию о сервисе
                if '保养' in text or '维修' in text:
                    data['service_history'] = text
                
        except Exception as e:
            logger.warning(f"Ошибка извлечения дополнительных характеристик: {e}")
    
    def _extract_images(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает изображения"""
        try:
            images = []
            
            # Ищем все изображения
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src and src.startswith('http'):
                    images.append(src)
            
            if images:
                data['image_gallery'] = ' '.join(images)
                data['image_count'] = len(images)
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения изображений: {e}")
    
    def _extract_description(self, soup: BeautifulSoup, data: Dict[str, Any]):
        """Извлекает описание"""
        try:
            # Ищем описание в различных элементах
            desc_elem = soup.find('div', class_=lambda x: x and 'desc' in x.lower()) or \
                       soup.find('p', class_=lambda x: x and 'desc' in x.lower())
            
            if desc_elem:
                data['description'] = desc_elem.get_text(strip=True)
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения описания: {e}")





