import re
import logging
import os
import requests
from typing import Optional, Tuple, Union, Dict, Any
from .models.response import DongchediApiResponse, DongchediData
from .models.car import DongchediCar
from ..base_parser import BaseCarParser
from api.date_utils import normalize_first_registration_date
from api.mileage_utils import normalize_mileage

logger = logging.getLogger(__name__)


def parse_float_value(raw_value: Union[str, int, float, None]) -> Optional[float]:
    """
    Преобразует строковое значение в float.
    
    Args:
        raw_value: Исходное значение
        
    Returns:
        float или None
    """
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    value_str = str(raw_value).strip()
    if not value_str:
        return None
    # Извлекаем число из строки
    match = re.search(r'([\d.,]+)', value_str)
    if match:
        try:
            return float(match.group(1).replace(',', '.'))
        except ValueError:
            return None
    return None


def parse_int_value(raw_value: Union[str, int, float, None]) -> Optional[int]:
    """
    Преобразует строковое значение в int.
    
    Args:
        raw_value: Исходное значение
        
    Returns:
        int или None
    """
    if raw_value is None:
        return None
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, float):
        return int(raw_value)
    value_str = str(raw_value).strip()
    if not value_str:
        return None
    # Извлекаем число из строки
    match = re.search(r'(\d+)', value_str)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


_PS_PATTERN = re.compile(r'\(([\d.,]+)\s*[Pp][Ss]?\)')
_HORSEPOWER_UNIT_PATTERN = re.compile(r'([\d.,]+)\s*(?:[Pp][Ss]?|л\.с\.|HP|hp)')
_KW_PATTERN = re.compile(r'[\d.,]+\s*[Kk][Ww]')
_FIRST_NUMBER_PATTERN = re.compile(r'([\d.,]+)')
_KW_TO_HP = 1.35962


def _parse_number(text: str) -> Optional[float]:
    match = _FIRST_NUMBER_PATTERN.search(text)
    if not match:
        return None
    number_str = match.group(1).replace(',', '.')
    try:
        return float(number_str)
    except ValueError:
        return None


def _format_hp(value: float) -> int:
    """Форматирует значение мощности как целое число л.с."""
    return int(round(value))


