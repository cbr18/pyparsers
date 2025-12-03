"""
API-based парсер детальной информации с che168.com
Использует прямые HTTP запросы к API вместо Playwright
"""

import re
import logging
import requests
from typing import Optional, Dict, Any, Union
from .models.detailed_car import Che168DetailedCar
from api.date_utils import normalize_first_registration_date

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _parse_int(value: Union[str, int, float, None]) -> Optional[int]:
    """Безопасное преобразование в int."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        match = re.search(r'(\d+)', str(value))
        if match:
            return int(match.group(1))
    except (ValueError, TypeError):
        pass
    return None


def _parse_float(value: Union[str, int, float, None]) -> Optional[float]:
    """Безопасное преобразование в float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        match = re.search(r'([\d.,]+)', str(value))
        if match:
            return float(match.group(1).replace(',', '.'))
    except (ValueError, TypeError):
        pass
    return None


def _convert_circle_to_bool(value: Union[str, None]) -> Optional[bool]:
    """
    Конвертирует символы ● (закрашенный круг) в True, 
    а незакрашенный круг (○) в False.
    
    Args:
        value: Значение для конвертации (может быть str или None)
        
    Returns:
        bool или None
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        # Закрашенный круг ● -> True
        if '●' in value:
            return True
        # Незакрашенный круг ○ -> False
        if '○' in value:
            return False
    return None


class Che168DetailedParserAPI:
    """
    API-based парсер детальной информации для che168.com
    Использует API endpoints напрямую без браузера - быстрее и надёжнее
    """
    
    # Маппинг китайских названий параметров на поля модели
    API_FIELD_MAPPING = {
        # Основные
        '车型名称': 'car_name',
        '厂商': 'manufacturer',
        '级别': 'body_type',
        '厂商指导价(元)': 'msrp',
        '上市时间': 'launch_date',
        
        # Двигатель
        '发动机': 'engine_info',
        '发动机型号': 'engine_code',
        '排量(mL)': 'engine_volume_ml',
        '排量(L)': 'engine_volume',
        '最大马力(Ps)': 'power',
        '最大功率(kW)': 'power_kw',
        '电动机(Ps)': 'power',  # Мощность электромотора для EV
        '最大扭矩(N·m)': 'torque',
        '最大功率转速(rpm)': 'power_rpm',
        '最大扭矩转速(rpm)': 'torque_rpm',
        '进气形式': 'turbo_type',
        '气缸数(个)': 'cylinder_count',
        '每缸气门数(个)': 'valve_count',
        '配气机构': 'valve_mechanism',
        '缸盖材料': 'cylinder_head_material',
        '缸体材料': 'cylinder_block_material',
        '燃料形式': 'fuel_type',
        '燃油标号': 'fuel_grade',
        '供油方式': 'fuel_injection',
        '环保标准': 'emission_standard',
        
        # Трансмиссия
        '变速箱': 'transmission',
        '变速箱类型': 'transmission_type',
        '挡位个数': 'gear_count',
        '简称': 'transmission_short',
        
        # Шасси
        '驱动方式': 'drive_type',
        '四驱形式': 'awd_type',
        '中央差速器结构': 'differential_type',
        '前悬架类型': 'front_suspension',
        '后悬架类型': 'rear_suspension',
        '助力类型': 'steering_type',
        '车体结构': 'body_structure',
        
        # Тормоза
        '前制动器类型': 'front_brakes',
        '后制动器类型': 'rear_brakes',
        '驻车制动类型': 'parking_brake',
        
        # Колёса
        '前轮胎规格': 'tire_size',
        '后轮胎规格': 'rear_tire_size',
        '轮圈材质': 'wheel_type',
        '备胎规格': 'spare_tire',
        
        # Размеры
        '长度(mm)': 'length',
        '宽度(mm)': 'width',
        '高度(mm)': 'height',
        '轴距(mm)': 'wheelbase',
        '长*宽*高(mm)': 'dimensions',
        '整备质量(kg)': 'curb_weight',
        '最大满载质量(kg)': 'gross_weight',
        '油箱容积(L)': 'fuel_tank_volume',
        '后备厢容积(L)': 'trunk_volume',
        '车门数(个)': 'door_count',
        '座位数(个)': 'seat_count',
        
        # Производительность
        '最高车速(km/h)': 'max_speed',
        '官方0-100km/h加速(s)': 'acceleration',
        'NEDC综合油耗(L/100km)': 'fuel_consumption',
        'WLTC综合油耗(L/100km)': 'fuel_consumption_wltc',
        
        # Гарантия и регистрация
        '整车质保': 'warranty_info',
        '首次上牌时间': 'first_registration_time',
        '车辆年审时间': 'inspection_date',
        '交强险截止日期': 'insurance_info',
        
        # Безопасность
        '主/副驾驶座安全气囊': 'airbag_count',
        'ABS防抱死': 'abs',
        '车身稳定控制(ESC/ESP/DSC等)': 'esp',
        '牵引力控制(ASR/TCS/TRC等)': 'tcs',
        '上坡辅助': 'hill_assist',
        '陡坡缓降': 'hill_descent',
        '车道偏离预警系统': 'lane_departure',
        '并线辅助': 'blind_spot_monitor',
        '主动刹车/主动安全系统': 'auto_brake',
        
        # Комфорт
        '空调温度控制方式': 'air_conditioning',
        '温度分区控制': 'climate_control',
        '前排座椅功能': 'seat_heating',
        '方向盘加热': 'steering_wheel_heating',
        '卫星导航系统': 'navigation',
        '蓝牙/车载电话': 'bluetooth',
        '多媒体/充电接口': 'usb',
        '扬声器数量': 'speakers_count',
        '天窗类型': 'sunroof',
        
        # Освещение
        '近光灯光源': 'headlight_type',
        '前大灯雨雾模式': 'fog_lights',
        'LED日间行车灯': 'daytime_running',
        
        # Электро
        '电池能量(kWh)': 'battery_capacity',
        'NEDC纯电续航里程(km)': 'electric_range',
        'CLTC纯电续航里程(km)': 'electric_range',
        '快充时间(小时)': 'fast_charge_time',
        '慢充时间(小时)': 'charging_time',
        '电动机总功率(kW)': 'power_kw',  # Общая мощность электромоторов в кВт
        '电动机总扭矩(N·m)': 'torque',  # Общий крутящий момент электромоторов
        '能源类型': 'fuel_type',  # Тип топлива/энергии (纯电动 = электро)
    }
    
    def __init__(self, timeout: int = 30):
        """
        Инициализация API парсера
        
        Args:
            timeout: Таймаут для HTTP запросов в секундах
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://m.che168.com/",
        })
    
    def parse_car_details(self, car_id: int) -> Optional[Che168DetailedCar]:
        """
        Парсит детальную информацию через API
        
        Args:
            car_id: ID машины
            
        Returns:
            Che168DetailedCar или None
        """
        logger.info(f"[API] Парсинг car_id: {car_id}")
        
        try:
            # Получаем данные из обоих API
            params_data = self._fetch_params_api(car_id)
            carinfo_data = self._fetch_carinfo_api(car_id)
            
            # Объединяем данные
            extracted = {'car_id': car_id}
            
            # Сначала добавляем данные из getparamtypeitems (технические характеристики)
            if params_data:
                extracted.update(params_data)
                logger.info(f"[API] Получено {len(params_data)} полей из getparamtypeitems")
            else:
                logger.warning(f"[API] getparamtypeitems вернул пустой результат для car_id={car_id}")
            
            # Добавляем данные из getcarinfo (базовая информация)
            if carinfo_data:
                # Не перезаписываем уже заполненные поля
                for key, value in carinfo_data.items():
                    if key not in extracted or not extracted.get(key):
                        extracted[key] = value
                logger.info(f"[API] Получено {len(carinfo_data)} полей из getcarinfo")
            
            # Проверяем наличие обязательных полей
            if not extracted.get('power'):
                logger.warning(f"[API] Не удалось получить power для car_id={car_id}")
                # Пробуем извлечь из engine_info
                engine_info = extracted.get('engine_info', '')
                if engine_info:
                    power_match = re.search(r'(\d+)\s*马力', engine_info)
                    if power_match:
                        extracted['power'] = _parse_int(power_match.group(1))  # int
                        logger.info(f"[API] Извлечено power из engine_info: {extracted['power']}")
            
            # Проверяем валидность данных
            significant_fields = ['power', 'transmission', 'drive_type', 'fuel_type', 
                                'engine_volume', 'emission_standard']
            has_significant = any(extracted.get(f) for f in significant_fields)
            
            if not has_significant:
                logger.warning(f"[API] Нет значимых полей для car_id={car_id}")
                return None
            
            logger.info(f"[API] Успешно извлечено {len([v for v in extracted.values() if v])} полей")
            
            # Логируем ключевые поля
            for key in ['power', 'torque', 'transmission', 'fuel_type', 'first_registration_time']:
                if extracted.get(key):
                    logger.info(f"[API]   {key}: {extracted[key]}")
            
            return Che168DetailedCar(**extracted)
            
        except Exception as e:
            logger.error(f"[API] Ошибка парсинга car_id={car_id}: {e}", exc_info=True)
            return None
    
    def _fetch_params_api(self, car_id: int) -> Dict[str, Any]:
        """
        Получает технические характеристики из API getparamtypeitems
        
        Args:
            car_id: ID машины
            
        Returns:
            Словарь с извлечёнными данными
        """
        url = "https://apiuscdt.che168.com/api/v1/car/getparamtypeitems"
        params = {
            "infoid": car_id,
            "deviceid": f"api_parser_{car_id}",
            "_appid": "2sc.m"
        }
        
        extracted = {}
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('returncode') != 0:
                logger.warning(f"[API] getparamtypeitems returncode != 0: {data.get('returnmsg')}")
                return extracted
            
            result = data.get('result', [])
            if not result:
                logger.warning(f"[API] getparamtypeitems result is empty")
                return extracted
            
            # Парсим все секции
            for section in result:
                section_title = section.get('title', '')
                items = section.get('data', [])
                
                for item in items:
                    name = item.get('name', '').strip()
                    content = item.get('content', '').strip()
                    
                    if not content or content == '-':
                        continue
                    
                    # Маппинг на поля модели
                    if name in self.API_FIELD_MAPPING:
                        field_name = self.API_FIELD_MAPPING[name]
                        
                        # Специальная обработка для некоторых полей с числовыми типами
                        if field_name == 'power':
                            # Мощность в л.с. - int
                            power_val = _parse_int(content)
                            if power_val:
                                extracted[field_name] = power_val
                                logger.debug(f"[API] power: {power_val}")
                        elif field_name == 'power_kw':
                            # Мощность в кВт - конвертируем в л.с. если нет power
                            if 'power' not in extracted:
                                try:
                                    kw = float(content)
                                    hp = int(kw * 1.35962)
                                    extracted['power'] = hp  # int
                                    logger.debug(f"[API] power (из kW): {hp}")
                                except (ValueError, TypeError):
                                    pass
                        elif field_name == 'torque':
                            # Крутящий момент - float
                            extracted[field_name] = _parse_float(content)
                        elif field_name == 'acceleration':
                            # Разгон до 100 км/ч - float
                            extracted[field_name] = _parse_float(content)
                        elif field_name == 'max_speed':
                            # Максимальная скорость - int
                            extracted[field_name] = _parse_int(content)
                        elif field_name == 'fuel_consumption':
                            # Расход топлива - float
                            extracted[field_name] = _parse_float(content)
                        elif field_name == 'battery_capacity':
                            # Емкость батареи - float
                            extracted[field_name] = _parse_float(content)
                        elif field_name == 'electric_range':
                            # Запас хода - int
                            extracted[field_name] = _parse_int(content)
                        elif field_name == 'engine_volume_ml':
                            # Объём двигателя в мл - int
                            extracted[field_name] = _parse_int(content)
                        elif field_name == 'door_count':
                            # Количество дверей - int
                            extracted[field_name] = _parse_int(content)
                        elif field_name in ('length', 'width', 'height', 'wheelbase', 'curb_weight'):
                            # Размеры и вес - int (SMALLINT в БД)
                            extracted[field_name] = _parse_int(content)
                        elif field_name == 'dimensions':
                            # Разбираем размеры "5052*1989*1773"
                            dims = re.findall(r'(\d+)', content)
                            if len(dims) >= 3:
                                extracted['length'] = _parse_int(dims[0])
                                extracted['width'] = _parse_int(dims[1])
                                extracted['height'] = _parse_int(dims[2])
                        elif field_name == 'first_registration_time':
                            # Нормализуем дату
                            normalized = normalize_first_registration_date(content)
                            if normalized:
                                extracted[field_name] = normalized
                        elif field_name in ('climate_control', 'lane_departure', 'steering_wheel_heating'):
                            # Оставляем как строку, конвертация будет в detailed_api.py при отправке
                            extracted[field_name] = content
                        else:
                            extracted[field_name] = content
                    
                    # Дополнительно извлекаем power из engine_info
                    if name == '发动机' and '马力' in content and 'power' not in extracted:
                        power_match = re.search(r'(\d+)\s*马力', content)
                        if power_match:
                            extracted['power'] = _parse_int(power_match.group(1))  # int
                            logger.debug(f"[API] power (из 发动机): {extracted['power']}")
                        extracted['engine_info'] = content
            
            return extracted
            
        except requests.RequestException as e:
            logger.error(f"[API] Ошибка запроса getparamtypeitems: {e}")
            return extracted
        except Exception as e:
            logger.error(f"[API] Ошибка парсинга getparamtypeitems: {e}")
            return extracted
    
    def _fetch_carinfo_api(self, car_id: int) -> Dict[str, Any]:
        """
        Получает базовую информацию о машине из API getcarinfo
        
        Args:
            car_id: ID машины
            
        Returns:
            Словарь с извлечёнными данными
        """
        url = "https://apiuscdt.che168.com/apic/v2/car/getcarinfo"
        params = {
            "infoid": car_id,
            "deviceid": f"api_parser_{car_id}",
            "_appid": "2sc.m"
        }
        
        extracted = {}
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if data.get('returncode') != 0:
                logger.warning(f"[API] getcarinfo returncode != 0: {data.get('returnmsg')}")
                return extracted
            
            result = data.get('result', {})
            if not result:
                logger.warning(f"[API] getcarinfo result is empty")
                return extracted
            
            # Маппинг полей API на поля модели
            field_map = {
                'carname': 'car_name',
                'brandname': 'brand_name',
                'seriesname': 'series_name',
                'price': 'price',
                'mileage': 'mileage',
                'regdate': 'first_registration_time',
                'cityname': 'city',
                'color': 'color',
                'engine': 'engine_type',
                'gearbox': 'transmission',
                'dealerid': 'shop_id',
                'dealername': 'dealer_info',
                'dealerphone': 'contact_info',
                'carimage': 'image',
            }
            
            for api_key, db_field in field_map.items():
                value = result.get(api_key)
                if value:
                    if db_field == 'first_registration_time':
                        # Нормализуем дату
                        normalized = normalize_first_registration_date(str(value))
                        if normalized:
                            extracted[db_field] = normalized
                    elif db_field == 'mileage':
                        # Преобразуем в км
                        mileage_str = str(value)
                        match = re.search(r'(\d+\.?\d*)万', mileage_str)
                        if match:
                            extracted[db_field] = str(int(float(match.group(1)) * 10000))
                        else:
                            extracted[db_field] = re.sub(r'[^\d]', '', mileage_str)
                    elif db_field == 'price':
                        # Цена - float
                        extracted[db_field] = _parse_float(value)
                    elif db_field == 'shop_id':
                        # ID магазина - int
                        extracted[db_field] = _parse_int(value)
                    else:
                        extracted[db_field] = str(value)
            
            # Извлекаем год из даты регистрации
            if 'first_registration_time' in extracted:
                reg_date = extracted['first_registration_time']
                try:
                    year = int(str(reg_date)[:4])
                    if 1990 <= year <= 2030:
                        extracted['year'] = year
                except (ValueError, TypeError):
                    pass
            
            # Галерея изображений - проверяем разные источники
            images = None
            image_source = None
            
            # 1. Пробуем piclist (основной источник)
            piclist = result.get('piclist', [])
            if piclist and isinstance(piclist, list) and len(piclist) > 0:
                images = piclist
                image_source = 'piclist'
                logger.info(f"[API] Найдено {len(images)} изображений в piclist для car_id={car_id}")
            
            # 2. Если piclist пуст, пробуем head_images (как в dongchedi)
            if not images:
                head_images = result.get('head_images', [])
                if head_images and isinstance(head_images, list) and len(head_images) > 0:
                    images = head_images
                    image_source = 'head_images'
                    logger.info(f"[API] Найдено {len(images)} изображений в head_images для car_id={car_id}")
            
            # 3. Пробуем images (альтернативное поле)
            if not images:
                images_list = result.get('images', [])
                if images_list and isinstance(images_list, list) and len(images_list) > 0:
                    images = images_list
                    image_source = 'images'
                    logger.info(f"[API] Найдено {len(images)} изображений в images для car_id={car_id}")
            
            # 4. Пробуем picurl (может быть массивом)
            if not images:
                picurl = result.get('picurl', [])
                if picurl:
                    if isinstance(picurl, list) and len(picurl) > 0:
                        images = picurl
                        image_source = 'picurl (list)'
                        logger.info(f"[API] Найдено {len(images)} изображений в picurl для car_id={car_id}")
                    elif isinstance(picurl, str) and picurl.strip():
                        images = [picurl]
                        image_source = 'picurl (string)'
                        logger.info(f"[API] Найдено 1 изображение в picurl (string) для car_id={car_id}")
            
            # Сохраняем галерею, если нашли изображения
            if images:
                # Фильтруем пустые строки и нормализуем URLs
                valid_images = []
                for img in images:
                    img_url = None
                    
                    # Если изображение - строка
                    if isinstance(img, str) and img.strip():
                        img_url = img.strip()
                    # Если изображение - словарь/объект, пробуем извлечь URL из разных полей
                    elif isinstance(img, dict):
                        img_url = (img.get('url') or img.get('src') or img.get('image') or 
                                 img.get('picurl') or img.get('link') or 
                                 list(img.values())[0] if img else None)
                        if img_url and not isinstance(img_url, str):
                            img_url = str(img_url) if img_url else None
                    
                    if img_url and img_url.strip():
                        # Нормализуем URL (добавляем https: если начинается с //)
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        valid_images.append(img_url.strip())
                
                if valid_images:
                    extracted['image'] = valid_images[0]
                    extracted['image_gallery'] = ' '.join(valid_images)
                    extracted['image_count'] = len(valid_images)
                    logger.info(f"[API] Сохранена image_gallery из {image_source} для car_id={car_id}: {len(valid_images)} изображений")
                else:
                    logger.warning(f"[API] Все изображения из {image_source} оказались пустыми для car_id={car_id}. Пример первого элемента: {images[0] if images else 'None'}")
            else:
                # Логируем доступные поля для отладки
                image_fields = ['piclist', 'head_images', 'images', 'picurl', 'imageurl', 'carimage']
                available_fields = {field: result.get(field) for field in image_fields if field in result}
                logger.warning(f"[API] Изображения не найдены для car_id={car_id}. Доступные поля: {list(available_fields.keys())}")
            
            # Если image все еще пуст, пробуем imageurl или carimage (одиночные изображения)
            if not extracted.get('image'):
                imageurl = result.get('imageurl', '') or result.get('carimage', '')
                if imageurl and isinstance(imageurl, str) and imageurl.strip():
                    if imageurl.startswith('//'):
                        imageurl = 'https:' + imageurl
                    extracted['image'] = imageurl.strip()
                    logger.info(f"[API] Использовано imageurl/carimage для car_id={car_id}: {imageurl[:50]}...")
            
            return extracted
            
        except requests.RequestException as e:
            logger.error(f"[API] Ошибка запроса getcarinfo: {e}")
            return extracted
        except Exception as e:
            logger.error(f"[API] Ошибка парсинга getcarinfo: {e}")
            return extracted
    
    def close(self):
        """Закрывает сессию"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

