import requests
from typing import Optional, Tuple
from .models.response import DongchediApiResponse, DongchediData
from .models.car import DongchediCar
from ..base_parser import BaseCarParser

class DongchediParser(BaseCarParser):
    """Парсер для сайта Dongchedi"""

    def __init__(self):
        self.base_url = "https://www.dongchedi.com/motor/pc/sh/sh_sku_list"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.dongchedi.com",
            "Referer": "https://www.dongchedi.com/",
            "Connection": "keep-alive"
        }

    def _build_url(self, page: int = 1) -> str:
        print(page)
        """Строит URL с параметрами запроса"""
        params = {
            "aid": "1839",  # Важный параметр для API
            "page": str(page),
            "limit": "80",
            "sort_type": "4"
        }

        # Строим URL с параметрами
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        # Проверяем, содержит ли базовый URL уже параметры
        if "?" in self.base_url:
            return f"{self.base_url}&{param_string}"
        else:
            return f"{self.base_url}?{param_string}"

    def fetch_cars(self, source: Optional[str] = None) -> DongchediApiResponse:
        """
        Выполняет запрос к API dongchedi и возвращает распарсенный DongchediApiResponse.
        По умолчанию загружает первую страницу.

        Args:
            source: Игнорируется для этого парсера, так как используется API

        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        return self.fetch_cars_by_page(1)

    def fetch_cars_by_page(self, page: int) -> DongchediApiResponse:
        """
        Выполняет запрос к API dongchedi для конкретной страницы.

        Args:
            page: Номер страницы (начиная с 1)

        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        try:
            url = self._build_url(page)

            # Попробуем использовать GET вместо POST, если POST не работает
            try:
                response = requests.post(url, headers=self.headers, timeout=3600)
                if response.status_code != 200:
                    response = requests.get(url, headers=self.headers, timeout=3600)
            except Exception:
                response = requests.get(url, headers=self.headers, timeout=3600)

            response.raise_for_status()

            # Проверяем кодировку ответа
            encoding = response.encoding

            # Если кодировка не определена или неправильная, пробуем UTF-8
            if not encoding or encoding.lower() == 'iso-8859-1':
                try:
                    response.encoding = 'utf-8'
                except:
                    pass

            try:
                data = response.json()
            except Exception:
                # Пробуем исправить некорректный JSON
                import json
                try:
                    # Иногда API может возвращать некорректный JSON с экранированными кавычками
                    fixed_text = response.text.replace('\\"', '"').replace('\\\\', '\\')
                    data = json.loads(fixed_text)
                except:
                    # Если все еще не работает, пробуем другой подход
                    try:
                        import re
                        # Находим начало и конец JSON объекта
                        match = re.search(r'(\{.*\})', response.text, re.DOTALL)
                        if match:
                            data = json.loads(match.group(1))
                        else:
                            raise Exception("Could not find JSON object in response")
                    except Exception as e:
                        raise Exception(f"Failed to parse JSON: {str(e)}")

            # Преобразуем данные в наши модели
            cars = []
            if 'data' in data and 'search_sh_sku_info_list' in data['data']:
                for car_data in data['data']['search_sh_sku_info_list']:
                    try:
                        # Генерируем UUID для каждой машины
                        import uuid

                        # Фильтруем и преобразуем поля для нашей модели
                        filtered_car_data = {}
                        for k, v in car_data.items():
                            if k in DongchediCar.__fields__:
                                # Преобразуем списки в строки для полей tags и tags_v2
                                if k in ['tags', 'tags_v2'] and v is not None:
                                    import json
                                    filtered_car_data[k] = json.dumps(v)
                                else:
                                    filtered_car_data[k] = v

                        # Добавляем UUID
                        filtered_car_data['uuid'] = str(uuid.uuid4())

                        # Устанавливаем source
                        filtered_car_data['source'] = 'dongchedi'

                        # Convert car_id and sku_id to strings to match Go struct expectations
                        if 'car_id' in filtered_car_data and filtered_car_data['car_id'] is not None:
                            filtered_car_data['car_id'] = str(filtered_car_data['car_id'])

                        if 'sku_id' in filtered_car_data and filtered_car_data['sku_id'] is not None:
                            filtered_car_data['sku_id'] = str(filtered_car_data['sku_id'])

                        # Копируем значения из одних полей в другие для совместимости
                        if 'car_year' in filtered_car_data and filtered_car_data['car_year'] is not None:
                            filtered_car_data['year'] = filtered_car_data['car_year']

                        if 'car_mileage' in filtered_car_data and filtered_car_data['car_mileage'] is not None:
                            # Преобразуем mileage в числовое значение, если возможно
                            try:
                                import re
                                mileage_str = str(filtered_car_data['car_mileage'])
                                mileage_numeric = re.sub(r'[^\d.]', '', mileage_str)
                                if mileage_numeric:
                                    filtered_car_data['mileage'] = int(float(mileage_numeric))
                            except:
                                pass

                        if 'car_source_city_name' in filtered_car_data and filtered_car_data['car_source_city_name'] is not None:
                            from converters import decode_dongchedi_detail
                            filtered_car_data['city'] = decode_dongchedi_detail(filtered_car_data['car_source_city_name'])

                        # Устанавливаем is_available по умолчанию в True
                        filtered_car_data['is_available'] = True

                        # Декодируем поля, которые могут содержать специальные символы
                        from converters import decode_dongchedi_list_sh_price, decode_dongchedi_detail
                        # Декодируем цены
                        for price_field in ['sh_price', 'official_price']:
                            if price_field in filtered_car_data and filtered_car_data[price_field] is not None:
                                filtered_car_data[price_field] = decode_dongchedi_list_sh_price(str(filtered_car_data[price_field]))

                        # Декодируем текстовые поля
                        for text_field in ['title', 'sub_title', 'car_name']:
                            if text_field in filtered_car_data and filtered_car_data[text_field] is not None:
                                filtered_car_data[text_field] = decode_dongchedi_detail(str(filtered_car_data[text_field]))

                        # Ensure price is properly set from sh_price
                        if 'sh_price' in filtered_car_data and filtered_car_data['sh_price'] is not None:
                            # Convert price to a numeric value if it's a string with units
                            price_str = str(filtered_car_data['sh_price'])
                            # Remove any non-numeric characters except decimal point
                            import re
                            price_numeric = re.sub(r'[^\d.]', '', price_str)
                            if price_numeric:
                                filtered_car_data['price'] = price_numeric

                        # Add current timestamp for created_at and updated_at if they don't exist
                        import datetime
                        # Форматируем время в формате RFC3339, который совместим с Go
                        current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        if 'created_at' not in filtered_car_data or filtered_car_data['created_at'] is None:
                            filtered_car_data['created_at'] = current_time
                        if 'updated_at' not in filtered_car_data or filtered_car_data['updated_at'] is None:
                            filtered_car_data['updated_at'] = current_time

                        car = DongchediCar(**filtered_car_data)
                        cars.append(car)
                    except Exception:
                        continue

            # Если данных нет или список пуст, считаем что страницы не существует
            if not cars:
                return DongchediApiResponse(
                    data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                    message=f"Страница {page} не найдена или данные не соответствуют ожидаемому формату",
                    status=404
                )

            dongchedi_data = DongchediData(
                has_more=data.get('data', {}).get('has_more', False),
                search_sh_sku_info_list=cars,
                total=data.get('data', {}).get('total', 0)
            )

            return DongchediApiResponse(
                data=dongchedi_data,
                message=data.get('message', 'Success'),
                status=data.get('status', 200)
            )

        except Exception as e:
            return DongchediApiResponse(
                data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                message=f"Ошибка при получении данных: {str(e)}",
                status=500
            )

    def fetch_car_detail(self, car_id: str):
        """
        Парсит детальную информацию о машине по car_id через selenium/beautifulsoup.
        Возвращает (DongchediCar | None, meta: dict)
        """
        import time
        import random
        import json
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.common.exceptions import TimeoutException, WebDriverException
        from bs4 import BeautifulSoup

        url = f"https://www.dongchedi.com/usedcar/{car_id}"
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
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
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
        driver = None
        try:
            import os
            chrome_bin = os.environ.get("CHROME_BIN")
            if chrome_bin:
                chrome_options.binary_location = chrome_bin
            driver_path = os.environ.get("CHROMEDRIVER_PATH")
            if driver_path:
                driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.get(url)
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
        # Добавляем текущее время для полей created_at и updated_at
        import datetime
        # Форматируем время в формате RFC3339, который совместим с Go
        current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Генерируем UUID для новой записи
        import uuid

        car_info = {
            "uuid": str(uuid.uuid4()),  # Генерируем UUID
            "title": None,
            "sh_price": None,
            "price": None,
            "image": None,
            "link": url,
            "car_name": None,
            "car_year": None,
            "year": None,
            "car_mileage": None,
            "mileage": None,
            "car_source_city_name": None,
            "city": None,
            "brand_name": None,
            "series_name": None,
            "brand_id": None,
            "series_id": None,
            "shop_id": None,
            "car_id": car_id,  # Keep as string to match Go struct
            "tags_v2": None,
            "tags": None,
            "sku_id": car_id,  # Keep as string to match Go struct
            "sort_number": 1,
            "source": "dongchedi",
            "is_available": True,
            "description": None,
            "color": None,
            "transmission": None,
            "fuel_type": None,
            "engine_volume": None,
            "body_type": None,
            "drive_type": None,
            "condition": None,
            "created_at": current_time,
            "updated_at": current_time
        }
        scripts = soup.find_all('script')
        json_data_found = False
        for script in scripts:
            if hasattr(script, 'string') and script.string:
                script_content = script.string
                if '__NEXT_DATA__' in script_content:
                    try:
                        start = script_content.find('{')
                        end = script_content.rfind('}') + 1
                        if start != -1 and end != 0:
                            json_data = json.loads(script_content[start:end])
                            if 'props' in json_data and 'pageProps' in json_data['props']:
                                page_props = json_data['props']['pageProps']
                                if 'skuDetail' in page_props:
                                    sku_detail = page_props['skuDetail']
                                    car_info.update({
                                        'title': sku_detail.get('title', ''),
                                        'sh_price': sku_detail.get('sh_price', ''),
                                        'car_mileage': sku_detail.get('car_info', {}).get('mileage', ''),
                                        'car_year': sku_detail.get('car_info', {}).get('year', ''),
                                        'year': sku_detail.get('car_info', {}).get('year', ''),
                                        'brand_name': sku_detail.get('car_info', {}).get('brand_name', ''),
                                        'series_name': sku_detail.get('car_info', {}).get('series_name', ''),
                                        'car_name': sku_detail.get('car_info', {}).get('car_name', ''),
                                        'image': sku_detail.get('image', ''),
                                        'shop_id': sku_detail.get('shop_info', {}).get('shop_id', ''),
                                        'brand_id': sku_detail.get('car_info', {}).get('brand_id', 0),
                                        'series_id': sku_detail.get('car_info', {}).get('series_id', 0),
                                        'car_source_city_name': sku_detail.get('car_info', {}).get('city', ''),
                                        'city': sku_detail.get('car_info', {}).get('city', ''),
                                        'description': sku_detail.get('description', ''),
                                        'color': sku_detail.get('car_info', {}).get('color', ''),
                                        'transmission': sku_detail.get('car_info', {}).get('transmission', ''),
                                        'fuel_type': sku_detail.get('car_info', {}).get('fuel_type', ''),
                                        'engine_volume': sku_detail.get('car_info', {}).get('engine_volume', ''),
                                        'body_type': sku_detail.get('car_info', {}).get('body_type', ''),
                                        'drive_type': sku_detail.get('car_info', {}).get('drive_type', ''),
                                        'condition': sku_detail.get('car_info', {}).get('condition', ''),
                                    })
                                    json_data_found = True
                                    break
                    except (json.JSONDecodeError, KeyError):
                        continue
        if not json_data_found:
            title_tag = soup.find('title')
            if title_tag:
                car_info['title'] = title_tag.get_text().strip()
                car_info['car_name'] = title_tag.get_text().strip()
            price_selectors = [
                'span.tw-text-color-red-500',
                'p.tw-text-color-red-500',
                'span[class*="price"]',
                'b.num-price',
                '.price',
                '[class*="price"]'
            ]
            for selector in price_selectors:
                price_elements = soup.select(selector)
                if price_elements:
                    for elem in price_elements:
                        price_text = elem.get_text().strip()
                        if any(char in price_text for char in ['万', '元', '¥', '￥']):
                            car_info['sh_price'] = price_text
                            break
                    if car_info['sh_price']:
                        break
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description and hasattr(meta_description, 'get'):
                content = meta_description.get('content', '')
                if content:
                    car_info['tags_v2'] = content
        page_text = soup.get_text()
        available_indicators = [
            "询底价", "点击查看联系电话", "我要优惠", "立即查询",
            "询价", "联系", "电话", "咨询", "优惠"
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
            # Применяем декодер к нужным полям
            from converters import decode_dongchedi_detail
            for key in ["title", "car_name", "sh_price"]:
                if car_info.get(key):
                    car_info[key] = decode_dongchedi_detail(car_info[key])
                # Декодируем город
                if car_info.get("city"):
                    car_info["city"] = decode_dongchedi_detail(car_info["city"])
                if car_info.get("car_source_city_name"):
                    car_info["car_source_city_name"] = decode_dongchedi_detail(car_info["car_source_city_name"])

            # Преобразуем списки в строки для полей tags и tags_v2
            for key in ["tags", "tags_v2"]:
                if car_info.get(key) is not None and not isinstance(car_info[key], str):
                    import json
                    try:
                        car_info[key] = json.dumps(car_info[key])
                    except:
                        car_info[key] = str(car_info[key])

            # Ensure price is properly set from sh_price
            if car_info.get('sh_price'):
                # Convert price to a numeric value if it's a string with units
                price_str = str(car_info['sh_price'])
                # Remove any non-numeric characters except decimal point
                import re
                price_numeric = re.sub(r'[^\d.]', '', price_str)
                if price_numeric:
                    car_info['price'] = price_numeric

            car_obj = DongchediCar(**{k: v for k, v in car_info.items() if k in DongchediCar.__fields__})
        except Exception as e:
            return None, {"is_available": False, "error": str(e), "status": 500}
        return car_obj, {"is_available": is_available, "status": 200, "link": url}

    def fetch_all_cars(self):
        """
        Получает все машины со всех страниц dongchedi.
        Возвращает DongchediApiResponse с полным списком машин.
        """
        all_cars = []
        seen_ids = set()
        page = 1
        
        # Основной проход по всем страницам
        while True:
            response = self.fetch_cars_by_page(page)
            cars_list = getattr(response.data, 'search_sh_sku_info_list', None)
            if not cars_list:
                break
            
            for car in cars_list:
                car_dict = car.dict()
                car_id = car_dict.get('car_id') or car_dict.get('sku_id') or car_dict.get('link')
                if car_id not in seen_ids:
                    all_cars.append(car)
                    seen_ids.add(car_id)
            
            if not getattr(response.data, 'has_more', False):
                break
            page += 1

        # Создаем ответ с полным списком машин
        from .models.response import DongchediData
        return DongchediApiResponse(
            data=DongchediData(
                has_more=False,
                search_sh_sku_info_list=all_cars,
                total=len(all_cars)
            ),
            message=f"Загружено {len(all_cars)} машин со всех страниц",
            status=200
        )

    def fetch_multiple_car_details(self, car_ids):
        """
        Получает детальную информацию о нескольких машинах по их ID.
        
        Args:
            car_ids: Список ID машин
            
        Returns:
            Список кортежей (DongchediCar | None, meta: dict)
        """
        results = []
        for car_id in car_ids:
            car_obj, meta = self.fetch_car_detail(car_id)
            results.append((car_obj, meta))
        return results