def normalize_power_value(raw_value, assume_kw: bool = False) -> Optional[int]:
    """
    Нормализует значение мощности и возвращает его как целое число л.с.
    
    Args:
        raw_value: Исходное значение (строка или число)
        assume_kw: Если True, предполагаем что значение в кВт если единицы не указаны
        
    Returns:
        Мощность в л.с. как int или None
    """
    if raw_value is None:
        return None
    value_str = str(raw_value).strip()
    if not value_str:
        return None
    normalized = value_str.replace('（', '(').replace('）', ')')

    match = _PS_PATTERN.search(normalized)
    if match:
        number = _parse_number(match.group(1))
        if number is not None:
            return _format_hp(number)

    match = _HORSEPOWER_UNIT_PATTERN.search(normalized)
    if match:
        number = _parse_number(match.group(1))
        if number is not None:
            return _format_hp(number)

    if _KW_PATTERN.search(normalized):
        number = _parse_number(normalized)
        if number is not None:
            return _format_hp(number * _KW_TO_HP)

    if assume_kw:
        number = _parse_number(normalized)
        if number is not None:
            return _format_hp(number * _KW_TO_HP)

    number = _parse_number(normalized)
    if number is not None:
        return _format_hp(number)

    return None

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

    def _parse_sku_detail(self, sku_detail: Dict[str, Any], car_id: str) -> Dict[str, Any]:
        """
        Общий метод для парсинга данных из skuDetail.
        Используется в _fetch_with_playwright, _fetch_mobile_version и fetch_car_detail.
        """
        result = {}
        
        # Изображения
        head_images = sku_detail.get('head_images', [])
        if head_images and isinstance(head_images, list) and len(head_images) > 0:
            result['image'] = head_images[0]
            result['image_gallery'] = ' '.join(head_images)
            result['image_count'] = len(head_images)
        
        # Пробег из important_text (формат: "2023年上牌 | 4万公里 | 城市")
        mileage_km = None
        imp_text = sku_detail.get("important_text", "")
        if imp_text:
            m = re.search(r'(\d+\.?\d*)\s*万公里', imp_text)
            if m:
                mileage_km = int(float(m.group(1)) * 10000)
                result['mileage'] = mileage_km
                result['car_mileage'] = str(mileage_km)
        
        # Данные из other_params
        other_params = sku_detail.get("other_params", [])
        for param in other_params:
            if not isinstance(param, dict):
                continue
            param_name = param.get('name', '') or param.get('key', '')
            param_value = param.get('value', '')
            
            # Дата регистрации
            if param_name in ('上牌时间', '首次上牌', '首次上牌时间'):
                normalized_date = normalize_first_registration_date(param_value)
                if normalized_date:
                    result['first_registration_time'] = normalized_date
            
            # Пробег (fallback если не нашли в important_text)
            if not mileage_km and ('里程' in param_name or '公里' in param_name):
                m = re.search(r'(\d+\.?\d*)', str(param_value))
                if m:
                    val = float(m.group(1))
                    mileage_km = int(val * 10000) if val < 1000 else int(val)
                    result['mileage'] = mileage_km
                    result['car_mileage'] = str(mileage_km)
            
            # Другие параметры
            if param_name == '过户次数':
                try:
                    result['owner_count'] = int(param_value.replace('次', '').strip())
                except:
                    pass
            elif param_name == '内饰颜色':
                result['interior_color'] = param_value
            elif param_name == '车身颜色':
                result['exterior_color'] = param_value
        
        # Основные поля из skuDetail
        result['title'] = sku_detail.get('title', '')
        result['sh_price'] = sku_detail.get('sh_price', '')
        result['sku_id'] = str(sku_detail.get('sku_id', car_id))
        result['description'] = sku_detail.get('sh_car_desc', '')
        result['favorite_count'] = sku_detail.get('favored_count', 0)
        
        # car_info
        car_info = sku_detail.get('car_info', {})
        if car_info:
            result['brand_name'] = car_info.get('brand_name', '')
            result['series_name'] = car_info.get('series_name', '')
            result['car_name'] = car_info.get('car_name', '')
            result['car_year'] = car_info.get('year')
            result['year'] = car_info.get('year')
            result['city'] = car_info.get('city', '')
            result['car_source_city_name'] = car_info.get('city', '')
            result['brand_id'] = car_info.get('brand_id')
            result['series_id'] = car_info.get('series_id')
            result['color'] = car_info.get('color', '')
            result['transmission'] = car_info.get('transmission', '')
            result['fuel_type'] = car_info.get('fuel_type', '')
            result['body_type'] = car_info.get('body_type', '')
            result['drive_type'] = car_info.get('drive_type', '')
            if car_info.get('car_id'):
                result['car_id'] = str(car_info.get('car_id'))
        
        # shop_info
        shop_info = sku_detail.get('shop_info', {})
        if shop_info:
            result['shop_id'] = shop_info.get('shop_id')
            dealer_parts = []
            if shop_info.get('shop_name'):
                dealer_parts.append(f"Название: {shop_info['shop_name']}")
            if shop_info.get('shop_address'):
                dealer_parts.append(f"Адрес: {shop_info['shop_address']}")
            if dealer_parts:
                result['dealer_info'] = '; '.join(dealer_parts)
        
        # Теги/сертификация
        tags = sku_detail.get('tags', [])
        if tags and isinstance(tags, list):
            cert_parts = [tag.get('text') for tag in tags if isinstance(tag, dict) and tag.get('text')]
            if cert_parts:
                result['certification'] = '; '.join(cert_parts)
        
        return result
    
    def _fetch_mobile_version(self, car_id: str) -> Optional[Dict[str, Any]]:
        """
        Fallback: парсинг через requests (без браузера).
        """
        import json
        from bs4 import BeautifulSoup
        
        url = f"https://m.dongchedi.com/usedcar/{car_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
            "Accept": "text/html",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200 or '__NEXT_DATA__' not in response.text:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            
            if not script_tag or not script_tag.string:
                return None
            
            data = json.loads(script_tag.string)
            sku_detail = data.get('props', {}).get('pageProps', {}).get('skuDetail', {})
            
            if sku_detail:
                result = self._parse_sku_detail(sku_detail, car_id)
                if result:
                    logger.info(f"[MOBILE] Успешно: mileage={result.get('mileage')}")
                    return result
            
            return None
            
        except Exception as e:
            logger.debug(f"[MOBILE] Ошибка для car_id={car_id}: {e}")
            return None

    def _fetch_with_playwright(self, car_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные о машине через Playwright (основной метод).
        Работает стабильнее Selenium в Docker.
        """
        try:
            from playwright.sync_api import sync_playwright
            import json
            
            url = f"https://www.dongchedi.com/usedcar/{car_id}"
            logger.info(f"[PLAYWRIGHT] Загружаем {url}")
            
            with sync_playwright() as p:
                launch_kwargs = {"headless": True}
                chrome_bin = os.environ.get("CHROME_BIN") or "/usr/bin/chromium"
                if chrome_bin:
                    launch_kwargs["executable_path"] = chrome_bin
                browser = p.chromium.launch(**launch_kwargs)
                page = browser.new_page()
                
                try:
                    page.goto(url, timeout=25000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2500)
                    
                    nd = page.query_selector("#__NEXT_DATA__")
                    if not nd:
                        logger.warning(f"[PLAYWRIGHT] __NEXT_DATA__ не найден для car_id={car_id}")
                        browser.close()
                        return None
                    
                    data = json.loads(nd.inner_text())
                    sku_detail = data.get("props", {}).get("pageProps", {}).get("skuDetail", {})
                    
                    if not sku_detail:
                        logger.warning(f"[PLAYWRIGHT] skuDetail пустой для car_id={car_id}")
                        browser.close()
                        return None
                    
                    # Используем общий метод парсинга
                    result = self._parse_sku_detail(sku_detail, car_id)
                    logger.info(f"[PLAYWRIGHT] Успешно: mileage={result.get('mileage')}, images={result.get('image_count')}")
                    browser.close()
                    return result
                    
                except Exception as e:
                    logger.warning(f"[PLAYWRIGHT] Ошибка для car_id={car_id}: {e}")
                    try:
                        browser.close()
                    except:
                        pass
                    return None
                    
        except ImportError:
            logger.debug("[PLAYWRIGHT] playwright не установлен")
            return None
        except Exception as e:
            logger.warning(f"[PLAYWRIGHT] Ошибка для car_id={car_id}: {e}")
            return None

    def _fetch_detail_api(self, sku_id: str, city_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Получает детальные данные через внутренний JSON endpoint страницы detail.
        Это основной и самый дешёвый путь для sku_id.
        """
        detail_url = "https://www.dongchedi.com/motor/pc/sh/detail/major"
        params = {"sku_id": str(sku_id)}
        if city_name:
            params["city_name"] = city_name

        headers = dict(self.headers)
        headers.update(
            {
                "Accept": "application/json, text/plain, */*",
                "Referer": f"https://www.dongchedi.com/usedcar/{sku_id}",
            }
        )

        try:
            response = requests.get(detail_url, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            logger.debug(f"[DETAIL API] Ошибка запроса для sku_id={sku_id}: {e}")
            return None

        if payload.get("status") not in (0, 200):
            logger.warning(f"[DETAIL API] Нестандартный status для sku_id={sku_id}: {payload.get('status')}")
            return None

        sku_detail = payload.get("data")
        if not isinstance(sku_detail, dict):
            logger.warning(f"[DETAIL API] Пустой data payload для sku_id={sku_id}")
            return None

        car_info = sku_detail.get("car_info") or {}
        if not car_info.get("car_id"):
            logger.warning(f"[DETAIL API] car_info.car_id отсутствует для sku_id={sku_id}")
            return None

        result = self._parse_sku_detail(sku_detail, str(sku_id))

        config_overview = sku_detail.get("car_config_overview") or {}
        power_block = config_overview.get("power") or {}
        space_block = config_overview.get("space") or {}
        manipulation_block = config_overview.get("manipulation") or {}

        horsepower = normalize_power_value(power_block.get("horsepower"))
        if horsepower is not None:
            result["power"] = horsepower

        acceleration = parse_float_value(power_block.get("acceleration_time"))
        if acceleration is not None:
            result["acceleration"] = acceleration

        for field in ("length", "width", "height", "wheelbase"):
            parsed_value = parse_int_value(space_block.get(field))
            if parsed_value is not None:
                result[field] = parsed_value

        if not result.get("drive_type") and manipulation_block.get("driver_form"):
            result["drive_type"] = manipulation_block.get("driver_form")

        capacity = power_block.get("capacity")
        if capacity:
            result["engine_volume"] = str(capacity)

        logger.info(
            f"[DETAIL API] Успешно получены данные для sku_id={sku_id}: "
            f"images={result.get('image_count', 0)}, reg={result.get('first_registration_time')}"
        )
        return result

    def _finalize_detail_car_info(self, car_info: Dict[str, Any]) -> DongchediCar:
        from converters import decode_dongchedi_detail

        for key in ["title", "car_name", "sh_price"]:
            if car_info.get(key):
                car_info[key] = decode_dongchedi_detail(car_info[key])

        if car_info.get("city"):
            car_info["city"] = decode_dongchedi_detail(car_info["city"])
        if car_info.get("car_source_city_name"):
            car_info["car_source_city_name"] = decode_dongchedi_detail(car_info["car_source_city_name"])

        for key in ["tags", "tags_v2"]:
            if car_info.get(key) is not None and not isinstance(car_info[key], str):
                import json
                try:
                    car_info[key] = json.dumps(car_info[key])
                except Exception:
                    car_info[key] = str(car_info[key])

        if car_info.get("sh_price"):
            price_value = parse_float_value(car_info["sh_price"])
            if price_value is not None:
                car_info["price"] = price_value

        if car_info.get("shop_id"):
            car_info["shop_id"] = parse_int_value(car_info["shop_id"])

        if "car_mileage" in car_info and car_info["car_mileage"] is not None:
            mileage_km, m_meta = normalize_mileage(
                car_info["car_mileage"],
                year_hint=car_info.get("car_year"),
                source="dongchedi:detail",
            )
            if mileage_km is not None:
                car_info["mileage"] = mileage_km
            if m_meta.get("warnings"):
                logger.debug(f"mileage warnings(detail) raw={car_info.get('car_mileage')} meta={m_meta}")

        return DongchediCar(**{k: v for k, v in car_info.items() if k in DongchediCar.__fields__})

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
                cars_list = data['data']['search_sh_sku_info_list']
                logger.info(f"Received {len(cars_list) if isinstance(cars_list, list) else 'non-list'} items in search_sh_sku_info_list for page {page}")
                for car_data in cars_list:
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

                        # Копируем значения из одних полей в другие для совместимости
                        if 'car_year' in filtered_car_data and filtered_car_data['car_year'] is not None:
                            filtered_car_data['year'] = filtered_car_data['car_year']

                        if 'car_mileage' in filtered_car_data and filtered_car_data['car_mileage'] is not None:
                            mileage_km, m_meta = normalize_mileage(
                                filtered_car_data['car_mileage'],
                                year_hint=filtered_car_data.get('car_year'),
                                source="dongchedi:list",
                            )
                            if mileage_km is not None:
                                filtered_car_data['mileage'] = mileage_km
                            if m_meta.get('warnings'):
                                logger.debug(f"mileage warnings(list) raw={filtered_car_data.get('car_mileage')} meta={m_meta}")

                        if 'car_source_city_name' in filtered_car_data and filtered_car_data['car_source_city_name'] is not None:
                            from converters import decode_dongchedi_detail
                            filtered_car_data['city'] = decode_dongchedi_detail(filtered_car_data['car_source_city_name'])

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

                        # Ensure price is properly set from sh_price (convert to float)
                        if 'sh_price' in filtered_car_data and filtered_car_data['sh_price'] is not None:
                            # Convert price to a numeric value if it's a string with units
                            price_value = parse_float_value(filtered_car_data['sh_price'])
                            if price_value is not None:
                                filtered_car_data['price'] = price_value
                        
                        # Convert shop_id to int
                        if 'shop_id' in filtered_car_data and filtered_car_data['shop_id'] is not None:
                            filtered_car_data['shop_id'] = parse_int_value(filtered_car_data['shop_id'])

                        # Convert sku_id to string (API returns int, but model expects str)
                        if 'sku_id' in filtered_car_data and filtered_car_data['sku_id'] is not None:
                            filtered_car_data['sku_id'] = str(filtered_car_data['sku_id'])

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
                    except Exception as e:
                        logger.warning(f"Failed to parse car data on page {page}: {e}. Car data keys: {list(car_data.keys()) if isinstance(car_data, dict) else type(car_data)}")
                        logger.debug(f"Filtered car data keys: {list(filtered_car_data.keys())}")
                        continue

            # Если данных нет или список пуст, считаем что страницы не существует
            if not cars:
                logger.warning(f"No cars found on dongchedi page {page}. Response data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                if isinstance(data, dict) and 'data' in data:
                    logger.warning(f"Response data structure: {list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data'])}")
                    if 'search_sh_sku_info_list' in data['data']:
                        cars_list = data['data']['search_sh_sku_info_list']
                        logger.warning(f"search_sh_sku_info_list length: {len(cars_list) if isinstance(cars_list, list) else 'not a list'}")
                        if isinstance(cars_list, list) and len(cars_list) > 0:
                            logger.warning(f"First car item type: {type(cars_list[0])}, keys: {list(cars_list[0].keys()) if isinstance(cars_list[0], dict) else 'not a dict'}")
                            # Логируем первые несколько полей первой машины для отладки
                            if isinstance(cars_list[0], dict):
                                sample_keys = list(cars_list[0].keys())[:10]
                                logger.warning(f"Sample car data (first 10 keys): {[(k, type(cars_list[0][k]).__name__ if k in cars_list[0] else None) for k in sample_keys]}")
                        elif isinstance(cars_list, list) and len(cars_list) == 0:
                            logger.warning(f"search_sh_sku_info_list is an empty list!")
                        else:
                            logger.warning(f"search_sh_sku_info_list is not a list: {type(cars_list)}")
                    else:
                        logger.warning(f"'search_sh_sku_info_list' key not found in data['data']")
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
            logger.error(f"Error fetching dongchedi page {page}: {e}", exc_info=True)
            return DongchediApiResponse(
                data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                message=f"Ошибка при получении данных: {str(e)}",
                status=500
            )

    def fetch_car_detail(self, car_id: str):
        """
        Парсит детальную информацию о машине по sku_id.
        Сначала пробует внутренний detail JSON API, затем браузерные fallback.
        Возвращает (DongchediCar | None, meta: dict)
        """
        logger.info(f"fetch_car_detail: ВХОД в функцию для car_id={car_id}")
        import datetime
        import uuid

        api_data = self._fetch_detail_api(car_id)
        if api_data:
            current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            car_info = {
                "uuid": str(uuid.uuid4()),
                "link": f"https://www.dongchedi.com/usedcar/{car_id}",
                "car_id": car_id,
                "sku_id": car_id,
                "source": "dongchedi",
                "is_available": True,
                "created_at": current_time,
                "updated_at": current_time,
                "has_details": bool(
                    api_data.get("power")
                    or api_data.get("image_gallery")
                    or api_data.get("first_registration_time")
                ),
                "is_banned": False,
            }
            car_info.update(api_data)
            try:
                car_obj = self._finalize_detail_car_info(car_info)
            except Exception as e:
                return None, {"is_available": False, "error": str(e), "status": 500}
            return car_obj, {"is_available": True, "status": 200}

        import time
        import random
        import json
        import shutil
        import tempfile
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
        car_info = None
        is_available = False
        try:
            chrome_bin = os.environ.get("CHROME_BIN")
            if chrome_bin:
                chrome_options.binary_location = chrome_bin
            driver_path = os.environ.get("CHROMEDRIVER_PATH")
            if driver_path:
                driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            # Устанавливаем таймауты для драйвера
            driver.set_page_load_timeout(60)  # 60 секунд на загрузку страницы
            driver.implicitly_wait(10)  # 10 секунд неявного ожидания

            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.get(url)
            time.sleep(random.uniform(3, 5))  # Увеличено время ожидания
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                pass
            
            # Ждем загрузки скрипта с __NEXT_DATA__
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.getElementById('__NEXT_DATA__') !== null || document.body.innerHTML.includes('__NEXT_DATA__')")
                )
                logger.info(f"fetch_car_detail: Скрипт __NEXT_DATA__ загружен для car_id={car_id}")
            except TimeoutException:
                logger.warning(f"fetch_car_detail: Скрипт __NEXT_DATA__ не загрузился в течение 10 секунд для car_id={car_id}")
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Увеличено время ожидания
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)  # Увеличено время ожидания
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
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
                "price": None,  # float - цена в wan юаней
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
                "shop_id": None,  # int - ID магазина
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
                "power": None,  # int - мощность в л.с.
                "torque": None,  # float - крутящий момент в Н·м
                "acceleration": None,  # float - разгон до 100 км/ч в секундах
                "max_speed": None,  # int - максимальная скорость в км/ч
                "fuel_consumption": None,  # float - расход топлива л/100км
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
                "first_registration_time": None,
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
                "fuel_tank_volume": None,
                # Флаг блокировки
                "is_banned": False  # True если источник заблокирован и не удалось получить image_gallery/first_registration_time
            }
            
            # Проверяем, не заблокирована ли страница (после создания car_info)
            page_blocked = False
            if page_source and ('验证' in page_source or 'captcha' in page_source.lower() or 'blocked' in page_source.lower() or 'access denied' in page_source.lower()):
                logger.warning(f"fetch_car_detail: Страница может быть заблокирована для car_id={car_id}, пробуем мобильную версию")
                page_blocked = True
                # Пробуем мобильную версию как fallback
                mobile_data = self._fetch_mobile_version(car_id)
                if mobile_data:
                    # Обновляем car_info данными из мобильной версии
                    if 'image' in mobile_data:
                        car_info['image'] = mobile_data['image']
                    if 'image_gallery' in mobile_data:
                        car_info['image_gallery'] = mobile_data['image_gallery']
                        car_info['image_count'] = mobile_data.get('image_count', 0)
                    if 'first_registration_time' in mobile_data:
                        car_info['first_registration_time'] = mobile_data['first_registration_time']
                    
                    logger.info(f"fetch_car_detail: [MOBILE FALLBACK] Обновлен car_info из мобильной версии (страница заблокирована) для car_id={car_id}")
                else:
                    logger.warning(f"fetch_car_detail: [MOBILE FALLBACK] Не удалось получить данные из мобильной версии для car_id={car_id}")
                    # Если мобильная версия не работает, устанавливаем is_banned
                    car_info['is_banned'] = True
            
            # Ищем скрипт с __NEXT_DATA__ по id
            script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
            json_data_found = False
            
            # Если страница была заблокирована и мы получили данные из мобильной версии, пропускаем парсинг JSON
            if page_blocked and (car_info.get('image_gallery') or car_info.get('first_registration_time')):
                logger.info(f"fetch_car_detail: Пропускаем парсинг JSON, так как данные уже получены из мобильной версии для car_id={car_id}")
                json_data_found = True  # Помечаем, что данные получены
            
            logger.info(f"fetch_car_detail: script_tag найден для car_id={car_id}: {script_tag is not None}")
            
            # Альтернативный поиск по содержимому, если не нашли по id
            if not script_tag:
                logger.info(f"fetch_car_detail: Пробуем альтернативный поиск скрипта по содержимому для car_id={car_id}")
                script_tags = soup.find_all('script')
                logger.info(f"fetch_car_detail: Найдено всего script тегов для car_id={car_id}: {len(script_tags)}")
                
                # Диагностика: выводим информацию о каждом script теге
                for idx, script in enumerate(script_tags):
                    script_id = script.get('id', 'нет id')
                    script_type = script.get('type', 'нет type')
                    script_src = script.get('src', 'нет src')
                    has_content = script.string is not None
                    content_preview = (script.string[:200] if script.string else 'нет содержимого')[:200]
                    contains_next_data = '__NEXT_DATA__' in (script.string or '')
                    logger.info(f"fetch_car_detail: Script #{idx+1} для car_id={car_id}: id={script_id}, type={script_type}, src={script_src}, has_content={has_content}, contains_next_data={contains_next_data}, preview={content_preview}")
                    
                    if script.string and '__NEXT_DATA__' in script.string:
                        script_tag = script
                        logger.info(f"fetch_car_detail: Найден скрипт с __NEXT_DATA__ по содержимому для car_id={car_id}")
                        break
                
                # Если не нашли по строке, пробуем поискать по тексту через get_text()
                if not script_tag:
                    logger.info(f"fetch_car_detail: Не нашли скрипт по строке, пробуем через get_text() для car_id={car_id}")
                    for script in script_tags:
                        script_text = script.get_text()
                        if '__NEXT_DATA__' in script_text:
                            script_tag = script
                            logger.info(f"fetch_car_detail: Найден скрипт с __NEXT_DATA__ через get_text() для car_id={car_id}")
                            break
            
            # Проверяем, есть ли вообще __NEXT_DATA__ в HTML
            if '__NEXT_DATA__' not in page_source:
                logger.warning(f"fetch_car_detail: __NEXT_DATA__ НЕ найден в HTML страницы для car_id={car_id}, размер HTML: {len(page_source)} байт")
            
            # Пытаемся получить содержимое скрипта разными способами
            script_content = None
            if script_tag:
                if script_tag.string:
                    script_content = script_tag.string
                    logger.info(f"fetch_car_detail: script_tag.string существует для car_id={car_id}, длина: {len(script_content)}")
                elif script_tag.contents:
                    script_content = ''.join(str(c) for c in script_tag.contents if isinstance(c, str))
                    logger.info(f"fetch_car_detail: script_content получен из contents для car_id={car_id}, длина: {len(script_content) if script_content else 0}")
                else:
                    script_text = script_tag.get_text()
                    if script_text:
                        script_content = script_text
                        logger.info(f"fetch_car_detail: script_content получен через get_text() для car_id={car_id}, длина: {len(script_content)}")
            
            if script_tag and script_content:
                try:
                    json_data = json.loads(script_content)
                    logger.info(f"fetch_car_detail: JSON успешно распарсен для car_id={car_id}")
                    if 'props' in json_data and 'pageProps' in json_data['props']:
                        page_props = json_data['props']['pageProps']
                        logger.info(f"fetch_car_detail: pageProps найден для car_id={car_id}, ключи: {list(page_props.keys())[:10]}")
                        if 'skuDetail' in page_props:
                            sku_detail = page_props['skuDetail']
                            logger.info(f"fetch_car_detail: skuDetail найден для car_id={car_id}, ключи: {list(sku_detail.keys())[:15] if isinstance(sku_detail, dict) else 'not a dict'}")
                            
                            # Парсим галерею изображений
                            head_images = sku_detail.get('head_images', [])
                            if head_images and isinstance(head_images, list):
                                # Сохраняем первую картинку в image
                                car_info['image'] = head_images[0] if len(head_images) > 0 else ''
                                # Сохраняем все картинки через пробел
                                car_info['image_gallery'] = ' '.join(head_images)
                                car_info['image_count'] = len(head_images)
                                logger.info(f"fetch_car_detail: Найдена image_gallery для car_id={car_id}: {len(head_images)} изображений")
                            else:
                                car_info['image'] = sku_detail.get('image', '')
                                logger.debug(f"fetch_car_detail: head_images не найден или пуст для car_id={car_id}, используем image={car_info['image']}")
                            
                            # Парсим дополнительные данные
                            shop_info = sku_detail.get('shop_info', {})
                            other_params = sku_detail.get('other_params', [])
                            
                            # Извлекаем информацию о владельцах, пробеге и т.д. из other_params
                            logger.info(f"fetch_car_detail: other_params для car_id={car_id}: {[(p.get('name'), p.get('value')) for p in other_params]}")
                            
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
                                elif param_name in ('上牌时间', '首次上牌', '首次上牌时间'):
                                    logger.info(f"fetch_car_detail: Найден параметр даты регистрации для car_id={car_id}: {param_name}={param_value}")
                                    normalized_date = normalize_first_registration_date(param_value)
                                    if normalized_date:
                                        car_info['first_registration_time'] = normalized_date
                                        logger.info(f"fetch_car_detail: first_registration_time нормализован для car_id={car_id}: {param_value} -> {normalized_date}")
                                    else:
                                        logger.warning(f"fetch_car_detail: Не удалось нормализовать first_registration_time для car_id={car_id}: {param_value}")
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
                                    # acceleration - float
                                    accel_value = new_energy.get('acceleration_time', '')
                                    if accel_value:
                                        car_info['acceleration'] = parse_float_value(accel_value)
                                    car_info['fuel_type'] = new_energy.get('fuel_form', '')
                                    car_info['transmission_type'] = new_energy.get('gearbox_description', '')
                                    horsepower_value = new_energy.get('horsepower')
                                    if horsepower_value is not None:
                                        # Проверяем, что значение содержит цифры
                                        horsepower_str = str(horsepower_value).strip()
                                        if any(c.isdigit() for c in horsepower_str):
                                            normalized_hp = normalize_power_value(horsepower_value)
                                            if normalized_hp:
                                                car_info['power'] = normalized_hp  # уже int
                                            # Если нет цифр или normalize_power_value вернул None, не устанавливаем power
                                
                                # Размеры из space
                                space = car_config.get('space', {})
                                if space:
                                    car_info['height'] = parse_int_value(space.get('height'))
                                    car_info['length'] = parse_int_value(space.get('length'))
                                    car_info['width'] = parse_int_value(space.get('width'))
                                    car_info['wheelbase'] = parse_int_value(space.get('wheelbase'))
                            
                            # Парсим engine_volume и engine_volume_ml из разных источников
                            # Примечание: для электромобилей и некоторых страниц объявлений объема может не быть
                            engine_volume = sku_detail.get('car_info', {}).get('engine_volume')
                            engine_volume_ml = None
                            
                            if not engine_volume or (isinstance(engine_volume, str) and not engine_volume.strip()):
                                # Если не нашли в car_info, ищем в rawData.car_info[0].info
                                try:
                                    raw_data = json_data.get('props', {}).get('pageProps', {}).get('rawData', {})
                                    car_info_list = raw_data.get('car_info', [])
                                    if car_info_list and len(car_info_list) > 0:
                                        info_dict = car_info_list[0].get('info', {})
                                        if info_dict:
                                            # Пробуем capacity_l (в литрах, например "2.0")
                                            capacity_l = info_dict.get('capacity_l', {})
                                            if isinstance(capacity_l, dict) and capacity_l.get('value'):
                                                engine_volume = str(capacity_l.get('value')).strip()
                                            # Пробуем cylinder_volume_ml (в миллилитрах, например "1999")
                                            cylinder_volume_ml = info_dict.get('cylinder_volume_ml', {})
                                            if isinstance(cylinder_volume_ml, dict) and cylinder_volume_ml.get('value'):
                                                ml_value = str(cylinder_volume_ml.get('value')).strip()
                                                engine_volume_ml = ml_value
                                                # Если engine_volume еще не найден, конвертируем из мл в литры
                                                if not engine_volume or (isinstance(engine_volume, str) and not engine_volume.strip()):
                                                    try:
                                                        ml_float = float(ml_value)
                                                        engine_volume = str(ml_float / 1000.0)
                                                    except (ValueError, TypeError):
                                                        pass
                                except (KeyError, IndexError, AttributeError):
                                    pass
                            
                            # Используем найденное значение или оставляем None
                            # None - это нормально для электромобилей и некоторых страниц объявлений
                            if not engine_volume or (isinstance(engine_volume, str) and not engine_volume.strip()):
                                engine_volume = None
                            if not engine_volume_ml or (isinstance(engine_volume_ml, str) and not engine_volume_ml.strip()):
                                engine_volume_ml = None
                            
                            # Логируем найденные значения для отладки
                            if engine_volume_ml:
                                logger.info(f"fetch_car_detail: Найден engine_volume_ml={engine_volume_ml} для car_id={car_id}")
                            if car_info.get('first_registration_time'):
                                logger.info(f"fetch_car_detail: Найден first_registration_time={car_info.get('first_registration_time')} для car_id={car_id}")
                            else:
                                logger.debug(f"fetch_car_detail: first_registration_time не найден для car_id={car_id}")
                            if car_info.get('image_gallery'):
                                logger.info(f"fetch_car_detail: image_gallery заполнен для car_id={car_id}, количество изображений: {car_info.get('image_count', 0)}")
                            else:
                                logger.debug(f"fetch_car_detail: image_gallery не заполнен для car_id={car_id}")
                            
                            # Парсим пробег из разных источников
                            mileage_km = None
                            mileage_raw = sku_detail.get('car_info', {}).get('mileage', '')
                            
                            # Метод 1: из car_info.mileage
                            if mileage_raw:
                                m = re.search(r'(\d+\.?\d*)', str(mileage_raw))
                                if m:
                                    val = float(m.group(1))
                                    if '万' in str(mileage_raw):
                                        mileage_km = int(val * 10000)
                                    elif val < 1000:  # вероятно в 万公里
                                        mileage_km = int(val * 10000)
                                    else:
                                        mileage_km = int(val)
                            
                            # Метод 2: из important_text (формат: "2023年上牌 | 4万公里 | 郑州车源")
                            if not mileage_km:
                                important_text = sku_detail.get('important_text', '')
                                if important_text:
                                    m = re.search(r'(\d+\.?\d*)\s*万公里', important_text)
                                    if m:
                                        mileage_km = int(float(m.group(1)) * 10000)
                                        logger.info(f"fetch_car_detail: Пробег из important_text для car_id={car_id}: {m.group(0)} -> {mileage_km}км")
                            
                            # Метод 3: из other_params
                            if not mileage_km:
                                for param in other_params:
                                    param_name = param.get('name', '') or param.get('key', '')
                                    param_value = param.get('value', '')
                                    if '里程' in param_name or '公里' in param_name:
                                        m = re.search(r'(\d+\.?\d*)', str(param_value))
                                        if m:
                                            val = float(m.group(1))
                                            if '万' in str(param_value) or val < 1000:
                                                mileage_km = int(val * 10000)
                                            else:
                                                mileage_km = int(val)
                                            logger.info(f"fetch_car_detail: Пробег из other_params для car_id={car_id}: {param_value} -> {mileage_km}км")
                                            break
                            
                            car_info.update({
                                'title': sku_detail.get('title', ''),
                                'sh_price': sku_detail.get('sh_price', ''),
                                'car_mileage': str(mileage_km) if mileage_km else '',
                                'mileage': mileage_km,  # int в км
                                'car_year': sku_detail.get('car_info', {}).get('year', ''),
                                'year': sku_detail.get('car_info', {}).get('year', ''),
                                'brand_name': sku_detail.get('car_info', {}).get('brand_name', ''),
                                'series_name': sku_detail.get('car_info', {}).get('series_name', ''),
                                'car_name': sku_detail.get('car_info', {}).get('car_name', ''),
                                'shop_id': shop_info.get('shop_id', ''),
                                'brand_id': sku_detail.get('car_info', {}).get('brand_id', 0),
                                'series_id': sku_detail.get('car_info', {}).get('series_id', 0),
                                'car_id': str(sku_detail.get('car_info', {}).get('car_id', '')) if sku_detail.get('car_info', {}).get('car_id') else None,
                                'sku_id': str(sku_detail.get('sku_id', '')) if sku_detail.get('sku_id') else car_id,  # sku_id важен для URL
                                'car_source_city_name': sku_detail.get('car_info', {}).get('city', ''),
                                'city': sku_detail.get('car_info', {}).get('city', ''),
                                'description': sku_detail.get('sh_car_desc', ''),
                                'color': sku_detail.get('car_info', {}).get('color', ''),
                                'transmission': sku_detail.get('car_info', {}).get('transmission', ''),
                                'fuel_type': sku_detail.get('car_info', {}).get('fuel_type', '') or car_info.get('fuel_type', ''),
                                'engine_volume': engine_volume if engine_volume else (car_info.get('engine_volume') or None),
                                'engine_volume_ml': engine_volume_ml if engine_volume_ml else (car_info.get('engine_volume_ml') or None),
                                'body_type': sku_detail.get('car_info', {}).get('body_type', ''),
                                'drive_type': sku_detail.get('car_info', {}).get('drive_type', '') or car_info.get('drive_type', ''),
                                'condition': sku_detail.get('car_info', {}).get('condition', ''),
                            })
                            json_data_found = True
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"fetch_car_detail: Ошибка при парсинге JSON для car_id={car_id}: {type(e).__name__}: {e}")
                    pass
            if not json_data_found:
                logger.warning(f"fetch_car_detail: json_data_found=False для car_id={car_id}, пробуем мобильную версию как fallback")
                
                # FALLBACK 1: Пробуем мобильную версию через requests
                mobile_data = self._fetch_mobile_version(car_id)
                if mobile_data:
                    # Обновляем car_info данными из мобильной версии
                    if 'image_gallery' in mobile_data and not car_info.get('image_gallery'):
                        car_info['image'] = mobile_data.get('image', car_info.get('image'))
                        car_info['image_gallery'] = mobile_data.get('image_gallery')
                        car_info['image_count'] = mobile_data.get('image_count', 0)
                        logger.info(f"fetch_car_detail: [MOBILE FALLBACK] Обновлена image_gallery для car_id={car_id}")
                    
                    if 'first_registration_time' in mobile_data and not car_info.get('first_registration_time'):
                        car_info['first_registration_time'] = mobile_data['first_registration_time']
                        logger.info(f"fetch_car_detail: [MOBILE FALLBACK] Обновлена first_registration_time для car_id={car_id}")
                    
                    # Если получили данные из мобильной версии, можно пропустить HTML fallback для этих полей
                    if mobile_data.get('image_gallery') or mobile_data.get('first_registration_time'):
                        logger.info(f"fetch_car_detail: [MOBILE FALLBACK] Данные получены, но продолжаем HTML fallback для других полей для car_id={car_id}")
                    else:
                        logger.warning(f"fetch_car_detail: [MOBILE FALLBACK] Данные не получены, используем HTML fallback для car_id={car_id}")
                else:
                    logger.warning(f"fetch_car_detail: [MOBILE FALLBACK] Не удалось получить данные, используем HTML fallback для car_id={car_id}")
                    # Если мобильная версия не работает, помечаем как заблокированную
                    if not car_info.get('image_gallery') and not car_info.get('first_registration_time'):
                        car_info['is_banned'] = True
                
                # FALLBACK 2: Парсинг из HTML (если мобильная версия не помогла или для других полей)
                logger.warning(f"fetch_car_detail: Используем fallback парсинг HTML для car_id={car_id}")
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
                
                # УЛУЧШЕННЫЙ FALLBACK: Извлечение image_gallery и first_registration_time из HTML
                logger.info(f"fetch_car_detail: Пробуем извлечь image_gallery и first_registration_time из HTML для car_id={car_id}")
                
                # Извлекаем изображения из HTML
                image_selectors = [
                    'img[src*="car"]',
                    'img[src*="dongchedi"]',
                    'img[class*="car"]',
                    'img[class*="image"]',
                    '.car-image img',
                    '.image-gallery img',
                    '[class*="gallery"] img',
                    '[class*="photo"] img',
                ]
                images_found = []
                for selector in image_selectors:
                    img_elements = soup.select(selector)
                    for img in img_elements:
                        src = img.get('src', '') or img.get('data-src', '') or img.get('data-lazy-src', '')
                        if src and 'http' in src and src not in images_found:
                            images_found.append(src)
                            logger.info(f"fetch_car_detail: Найдено изображение для car_id={car_id}: {src[:100]}")
                
                if images_found:
                    car_info['image'] = images_found[0] if images_found else ''
                    car_info['image_gallery'] = ' '.join(images_found)
                    car_info['image_count'] = len(images_found)
                    logger.info(f"fetch_car_detail: [FALLBACK] Извлечена image_gallery из HTML для car_id={car_id}: {len(images_found)} изображений")
                else:
                    logger.info(f"fetch_car_detail: [FALLBACK] Изображения не найдены в HTML для car_id={car_id} (проверено {len(image_selectors)} селекторов)")
                
                # Извлекаем first_registration_time из текста страницы
                page_text = soup.get_text()
                
                # Паттерны для поиска даты регистрации
                registration_patterns = [
                    r'上牌时间[：:]\s*(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2})',
                    r'首次上牌[：:]\s*(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2})',
                    r'首次上牌时间[：:]\s*(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2})',
                    r'上牌[：:]\s*(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2})',
                    r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}).*上牌',
                    r'注册时间[：:]\s*(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2})',
                ]
                
                for pattern in registration_patterns:
                    match = re.search(pattern, page_text)
                    if match:
                        date_str = match.group(1)
                        logger.info(f"fetch_car_detail: Найдена дата регистрации в тексте для car_id={car_id}: {date_str}")
                        normalized_date = normalize_first_registration_date(date_str)
                        if normalized_date:
                            car_info['first_registration_time'] = normalized_date
                            logger.info(f"fetch_car_detail: first_registration_time нормализован из HTML для car_id={car_id}: {date_str} -> {normalized_date}")
                            break
                
                # Также ищем в meta тегах
                meta_tags = soup.find_all('meta')
                for meta in meta_tags:
                    content = meta.get('content', '')
                    if content and any(keyword in content for keyword in ['上牌', '注册', '首次']):
                        date_match = re.search(r'(\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2})', content)
                        if date_match:
                            date_str = date_match.group(1)
                            normalized_date = normalize_first_registration_date(date_str)
                            if normalized_date:
                                car_info['first_registration_time'] = normalized_date
                                logger.info(f"fetch_car_detail: first_registration_time найден в meta для car_id={car_id}: {normalized_date}")
                                break
                
                # Логируем финальный статус извлеченных данных из fallback
                if car_info.get('image_gallery'):
                    logger.info(f"fetch_car_detail: [FALLBACK] image_gallery заполнен для car_id={car_id}, количество изображений: {car_info.get('image_count', 0)}")
                else:
                    logger.debug(f"fetch_car_detail: [FALLBACK] image_gallery не заполнен для car_id={car_id}")
                
                if car_info.get('first_registration_time'):
                    logger.info(f"fetch_car_detail: [FALLBACK] first_registration_time заполнен для car_id={car_id}: {car_info.get('first_registration_time')}")
                else:
                    logger.info(f"fetch_car_detail: [FALLBACK] first_registration_time не заполнен для car_id={car_id} (проверено {len(registration_patterns)} паттернов в тексте и {len(meta_tags)} meta тегов)")
            
            page_text = soup.get_text()
            # Индикаторы того, что машина ПРОДАНА (недоступна)
            # Убрали "sale" - это может означать "for sale" (продаётся), а не "продано"
            unavailable_indicators = [
                "已售", "售出", "已卖出", "下架", "已下架", "已成交",
                "sold out", "已售出"
            ]
            # По умолчанию считаем машину доступной
            # Меняем на False только если явно нашли индикатор продажи
            is_available = True
            page_text_lower = page_text.lower()
            for indicator in unavailable_indicators:
                if indicator.lower() in page_text_lower:
                    is_available = False
                    logger.debug(f"dongchedi car_id={car_id}: найден индикатор недоступности '{indicator}'")
                    break
            car_info['is_available'] = is_available
            
            # Устанавливаем is_banned, если страница была заблокирована и не удалось получить критичные данные
            if page_blocked:
                # Проверяем, получили ли мы критичные данные (image_gallery или first_registration_time)
                has_critical_data = car_info.get('image_gallery') or car_info.get('first_registration_time')
                if not has_critical_data:
                    car_info['is_banned'] = True
                    logger.warning(f"fetch_car_detail: Источник заблокирован для car_id={car_id}: не удалось получить image_gallery или first_registration_time")
                else:
                    # Fallback сработал - критичные данные получены, блокировка не помешала
                    car_info['is_banned'] = False
                    logger.info(f"fetch_car_detail: Источник заблокирован для car_id={car_id}, но fallback успешно получил критичные данные")
            
            # Если __NEXT_DATA__ не найден и мобильная версия не помогла, и нет критичных данных
            if not json_data_found and not car_info.get('image_gallery') and not car_info.get('first_registration_time'):
                car_info['is_banned'] = True
                logger.warning(f"fetch_car_detail: Источник заблокирован для car_id={car_id}: __NEXT_DATA__ не найден и критичные данные не получены")
            
            # Инициализируем is_banned если не установлен
            if 'is_banned' not in car_info:
                car_info['is_banned'] = False
        except Exception as e:
            # В случае ошибки при парсинге пробуем мобильную версию как fallback
            logger.error(f"Ошибка при парсинге страницы dongchedi car_id={car_id}: {e}")
            
            # FALLBACK: Пробуем мобильную версию через requests
            try:
                mobile_data = self._fetch_mobile_version(car_id)
                if mobile_data:
                    # Создаем минимальный car_info из мобильных данных
                    import datetime
                    import uuid
                    current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    car_info = {
                        "uuid": str(uuid.uuid4()),
                        "car_id": car_id,
                        "sku_id": car_id,
                        "source": "dongchedi",
                        "is_available": True,
                        "created_at": current_time,
                        "updated_at": current_time,
                        "link": f"https://m.dongchedi.com/usedcar/{car_id}",
                    }
                    
                    # Добавляем данные из мобильной версии
                    if 'image' in mobile_data:
                        car_info['image'] = mobile_data['image']
                    if 'image_gallery' in mobile_data:
                        car_info['image_gallery'] = mobile_data['image_gallery']
                        car_info['image_count'] = mobile_data.get('image_count', 0)
                    if 'first_registration_time' in mobile_data:
                        car_info['first_registration_time'] = mobile_data['first_registration_time']
                    
                    logger.info(f"fetch_car_detail: [MOBILE FALLBACK] Создан car_info из мобильной версии для car_id={car_id}")
                else:
                    # Если мобильная версия тоже не помогла, возвращаем None
                    if 'soup' not in locals() or soup is None:
                        soup = None
                    car_info = None
            except Exception as fallback_error:
                logger.error(f"Ошибка в мобильном fallback для car_id={car_id}: {fallback_error}")
                # Гарантируем, что soup инициализирован
                if 'soup' not in locals() or soup is None:
                    soup = None
                car_info = None
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
            # Освобождаем память от page_source (soup еще нужен для парсинга, если он был создан)
            if page_source:
                del page_source
            # НЕ удаляем soup здесь, так как он может использоваться после finally
            # soup будет удален после использования
        
        # Проверяем, что soup был успешно создан и данные распарсены
        if car_info is None:
            # Пробуем Playwright как последний fallback
            logger.info(f"fetch_car_detail: Selenium не сработал, пробуем Playwright для car_id={car_id}")
            playwright_data = self._fetch_with_playwright(car_id)
            if playwright_data:
                # Создаем базовый car_info и обновляем данными из Playwright
                import datetime
                import uuid
                current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                car_info = {
                    "uuid": str(uuid.uuid4()),
                    "link": f"https://www.dongchedi.com/usedcar/{car_id}",
                    "car_id": car_id,
                    "sku_id": car_id,
                    "source": "dongchedi",
                    "is_available": True,
                    "created_at": current_time,
                    "updated_at": current_time,
                    "has_details": True,
                    "is_banned": False,
                }
                car_info.update(playwright_data)
                logger.info(f"fetch_car_detail: [PLAYWRIGHT] Успешно получены данные для car_id={car_id}")
            else:
                return None, {"is_available": False, "error": "Failed to load or parse page", "status": 500}
        
        try:
            car_obj = self._finalize_detail_car_info(car_info)
        except Exception as e:
            # Освобождаем память перед возвратом ошибки
            if 'soup' in locals() and soup:
                try:
                    soup.decompose()
                    del soup
                except:
                    pass
            return None, {"is_available": False, "error": str(e), "status": 500}
        
        # Освобождаем память перед возвратом результата
        if 'soup' in locals() and soup:
            try:
                soup.decompose()
                del soup
            except:
                pass
        
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
        logger.info(f"fetch_car_specifications: ВХОД в функцию для car_id={car_id}")
        import time
        import random
        import json
        import os
        import shutil
        import tempfile
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
        # Дополнительные опции для стабильности
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        # Добавляем уникальный user-data-dir для избежания конфликтов
        temp_dir = None
        driver = None
        soup = None
        page_source = None
        try:
            temp_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            ]
            chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")
            chrome_bin = os.environ.get("CHROME_BIN")
            if chrome_bin:
                chrome_options.binary_location = chrome_bin
            driver_path = os.environ.get("CHROMEDRIVER_PATH")
            if driver_path:
                driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
            # Устанавливаем таймауты для драйвера
            driver.set_page_load_timeout(60)  # 60 секунд на загрузку страницы
            driver.implicitly_wait(10)  # 10 секунд неявного ожидания
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Обертка для безопасной работы с driver
            def safe_driver_operation(operation, description="", check_session=True):
                """Безопасное выполнение операции с driver"""
                try:
                    if driver is None:
                        raise WebDriverException("Driver is None")
                    # Проверяем что driver все еще активен (только если нужно)
                    if check_session:
                        try:
                            # Используем более легкую проверку - просто пытаемся выполнить операцию
                            # Если сессия потеряна, операция сама выбросит исключение
                            pass
                        except Exception:
                            raise WebDriverException("Driver session is lost")
                    # Выполняем операцию напрямую - она сама выбросит ConnectionRefusedError если сессия потеряна
                    return operation()
                except (ConnectionRefusedError, OSError) as e:
                    # Специальная обработка для ConnectionRefusedError - это означает что Chrome упал
                    logger.error(f"fetch_car_specifications: Chrome процесс упал при {description} для car_id={car_id}: {e}")
                    raise WebDriverException(f"Chrome process crashed: {e}")
                except (WebDriverException, Exception) as e:
                    logger.warning(f"fetch_car_specifications: Ошибка при выполнении {description} для car_id={car_id}: {e}")
                    raise
            
            # Получаем page_source максимально быстро после загрузки, чтобы минимизировать риск потери сессии
            try:
                logger.info(f"fetch_car_specifications: Загрузка страницы для car_id={car_id}")
                safe_driver_operation(lambda: driver.get(url), "driver.get()", check_session=False)
                logger.info(f"fetch_car_specifications: Страница загружена для car_id={car_id}")
            except Exception as e:
                logger.error(f"fetch_car_specifications: Не удалось загрузить страницу для car_id={car_id}: {e}", exc_info=True)
                raise
            
            time.sleep(random.uniform(1, 2))  # Уменьшено время ожидания
            
            try:
                logger.info(f"fetch_car_specifications: Ожидание body для car_id={car_id}")
                safe_driver_operation(
                    lambda: WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    ),
                    "wait for body",
                    check_session=False
                )
                logger.info(f"fetch_car_specifications: Body найден для car_id={car_id}")
            except (TimeoutException, Exception) as e:
                logger.warning(f"fetch_car_specifications: Timeout ожидания body для car_id={car_id}: {e}, продолжаем")
            
            # Получаем page_source СРАЗУ после загрузки, до любых других операций
            # Это минимизирует риск потери сессии между операциями
            try:
                logger.info(f"fetch_car_specifications: Получение page_source для car_id={car_id}")
                page_source = safe_driver_operation(lambda: driver.page_source, "driver.page_source", check_session=False)
                logger.info(f"fetch_car_specifications: page_source получен для car_id={car_id}, размер: {len(page_source)} байт")
            except Exception as e:
                logger.error(f"fetch_car_specifications: Не удалось получить page_source для car_id={car_id}: {e}", exc_info=True)
                raise
            
            # Скролл выполняем ПОСЛЕ получения page_source (это не критично для парсинга)
            try:
                safe_driver_operation(lambda: driver.execute_script("window.scrollTo(0, document.body.scrollHeight);"), "scroll down", check_session=False)
                time.sleep(0.5)
                safe_driver_operation(lambda: driver.execute_script("window.scrollTo(0, 0);"), "scroll up", check_session=False)
                time.sleep(0.5)
            except Exception as e:
                # Скролл не критичен, мы уже получили page_source
                logger.debug(f"fetch_car_specifications: Ошибка при скролле для car_id={car_id}: {e} (не критично, page_source уже получен)")
            logger.info(f"fetch_car_specifications: page_source получен для car_id={car_id}, размер: {len(page_source)} байт")
            soup = BeautifulSoup(page_source, 'html.parser')
            logger.info(f"fetch_car_specifications: BeautifulSoup создан для car_id={car_id}")
            logger.info(f"fetch_car_specifications: HTML загружен для car_id={car_id}, размер: {len(page_source)} байт")
            
            # Парсим технические характеристики из таблицы (внутри try, чтобы можно было удалить soup в finally)
            specs = {}
            
            # Ищем таблицы с параметрами
            table_rows = soup.find_all('div', class_='table_row__yVX1h')
            logger.info(f"Найдено table_rows для car_id={car_id}: {len(table_rows)} строк")
            
            # Если не нашли, пробуем альтернативные селекторы
            if len(table_rows) == 0:
                # Пробуем другие возможные классы
                alt_selectors = [
                    ('div', {'class': re.compile(r'table.*row', re.I)}),
                    ('div', {'class': re.compile(r'row.*table', re.I)}),
                    ('div', {'class': re.compile(r'spec.*row', re.I)}),
                    ('div', {'class': re.compile(r'param.*row', re.I)}),
                ]
                for tag, attrs in alt_selectors:
                    alt_rows = soup.find_all(tag, attrs)
                    if alt_rows:
                        logger.info(f"Найдено альтернативных строк ({tag}, {attrs}): {len(alt_rows)}")
                        table_rows = alt_rows
                        break
            
            # Логируем все найденные label'ы для диагностики
            all_labels = []
            for row in table_rows:
                try:
                    label_elem = row.find('label', class_='cell_label__ZtXlw')
                    if label_elem:
                        all_labels.append(label_elem.get_text().strip())
                except:
                    pass
            if all_labels:
                logger.info(f"Все найденные label'ы на странице specs для car_id={car_id}: {all_labels[:30]}")
            
            for row in table_rows:
                try:
                    label_elem = row.find('label', class_='cell_label__ZtXlw')
                    value_elem = row.find('div', class_='cell_normal__37nRi')
                    
                    if label_elem and value_elem:
                        label = label_elem.get_text().strip()
                        value = value_elem.get_text().strip()
                        
                        # Маппинг китайских названий на английские поля (только поля которые есть в БД)
                        field_mapping = {
                            # === Мощность и динамика ===
                            '最大功率(kW)': 'power',
                            '最大功率': 'power',
                            '最大马力': 'power',
                            '最大马力(Ps)': 'power',
                            '最大扭矩(N·m)': 'torque',
                            '官方百公里加速时间(s)': 'acceleration',
                            '最高车速(km/h)': 'max_speed',
                            '百公里耗电量(kWh/100km)': 'fuel_consumption',
                            'NEDC综合油耗(L/100km)': 'fuel_consumption',
                            'WLTC综合油耗(L/100km)': 'fuel_consumption',
                            '环保标准': 'emission_standard',
                            
                            # === Размеры и кузов ===
                            '长x宽x高(mm)': 'dimensions',
                            '长(mm)': 'length',
                            '宽(mm)': 'width',
                            '高(mm)': 'height',
                            '轴距(mm)': 'wheelbase',
                            '车身结构': 'body_type',
                            '整备质量(kg)': 'curb_weight',
                            '满载质量(kg)': 'gross_weight',
                            '行李舱容积(L)': 'trunk_volume',
                            '行李厢容积(L)': 'trunk_volume',
                            '油箱容积(L)': 'fuel_tank_volume',
                            '座位数(个)': 'seat_count',
                            '座位数': 'seat_count',
                            '车门数(个)': 'door_count',
                            '车门数': 'door_count',
                            
                            # === Двигатель ДВС ===
                            '发动机': 'engine_type',
                            '发动机型号': 'engine_code',
                            '排量(mL)': 'engine_volume_ml',
                            '排量(L)': 'engine_volume',
                            '气缸数(个)': 'cylinder_count',
                            '每缸气门数(个)': 'valve_count',
                            '压缩比': 'compression_ratio',
                            '进气形式': 'turbo_type',
                            
                            # === Электромобили ===
                            '纯电续航里程(km)': 'electric_range',
                            '纯电续航里程(km)CLTC': 'electric_range',
                            '纯电续航里程(km)NEDC': 'electric_range',
                            '纯电续航里程(km)工信部': 'electric_range',
                            '电池容量(kWh)': 'battery_capacity',
                            '充电时间(小时)': 'charging_time',
                            '快充时间(小时)': 'fast_charge_time',
                            '快充接口位置': 'charge_port_type',
                            
                            # === Трансмиссия и привод ===
                            '变速箱': 'transmission_type',
                            '变速箱描述': 'transmission_type',
                            '变速箱类型': 'transmission_type',
                            '挡位数': 'gear_count',
                            '驱动方式': 'drive_type',
                            
                            # === Подвеска и тормоза ===
                            '前悬挂形式': 'front_suspension',
                            '前悬架类型': 'front_suspension',
                            '后悬挂形式': 'rear_suspension',
                            '后悬架类型': 'rear_suspension',
                            '前制动器类型': 'front_brakes',
                            '后制动器类型': 'rear_brakes',
                            '驻车制动类型': 'brake_system',
                            
                            # === Колёса и шины ===
                            '前轮胎规格尺寸': 'tire_size',
                            '后轮胎规格尺寸': 'tire_size',
                            '轮胎规格': 'tire_size',
                            '轮毂规格': 'wheel_size',
                            '铝合金轮毂': 'wheel_type',
                            '备胎规格': 'tire_type',
                            
                            # === Безопасность ===
                            '主/副驾驶座安全气囊': 'airbag_count',
                            '前排安全气囊': 'airbag_count',
                            'ABS防抱死': 'abs',
                            '车身稳定系统(ESP/DSC等)': 'esp',
                            'ESP车身稳定系统': 'esp',
                            '牵引力控制(TCS/ASR等)': 'tcs',
                            'TCS牵引力控制': 'tcs',
                            '上坡辅助(HAC)': 'hill_assist',
                            '上坡辅助': 'hill_assist',
                            '并线辅助': 'blind_spot_monitor',
                            '盲区监测': 'blind_spot_monitor',
                            '车道偏离预警': 'lane_departure',
                            
                            # === Комфорт ===
                            '空调控制方式': 'air_conditioning',
                            '空调': 'air_conditioning',
                            '自动空调': 'climate_control',
                            '座椅材质': 'upholstery',
                            '座椅加热': 'seat_heating',
                            '座椅通风': 'seat_ventilation',
                            '座椅按摩': 'seat_massage',
                            '方向盘加热': 'steering_wheel_heating',
                            '天窗类型': 'sunroof',
                            '全景天窗': 'panoramic_roof',
                            
                            # === Мультимедиа ===
                            'GPS导航': 'navigation',
                            '卫星导航系统': 'navigation',
                            '音响系统': 'audio_system',
                            '扬声器数量(个)': 'speakers_count',
                            '扬声器数量': 'speakers_count',
                            '蓝牙/车载电话': 'bluetooth',
                            '蓝牙': 'bluetooth',
                            'USB接口': 'usb',
                            'AUX接口': 'aux',
                            
                            # === Освещение ===
                            '前大灯类型': 'headlight_type',
                            '近光灯': 'headlight_type',
                            '远光灯': 'headlight_type',
                            '前雾灯': 'fog_lights',
                            'LED大灯': 'led_lights',
                            '日间行车灯': 'daytime_running',
                        }
                        
                    if label in field_mapping:
                        field_name = field_mapping[label]
                        clean_value = value.strip()
                        
                        # Преобразуем в числовые типы в зависимости от поля
                        if field_name == 'power':
                            logger.info(f"Raw power value from HTML: '{clean_value}' for label '{label}'")
                            # Проверяем, что значение содержит цифры перед обработкой
                            if not any(c.isdigit() for c in clean_value):
                                logger.warning(f"Power value '{clean_value}' does not contain digits, skipping")
                                continue  # Пропускаем это поле
                            # Если label содержит '马力' или 'Ps', это уже л.с., не конвертируем
                            is_already_hp = '马力' in label or 'Ps' in label
                            normalized_hp = normalize_power_value(clean_value, assume_kw=not is_already_hp)
                            logger.info(f"Normalized power value: '{normalized_hp}' for label '{label}' (is_already_hp={is_already_hp})")
                            if normalized_hp:
                                specs[field_name] = normalized_hp  # уже int
                            else:
                                logger.warning(f"Power value '{clean_value}' is invalid, skipping")
                            continue
                        elif field_name == 'max_speed':
                            # int - максимальная скорость в км/ч
                            specs[field_name] = parse_int_value(clean_value)
                        elif field_name == 'electric_range':
                            # int - запас хода в км
                            specs[field_name] = parse_int_value(clean_value)
                        elif field_name == 'engine_volume_ml':
                            # int - объём двигателя в мл
                            specs[field_name] = parse_int_value(clean_value)
                        elif field_name == 'door_count':
                            # int - количество дверей
                            specs[field_name] = parse_int_value(clean_value)
                        elif field_name in ('length', 'width', 'height', 'wheelbase', 'curb_weight'):
                            # Размеры и вес - int (SMALLINT в БД)
                            specs[field_name] = parse_int_value(clean_value)
                        elif field_name in ('torque', 'acceleration', 'fuel_consumption', 'battery_capacity'):
                            # float - числовые характеристики с дробной частью
                            specs[field_name] = parse_float_value(clean_value)
                        else:
                            specs[field_name] = clean_value
                            
                            # Обработка специальных случаев
                            if field_name == 'dimensions':
                                # Парсим размеры из строки "5200x2062x1618"
                                try:
                                    parts = value.split('x')
                                    if len(parts) == 3:
                                        specs['length'] = parse_int_value(parts[0])
                                        specs['width'] = parse_int_value(parts[1])
                                        specs['height'] = parse_int_value(parts[2])
                                except:
                                    pass
                            
                except Exception as row_e:
                    logger.debug(f"Ошибка при парсинге строки таблицы для car_id={car_id}: {row_e}")
                    continue
            
            # Fallback: если power не найден, пробуем извлечь из поля engine_type (发动机)
            # Формат: "2.0T 250马力 H4" или "3.0T 150马力 L4"
            if 'power' not in specs and 'engine_type' in specs:
                engine_desc = specs.get('engine_type', '')
                hp_match = re.search(r'(\d+)\s*马力', engine_desc)
                if hp_match:
                    power_from_engine = parse_int_value(hp_match.group(1))
                    logger.info(f"Fallback: Power extracted from engine_type '{engine_desc}': {power_from_engine} for car_id={car_id}")
                    specs['power'] = power_from_engine
            
            # Логируем итоговые specs
            if 'power' in specs:
                logger.info(f"Final power in specs: {specs['power']} for car_id={car_id}")
            else:
                logger.warning(f"Power NOT found in specs for car_id={car_id}, engine_type={specs.get('engine_type', 'N/A')}")
        except Exception as e:
            # В случае ошибки логируем и возвращаем пустой словарь
            logger.error(f"Ошибка в fetch_car_specifications для car_id={car_id}: {e}", exc_info=True)
            specs = {}
            # Гарантируем, что soup инициализирован
            if 'soup' not in locals() or soup is None:
                soup = None
        finally:
            # Гарантируем закрытие драйвера с проверкой валидности сессии
            if driver:
                try:
                    # Проверяем что driver еще активен перед закрытием
                    try:
                        driver.current_url  # Проверка что сессия жива
                        driver.quit()
                    except (ConnectionRefusedError, WebDriverException, Exception):
                        # Driver уже закрыт или сессия потеряна, просто помечаем как None
                        logger.debug(f"fetch_car_specifications: Driver уже закрыт для car_id={car_id}")
                        pass
                except Exception as e:
                    logger.debug(f"fetch_car_specifications: Ошибка при закрытии driver для car_id={car_id}: {e}")
                finally:
                    driver = None
            # Удаляем временную директорию
            try:
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            # Освобождаем память от page_source (soup уже не нужен, так как парсинг завершен)
            if page_source:
                del page_source
            # Освобождаем память от soup
            if 'soup' in locals() and soup:
                try:
                    soup.decompose()
                    del soup
                except:
                    pass

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
        logger.info(f"Starting enhance for sku_id={sku_id}, car_id={car_id}")
        try:
            detail_car, _ = self.fetch_car_detail(sku_id)
            logger.info(f"fetch_car_detail completed for sku_id={sku_id}")
            if detail_car and hasattr(detail_car, 'power'):
                logger.info(f"Power from detail_car: {getattr(detail_car, 'power', None)} for sku_id={sku_id}")
        except Exception as e:
            logger.error(f"Error in fetch_car_detail for sku_id={sku_id}: {e}", exc_info=True)
            detail_car = None
        
        # Получаем car_id из detail_car, если он не был передан
        if not car_id and detail_car and hasattr(detail_car, 'car_id') and detail_car.car_id:
            car_id = str(detail_car.car_id)
            logger.info(f"Got car_id from detail_car: {car_id} for sku_id={sku_id}")
        
        # Получаем технические характеристики, если car_id предоставлен
        specs = {}
        if car_id:
            try:
                logger.info(f"Starting fetch_car_specifications for car_id={car_id}")
                specs, _ = self.fetch_car_specifications(car_id)
                logger.info(f"fetch_car_specifications completed for car_id={car_id}, specs keys: {list(specs.keys())}")
                if 'power' in specs:
                    logger.info(f"Power from specs: {specs['power']} for car_id={car_id}")
                if 'engine_volume_ml' in specs:
                    logger.info(f"engine_volume_ml from specs: {specs['engine_volume_ml']} for car_id={car_id}")
            except Exception as e:
                logger.error(f"Error in fetch_car_specifications for car_id={car_id}: {e}", exc_info=True)
                specs = {}
        
        # Обновляем объект машины
        if detail_car:
            if getattr(detail_car, "link", None):
                car_obj.link = detail_car.link
            # Копируем базовые поля
            for field in ['title', 'description', 'color', 'transmission', 'fuel_type', 'body_type', 
                         'drive_type', 'condition', 'engine_volume', 'mileage', 'car_mileage',
                         'brand_name', 'series_name', 'car_name', 'car_year', 'year', 'city',
                         'car_source_city_name', 'brand_id', 'series_id', 'shop_id', 'sh_price']:
                if hasattr(detail_car, field) and getattr(detail_car, field) is not None:
                    setattr(car_obj, field, getattr(detail_car, field))
                    if field == 'mileage':
                        logger.info(f"enhance_car_with_details: Копируем mileage для sku_id={sku_id}: {getattr(detail_car, field)}км")
            
            # Копируем engine_volume_ml отдельно, чтобы не перезаписать приоритетным значением из specs позже
            if hasattr(detail_car, 'engine_volume_ml'):
                engine_volume_ml_from_detail = getattr(detail_car, 'engine_volume_ml')
                logger.debug(f"enhance_car_with_details: engine_volume_ml из detail_car для sku_id={sku_id}: {repr(engine_volume_ml_from_detail)} (type: {type(engine_volume_ml_from_detail)})")
                # Преобразуем в int если это строка
                if engine_volume_ml_from_detail is not None:
                    if isinstance(engine_volume_ml_from_detail, int):
                        car_obj.engine_volume_ml = engine_volume_ml_from_detail
                        logger.info(f"engine_volume_ml from detail_car: {engine_volume_ml_from_detail} for sku_id={sku_id}")
                    else:
                        parsed_value = parse_int_value(engine_volume_ml_from_detail)
                        if parsed_value is not None:
                            car_obj.engine_volume_ml = parsed_value
                            logger.info(f"engine_volume_ml from detail_car (parsed): {parsed_value} for sku_id={sku_id}")
                        else:
                            logger.debug(f"engine_volume_ml из detail_car не удалось распарсить для sku_id={sku_id}")
            
            # Логируем first_registration_time из detail_car
            if hasattr(detail_car, 'first_registration_time'):
                first_reg_time = getattr(detail_car, 'first_registration_time')
                logger.debug(f"enhance_car_with_details: first_registration_time из detail_car для sku_id={sku_id}: {repr(first_reg_time)}")
                if first_reg_time:
                    logger.info(f"first_registration_time from detail_car: {first_reg_time} for sku_id={sku_id}")
            
            # Копируем детальную информацию
            # Поля, которые нужно преобразовать в числовые типы
            int_fields = {'power', 'max_speed', 'electric_range', 'door_count'}
            float_fields = {'torque', 'acceleration', 'fuel_consumption', 'battery_capacity'}
            
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
                         'fuel_tank_volume', 'first_registration_time']:
                if not hasattr(detail_car, field):
                    continue
                raw_value = getattr(detail_car, field)
                if raw_value is None:
                    continue
                
                # Логируем важные поля
                if field == 'image_gallery':
                    logger.info(f"enhance_car_with_details: Копируем image_gallery для sku_id={sku_id}: {len(raw_value.split()) if raw_value else 0} изображений")
                elif field == 'first_registration_time':
                    logger.info(f"enhance_car_with_details: Копируем first_registration_time для sku_id={sku_id}: {raw_value}")
                
                if field == 'power':
                    # Используем normalize_power_value который теперь возвращает int
                    normalized_hp = normalize_power_value(raw_value)
                    if normalized_hp:
                        setattr(car_obj, field, normalized_hp)
                elif field in int_fields:
                    # Преобразуем в int
                    parsed_value = parse_int_value(raw_value) if not isinstance(raw_value, int) else raw_value
                    if parsed_value is not None:
                        setattr(car_obj, field, parsed_value)
                elif field in float_fields:
                    # Преобразуем в float
                    parsed_value = parse_float_value(raw_value) if not isinstance(raw_value, float) else raw_value
                    if parsed_value is not None:
                        setattr(car_obj, field, parsed_value)
                else:
                    setattr(car_obj, field, raw_value)
        
        # Добавляем технические характеристики
        for field, value in specs.items():
            if hasattr(car_obj, field):
                # Для power проверяем валидность - должны быть числом
                if field == 'power':
                    if isinstance(value, int) and value > 0:
                        setattr(car_obj, field, value)
                        logger.info(f"Power from specs: {value} for sku_id={sku_id}")
                    else:
                        logger.warning(f"Invalid power value from specs: '{value}' for sku_id={sku_id}, skipping")
                elif field == 'engine_volume_ml':
                    # engine_volume_ml: используем значение из specs только если его еще нет из detail_car
                    # Приоритет отдаем detail_car, так как там более точное значение
                    existing_value = getattr(car_obj, field, None)
                    if not existing_value:
                        if isinstance(value, int) and value > 0:
                            setattr(car_obj, field, value)
                            logger.info(f"engine_volume_ml from specs: {value} for sku_id={sku_id}")
                        else:
                            logger.debug(f"engine_volume_ml from specs пустое или невалидное, пропускаем для sku_id={sku_id}")
                    else:
                        logger.info(f"engine_volume_ml уже установлен из detail_car ({existing_value}), не перезаписываем значением из specs ({value}) для sku_id={sku_id}")
                else:
                    setattr(car_obj, field, value)
        
        # Проверяем, что хотя бы power был успешно распарсен
        # power может быть из detail_car или из specs
        power_value = None
        if hasattr(car_obj, 'power'):
            power_value = getattr(car_obj, 'power')
            logger.info(f"Final power value: {power_value} for sku_id={sku_id}")
        
        # Проверяем валидность power - должен быть int > 0
        has_power = isinstance(power_value, int) and power_value > 0
        logger.info(f"has_power={has_power} for sku_id={sku_id}, power_value={power_value}")
        
        # Устанавливаем флаги только если power был успешно распарсен и содержит цифры
        if has_power:
            car_obj.has_details = True
            car_obj.last_detail_update = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            logger.info(f"Setting has_details=True for sku_id={sku_id}")
        else:
            # Если power не был распарсен или не содержит цифр, оставляем has_details = False
            car_obj.has_details = False
            logger.info(f"No power found for sku_id={sku_id}, has_details=False")
        
        return car_obj
