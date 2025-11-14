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
            "updated_at": current_time,
            # Новые поля для детальной информации
            "has_details": False,
            "last_detail_update": None,
            "power": None,
            "torque": None,
            "acceleration": None,
            "max_speed": None,
            "fuel_consumption": None,
            "emission_standard": None,
            "length": None,
            "width": None,
            "height": None,
            "wheelbase": None,
            "curb_weight": None,
            "gross_weight": None,
            "engine_type": None,
            "engine_code": None,
            "cylinder_count": None,
            "valve_count": None,
            "compression_ratio": None,
            "turbo_type": None,
            "battery_capacity": None,
            "electric_range": None,
            "charging_time": None,
            "fast_charge_time": None,
            "charge_port_type": None,
            "transmission_type": None,
            "gear_count": None,
            "differential_type": None,
            "front_suspension": None,
            "rear_suspension": None,
            "front_brakes": None,
            "rear_brakes": None,
            "brake_system": None,
            "wheel_size": None,
            "tire_size": None,
            "wheel_type": None,
            "tire_type": None,
            "airbag_count": None,
            "abs": None,
            "esp": None,
            "tcs": None,
            "hill_assist": None,
            "blind_spot_monitor": None,
            "lane_departure": None,
            "air_conditioning": None,
            "climate_control": None,
            "seat_heating": None,
            "seat_ventilation": None,
            "seat_massage": None,
            "steering_wheel_heating": None,
            "navigation": None,
            "audio_system": None,
            "speakers_count": None,
            "bluetooth": None,
            "usb": None,
            "aux": None,
            "headlight_type": None,
            "fog_lights": None,
            "led_lights": None,
            "daytime_running": None,
            "owner_count": 0,
            "accident_history": None,
            "service_history": None,
            "warranty_info": None,
            "inspection_date": None,
            "insurance_info": None,
            "interior_color": None,
            "exterior_color": None,
            "upholstery": None,
            "sunroof": None,
            "panoramic_roof": None,
            "view_count": 0,
            "favorite_count": 0,
            "contact_info": None,
            "dealer_info": None,
            "certification": None,
            "image_gallery": None,
            "image_count": 0,
            "seat_count": None,
            "door_count": None,
            "trunk_volume": None,
            "fuel_tank_volume": None
        }
        # Ищем скрипт с __NEXT_DATA__ по id
        script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
        json_data_found = False
        if script_tag and script_tag.string:
            try:
                json_data = json.loads(script_tag.string)
                if 'props' in json_data and 'pageProps' in json_data['props']:
                    page_props = json_data['props']['pageProps']
                    if 'skuDetail' in page_props:
                        sku_detail = page_props['skuDetail']
                        
                        # Парсим галерею изображений
                        head_images = sku_detail.get('head_images', [])
                        if head_images and isinstance(head_images, list):
                            # Сохраняем первую картинку в image
                            car_info['image'] = head_images[0] if len(head_images) > 0 else ''
                            # Сохраняем все картинки через пробел
                            car_info['image_gallery'] = ' '.join(head_images)
                            car_info['image_count'] = len(head_images)
                        else:
                            car_info['image'] = sku_detail.get('image', '')
                        
                        # Парсим дополнительные данные
                        shop_info = sku_detail.get('shop_info', {})
                        other_params = sku_detail.get('other_params', [])
                        
                        # Извлекаем информацию о владельцах, пробеге и т.д. из other_params
                        for param in other_params:
                            param_name = param.get('name', '')
                            param_value = param.get('value', '')
                            
                            if param_name == '过户次数':
                                # Количество владельцев
                                try:
                                    car_info['owner_count'] = int(param_value.replace('次', '').strip())
                                except:
                                    pass
                            elif param_name == '上牌地':
                                car_info['inspection_date'] = param_value
                            elif param_name == '内饰颜色':
                                car_info['interior_color'] = param_value
                            elif param_name == '车身颜色':
                                car_info['exterior_color'] = param_value
                        
                        # Извлекаем информацию о дилере
                        if shop_info:
                            dealer_parts = []
                            if shop_info.get('shop_name'):
                                dealer_parts.append(f"Название: {shop_info['shop_name']}")
                            if shop_info.get('shop_address'):
                                dealer_parts.append(f"Адрес: {shop_info['shop_address']}")
                            if shop_info.get('business_time'):
                                dealer_parts.append(f"Время работы: {shop_info['business_time']}")
                            if shop_info.get('sales_car_num'):
                                dealer_parts.append(f"Машин в продаже: {shop_info['sales_car_num']}")
                            car_info['dealer_info'] = '; '.join(dealer_parts)
                        
                        # Извлекаем сертификацию
                        tags = sku_detail.get('tags', [])
                        if tags and isinstance(tags, list):
                            cert_parts = []
                            for tag in tags:
                                if isinstance(tag, dict) and tag.get('text'):
                                    cert_parts.append(tag['text'])
                            if cert_parts:
                                car_info['certification'] = '; '.join(cert_parts)
                        
                        # Извлекаем количество просмотров и избранного
                        car_info['favorite_count'] = sku_detail.get('favored_count', 0)
                        
                        # Парсим car_config_overview для дополнительных характеристик
                        car_config = sku_detail.get('car_config_overview', {})
                        if car_config:
                            # Подвеска из manipulation
                            manipulation = car_config.get('manipulation', {})
                            if manipulation:
                                car_info['front_suspension'] = manipulation.get('front_suspension_form', '')
                                car_info['rear_suspension'] = manipulation.get('rear_suspension_form', '')
                                if manipulation.get('driver_form'):
                                    car_info['drive_type'] = manipulation.get('driver_form', '')
                            
                            # Характеристики электромобиля
                            new_energy = car_config.get('new_energy_power', {})
                            if new_energy:
                                car_info['acceleration'] = new_energy.get('acceleration_time', '')
                                car_info['fuel_type'] = new_energy.get('fuel_form', '')
                                car_info['transmission_type'] = new_energy.get('gearbox_description', '')
                                car_info['power'] = new_energy.get('horsepower', '')
                            
                            # Размеры из space
                            space = car_config.get('space', {})
                            if space:
                                car_info['height'] = space.get('height', '')
                                car_info['length'] = space.get('length', '')
                                car_info['width'] = space.get('width', '')
                                car_info['wheelbase'] = space.get('wheelbase', '')
                        
                        car_info.update({
                            'title': sku_detail.get('title', ''),
                            'sh_price': sku_detail.get('sh_price', ''),
                            'car_mileage': sku_detail.get('car_info', {}).get('mileage', ''),
                            'car_year': sku_detail.get('car_info', {}).get('year', ''),
                            'year': sku_detail.get('car_info', {}).get('year', ''),
                            'brand_name': sku_detail.get('car_info', {}).get('brand_name', ''),
                            'series_name': sku_detail.get('car_info', {}).get('series_name', ''),
                            'car_name': sku_detail.get('car_info', {}).get('car_name', ''),
                            'shop_id': shop_info.get('shop_id', ''),
                            'brand_id': sku_detail.get('car_info', {}).get('brand_id', 0),
                            'series_id': sku_detail.get('car_info', {}).get('series_id', 0),
                            'car_source_city_name': sku_detail.get('car_info', {}).get('city', ''),
                            'city': sku_detail.get('car_info', {}).get('city', ''),
                            'description': sku_detail.get('sh_car_desc', ''),
                            'color': sku_detail.get('car_info', {}).get('color', ''),
                            'transmission': sku_detail.get('car_info', {}).get('transmission', ''),
                            'fuel_type': sku_detail.get('car_info', {}).get('fuel_type', '') or car_info.get('fuel_type', ''),
                            'engine_volume': sku_detail.get('car_info', {}).get('engine_volume', ''),
                            'body_type': sku_detail.get('car_info', {}).get('body_type', ''),
                            'drive_type': sku_detail.get('car_info', {}).get('drive_type', '') or car_info.get('drive_type', ''),
                            'condition': sku_detail.get('car_info', {}).get('condition', ''),
                        })
                        json_data_found = True
            except (json.JSONDecodeError, KeyError):
                pass
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

    def fetch_car_specifications(self, car_id: str):
        """
        Парсит технические характеристики машины по car_id через страницу параметров.
        Возвращает (dict | None, meta: dict)
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

        url = f"https://www.dongchedi.com/auto/params-carIds-{car_id}"
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

        # Парсим технические характеристики из таблицы
        specs = {}
        
        # Ищем таблицы с параметрами
        table_rows = soup.find_all('div', class_='table_row__yVX1h')
        
        for row in table_rows:
            try:
                label_elem = row.find('label', class_='cell_label__ZtXlw')
                value_elem = row.find('div', class_='cell_normal__37nRi')
                
                if label_elem and value_elem:
                    label = label_elem.get_text().strip()
                    value = value_elem.get_text().strip()
                    
                    # Маппинг китайских названий на английские поля
                    field_mapping = {
                        '最大功率(kW)': 'power',
                        '最大扭矩(N·m)': 'torque',
                        '官方百公里加速时间(s)': 'acceleration',
                        '最高车速(km/h)': 'max_speed',
                        '百公里耗电量(kWh/100km)': 'fuel_consumption',
                        '长x宽x高(mm)': 'dimensions',
                        '车身结构': 'body_structure',
                        '纯电续航里程(km)': 'electric_range',
                        '充电时间(小时)': 'charging_time',
                        '快充时间(小时)': 'fast_charge_time',
                        '发动机': 'engine_type',
                        '排量(mL)': 'engine_volume',
                        '变速箱': 'transmission_type',
                        '驱动方式': 'drive_type',
                        '前悬架类型': 'front_suspension',
                        '后悬架类型': 'rear_suspension',
                        '前制动器类型': 'front_brakes',
                        '后制动器类型': 'rear_brakes',
                        '轮胎规格': 'tire_size',
                        '轮毂规格': 'wheel_size',
                        '主/副驾驶座安全气囊': 'airbag_count',
                        'ABS防抱死': 'abs',
                        'ESP车身稳定系统': 'esp',
                        'TCS牵引力控制': 'tcs',
                        '上坡辅助': 'hill_assist',
                        '盲区监测': 'blind_spot_monitor',
                        '车道偏离预警': 'lane_departure',
                        '空调': 'air_conditioning',
                        '自动空调': 'climate_control',
                        '座椅加热': 'seat_heating',
                        '座椅通风': 'seat_ventilation',
                        '座椅按摩': 'seat_massage',
                        '方向盘加热': 'steering_wheel_heating',
                        'GPS导航': 'navigation',
                        '音响系统': 'audio_system',
                        '扬声器数量': 'speakers_count',
                        '蓝牙': 'bluetooth',
                        'USB接口': 'usb',
                        'AUX接口': 'aux',
                        '前大灯类型': 'headlight_type',
                        '前雾灯': 'fog_lights',
                        'LED大灯': 'led_lights',
                        '日间行车灯': 'daytime_running',
                        '座位数': 'seat_count',
                        '车门数': 'door_count',
                        '行李厢容积(L)': 'trunk_volume',
                        '油箱容积(L)': 'fuel_tank_volume'
                    }
                    
                    if label in field_mapping:
                        field_name = field_mapping[label]
                        specs[field_name] = value
                        
                        # Обработка специальных случаев
                        if field_name == 'dimensions':
                            # Парсим размеры из строки "5200x2062x1618"
                            try:
                                parts = value.split('x')
                                if len(parts) == 3:
                                    specs['length'] = parts[0]
                                    specs['width'] = parts[1]
                                    specs['height'] = parts[2]
                            except:
                                pass
                        
            except Exception:
                continue

        return specs, {"status": 200, "link": url}

    def enhance_car_with_details(self, car_obj, sku_id: str, car_id: str = None):
        """
        Улучшает объект машины детальной информацией.
        
        Args:
            car_obj: Объект DongchediCar
            sku_id: SKU ID для детальной страницы
            car_id: Car ID для страницы характеристик (опционально)
            
        Returns:
            Улучшенный объект DongchediCar
        """
        import datetime
        
        # Получаем детальную информацию
        detail_car, detail_meta = self.fetch_car_detail(sku_id)
        
        # Получаем технические характеристики, если car_id предоставлен
        specs = {}
        if car_id:
            specs, specs_meta = self.fetch_car_specifications(car_id)
        
        # Обновляем объект машины
        if detail_car:
            # Копируем детальную информацию
            for field in ['power', 'torque', 'acceleration', 'max_speed', 'fuel_consumption',
                         'emission_standard', 'length', 'width', 'height', 'wheelbase',
                         'curb_weight', 'gross_weight', 'engine_type', 'engine_code',
                         'cylinder_count', 'valve_count', 'compression_ratio', 'turbo_type',
                         'battery_capacity', 'electric_range', 'charging_time', 'fast_charge_time',
                         'charge_port_type', 'transmission_type', 'gear_count', 'differential_type',
                         'front_suspension', 'rear_suspension', 'front_brakes', 'rear_brakes',
                         'brake_system', 'wheel_size', 'tire_size', 'wheel_type', 'tire_type',
                         'airbag_count', 'abs', 'esp', 'tcs', 'hill_assist', 'blind_spot_monitor',
                         'lane_departure', 'air_conditioning', 'climate_control', 'seat_heating',
                         'seat_ventilation', 'seat_massage', 'steering_wheel_heating', 'navigation',
                         'audio_system', 'speakers_count', 'bluetooth', 'usb', 'aux', 'headlight_type',
                         'fog_lights', 'led_lights', 'daytime_running', 'owner_count', 'accident_history',
                         'service_history', 'warranty_info', 'inspection_date', 'insurance_info',
                         'interior_color', 'exterior_color', 'upholstery', 'sunroof', 'panoramic_roof',
                         'view_count', 'favorite_count', 'contact_info', 'dealer_info', 'certification',
                         'image_gallery', 'image_count', 'seat_count', 'door_count', 'trunk_volume',
                         'fuel_tank_volume']:
                if hasattr(detail_car, field) and getattr(detail_car, field) is not None:
                    setattr(car_obj, field, getattr(detail_car, field))
        
        # Добавляем технические характеристики
        for field, value in specs.items():
            if hasattr(car_obj, field):
                setattr(car_obj, field, value)
        
        # Проверяем, что хотя бы power был успешно распарсен
        # power может быть из detail_car или из specs
        power_value = None
        if hasattr(car_obj, 'power'):
            power_value = getattr(car_obj, 'power')
        
        # Проверяем, что power не None и не пустая строка
        has_power = power_value is not None and str(power_value).strip() != ''
        
        # Устанавливаем флаги только если power был успешно распарсен
        if has_power:
            car_obj.has_details = True
            car_obj.last_detail_update = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            # Если power не был распарсен, оставляем has_details = False
            car_obj.has_details = False
            # Не обновляем last_detail_update, если парсинг не удался
        
        return car_obj
