"""
Парсер детальной информации с che168.com используя Playwright для обхода детекта
"""

import os
import time
import random
import logging
import json
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout, Page
from .models.detailed_car import Che168DetailedCar

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Che168DetailedParserPlaywright:
    """Парсер детальной информации используя Playwright"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
    
    def parse_car_details(self, car_id: int) -> Optional[Che168DetailedCar]:
        """
        Парсит детальную информацию используя Playwright + Desktop версию
        
        Args:
            car_id: ID машины
            
        Returns:
            Che168DetailedCar или None
        """
        # ИСПОЛЬЗУЕМ DESKTOP ВЕРСИЮ - она не детектируется!
        # dealer_id можно получить из URL редиректа или использовать дефолтный
        dealer_id = os.environ.get("CHE168_DEFAULT_DEALER_ID", "379347")
        url = f"https://www.che168.com/dealer/{dealer_id}/{car_id}.html"
        
        logger.info(f"[Playwright] Парсинг car_id: {car_id}, URL: {url}")
        
        with sync_playwright() as p:
            try:
                # Запускаем браузер
                logger.info("[Playwright] Запуск браузера...")
                browser = p.chromium.launch(
                    headless=self.headless,
                    executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage'
                    ]
                )
                
                # Создаем контекст DESKTOP
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    locale='zh-CN',
                    timezone_id='Asia/Shanghai'
                )
                
                page = context.new_page()
                
                # Блокируем изображения для ускорения
                page.route("**/*.{png,jpg,jpeg,gif,svg,webp}", lambda route: route.abort())
                
                logger.info(f"[Playwright] Загрузка desktop страницы...")
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Ожидание для JavaScript
                logger.info("[Playwright] Ждем JavaScript...")
                time.sleep(5)
                
                # Прокрутка для загрузки динамического контента
                logger.info("[Playwright] Прокрутка страницы...")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(1)
                
                # Получаем HTML
                html = page.content()
                logger.info(f"[Playwright] Размер HTML: {len(html):,} байт")
                
                # Пробуем кликнуть на "更多" / "全部参数配置" для получения детальных характеристик
                logger.info("[Playwright] Попытка клика на '更多' для деталей...")
                try:
                    # Ищем кнопку или ссылку "全部参数配置"
                    more_selectors = [
                        "text=全部参数配置",
                        "a:has-text('全部参数配置')",
                        "a:has-text('更多')",
                        ".more-params",
                        "[onclick*='showParams']",
                    ]
                    
                    clicked = False
                    for selector in more_selectors:
                        try:
                            button = page.locator(selector).first
                            if button.count() > 0:
                                logger.info(f"[Playwright] Найдена кнопка: {selector}")
                                button.click(timeout=3000)
                                logger.info("[Playwright] ✓ Клик выполнен!")
                                page.wait_for_timeout(2000)  # Ждем загрузки контента
                                clicked = True
                                break
                        except Exception as e:
                            continue
                    
                    if clicked:
                        # Получаем обновленный HTML после клика
                        html_after = page.content()
                        if len(html_after) > len(html):
                            logger.info(f"[Playwright] ✓ HTML расширен: +{len(html_after) - len(html):,} байт")
                            html = html_after
                        else:
                            logger.info("[Playwright] HTML не изменился, возможно детали уже отображены")
                    else:
                        logger.info("[Playwright] Кнопка '更多' не найдена - все данные уже отображены")
                        
                except Exception as e:
                    logger.warning(f"[Playwright] Не удалось кликнуть на '更多': {e}")
                
                # Сохраняем для отладки
                debug_dir = os.getenv('CHE168_DEBUG_DIR', '/tmp/che168_debug')
                try:
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_file = os.path.join(debug_dir, f'playwright_{car_id}.html')
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(html)
                    logger.info(f"[Playwright] HTML сохранен: {debug_file}")
                except Exception as e:
                    logger.warning(f"[Playwright] Не удалось сохранить HTML: {e}")
                
                # Закрываем браузер
                browser.close()
                
                # Проверяем на "продано"
                if '当前车源已成交' in html or '车源已下架' in html or '车源已删除' in html:
                    logger.warning(f"[Playwright] Автомобиль {car_id} УЖЕ ПРОДАН или недоступен")
                    return None
                
                # Парсим данные
                soup = BeautifulSoup(html, 'html.parser')
                car_data = self._extract_car_data(soup, car_id, html)
                
                if car_data:
                    data_fields = {k: v for k, v in car_data.items() if k != 'car_id' and v is not None}
                    logger.info(f"[Playwright] Успешно извлечено {len(data_fields)} полей")
                    return Che168DetailedCar(**car_data)
                else:
                    logger.warning(f"[Playwright] Не удалось извлечь данные для {car_id}")
                    return None
                    
            except Exception as e:
                logger.error(f"[Playwright] Ошибка парсинга {car_id}: {e}", exc_info=True)
                return None
    
    def _extract_car_data(self, soup: BeautifulSoup, car_id: int, html: str = "") -> Optional[Dict[str, Any]]:
        """Извлекает данные из desktop HTML"""
        try:
            data = {'car_id': car_id}
            
            # ПАРСИНГ DESKTOP СТРУКТУРЫ
            # Desktop использует: <span class="item-name">Ключ</span>Значение в родителе
            logger.info("[Playwright] Парсинг desktop структуры...")
            
            items = soup.find_all('span', class_='item-name')
            logger.debug(f"[Playwright] Найдено item-name элементов: {len(items)}")
            
            field_mapping = {
                # Основные данные
                '上牌时间': 'registration_date',
                '表显里程': 'mileage',
                '排放标准': 'emission_standard',
                '所  在  地': 'city',
                '所在地': 'city',
                '车身颜色': 'color',
                '外观颜色': 'exterior_color',
                '内饰颜色': 'interior_color',
                
                # Двигатель и трансмиссия
                '发  动  机': 'engine_info',  # "2.0T 252马力 L4"
                '变  速  箱': 'transmission',
                '排       量': 'engine_volume',
                '驱动方式': 'drive_type',
                '燃油标号': 'fuel_grade',
                '燃料形式': 'fuel_type',
                
                # История и статус
                '过户次数': 'owner_count',
                '年检到期': 'inspection_date',
                '保险到期': 'insurance_info',
                '质保到期': 'warranty_info',
                
                # Классификация
                '车辆级别': 'vehicle_class',
                
                # Дополнительные данные
                '配置亮点': 'features',  # Список функций безопасности и комфорта
                '出险查询': 'accident_query_info',
                '维修保养': 'service_query_info',
            }
            
            found_keys = []
            for item in items:
                key_raw = item.get_text(strip=True)
                # Нормализуем неразрывные пробелы (\xa0) в обычные
                key = key_raw.replace('\xa0', ' ')
                found_keys.append(key)
                
                if key in field_mapping:
                    field_name = field_mapping[key]
                    
                    # Получаем родительский элемент
                    parent = item.parent
                    if parent:
                        # Извлекаем весь текст и нормализуем пробелы
                        full_text_raw = parent.get_text(strip=True)
                        full_text = full_text_raw.replace('\xa0', ' ')
                        value = full_text.replace(key, '').strip()
                        
                        if value:
                            data[field_name] = value
                            logger.info(f"[Playwright] ✓ {key}: {value[:50]}")
            
            # Логируем какие ключи не нашли в mapping
            logger.debug(f"[Playwright] Найденные ключи: {found_keys}")
            missing_keys = [k for k in found_keys if k not in field_mapping]
            if missing_keys:
                logger.warning(f"[Playwright] Ключи без mapping: {missing_keys}")
            
            # СПЕЦИАЛЬНАЯ ОБРАБОТКА ПОЛЕЙ
            
            # 1. Мощность из engine_info
            if 'engine_info' in data:
                engine_text = data['engine_info']  # "2.0T 252马力 L4"
                logger.debug(f"[Playwright] Обработка engine_info: {engine_text}")
                
                # Мощность (число перед "马力")
                power_match = re.search(r'(\d+)马力', engine_text)
                if power_match:
                    data['power'] = power_match.group(1) + 'Ps'
                    logger.info(f"[Playwright] ✓ Мощность: {data['power']}")
                
                # Объем двигателя
                volume_match = re.search(r'([\d.]+)[TL]', engine_text)
                if volume_match:
                    data['engine_volume'] = volume_match.group(1) + 'L'
                    logger.debug(f"[Playwright] ✓ Объем: {data['engine_volume']}")
                
                # Тип двигателя (турбо)
                if 'T' in engine_text and not data.get('engine_type'):
                    data['engine_type'] = engine_text.split()[0] if ' ' in engine_text else engine_text
                    logger.debug(f"[Playwright] ✓ Тип двигателя: {data['engine_type']}")
                
                # Количество цилиндров
                cyl_match = re.search(r'L(\d+)', engine_text)
                if cyl_match:
                    data['cylinder_count'] = cyl_match.group(1)
                    logger.debug(f"[Playwright] ✓ Цилиндров: {data['cylinder_count']}")
            
            # 2. Пробег - преобразуем "0.4万公里" в км
            if 'mileage' in data:
                mileage_text = data['mileage']
                match = re.search(r'(\d+\.?\d*)万公里', mileage_text)
                if match:
                    mileage_wan = float(match.group(1))
                    mileage_km = int(mileage_wan * 10000)
                    data['mileage'] = str(mileage_km)
                    logger.debug(f"[Playwright] ✓ Пробег: {mileage_km} км")
            
            # 3. Год из даты регистрации
            if 'registration_date' in data:
                reg_date = data['registration_date']
                year_match = re.search(r'(\d{4})', reg_date)
                if year_match:
                    data['year'] = int(year_match.group(1))
                    logger.debug(f"[Playwright] ✓ Год: {data['year']}")
            
            # 4. Количество владельцев из "0次"
            if 'owner_count' in data:
                owner_text = data['owner_count']
                owner_match = re.search(r'(\d+)次', owner_text)
                if owner_match:
                    data['owner_count'] = int(owner_match.group(1))
                    logger.debug(f"[Playwright] ✓ Владельцев: {data['owner_count']}")
            
            # 5. Парсинг "配置亮点" (features) - извлекаем конкретные функции
            if 'features' in data:
                features_text = data['features']
                logger.debug(f"[Playwright] Парсинг features: {features_text[:100]}")
                
                # Маппинг китайских названий функций на поля domain.Car
                feature_mapping = {
                    # Безопасность
                    '并线辅助': 'blind_spot_monitor',
                    '车道保持': 'lane_departure',
                    '车道偏离': 'lane_departure',
                    '主动刹车': 'abs',
                    '主动安全': 'esp',
                    'ABS': 'abs',
                    'ESP': 'esp',
                    'TCS': 'tcs',
                    '上坡辅助': 'hill_assist',
                    '气囊': 'airbag_count',
                    
                    # Комфорт и удобство
                    'ISOFIX': 'isofix',
                    '自动驻车': 'auto_parking',
                    '自动泊车': 'auto_parking',
                    '电动后备厢': 'power_trunk',
                    '感应后备厢': 'sensor_trunk',
                    '无钥匙启动': 'keyless_start',
                    '无钥匙进入': 'keyless_entry',
                    '座椅加热': 'seat_heating',
                    '座椅通风': 'seat_ventilation',
                    '座椅按摩': 'seat_massage',
                    '方向盘加热': 'steering_wheel_heating',
                    '自动空调': 'air_conditioning',
                    '分区空调': 'climate_control',
                    
                    # Освещение
                    'LED': 'led_lights',
                    '日间行车灯': 'daytime_running',
                    '大灯': 'headlight_type',
                    '雾灯': 'fog_lights',
                    
                    # Мультимедиа
                    '蓝牙': 'bluetooth',
                    '导航': 'navigation',
                    'USB': 'usb',
                    '音响': 'audio_system',
                    
                    # Другое
                    '天窗': 'sunroof',
                    '全景天窗': 'panoramic_roof',
                    '电动座椅': 'power_seats',
                }
                
                for keyword, field_name in feature_mapping.items():
                    if keyword in features_text:
                        # Пробуем извлечь конкретное значение, иначе просто "有" (есть)
                        if field_name == 'airbag_count' and '气囊' in keyword:
                            # Пробуем найти число перед "气囊"
                            match = re.search(r'(\d+).*?气囊', features_text)
                            if match:
                                data[field_name] = match.group(1)
                            else:
                                data[field_name] = '有'
                        else:
                            data[field_name] = '有'
                        
                        logger.debug(f"[Playwright] ✓ Feature: {keyword} → {field_name}")
            
            # 6. Body type из vehicle_class
            if 'vehicle_class' in data and not data.get('body_type'):
                vehicle_class = data['vehicle_class']
                # Маппинг китайских типов кузова
                body_mapping = {
                    '轿车': 'Sedan',
                    '中大型车': 'Full-size Sedan',
                    '中型车': 'Mid-size Sedan',
                    '紧凑型车': 'Compact',
                    '微型车': 'Mini',
                    'SUV': 'SUV',
                    '中型SUV': 'Mid-size SUV',
                    '中大型SUV': 'Full-size SUV',
                    '紧凑型SUV': 'Compact SUV',
                    'MPV': 'MPV',
                    '跑车': 'Sports Car',
                    '皮卡': 'Pickup',
                    '客车': 'Van',
                    '卡车': 'Truck',
                }
                for cn_type, en_type in body_mapping.items():
                    if cn_type in vehicle_class:
                        data['body_type'] = en_type
                        logger.debug(f"[Playwright] ✓ Body type: {en_type}")
                        break
            
            # 7. Fuel type из fuel_grade
            if 'fuel_grade' in data and not data.get('fuel_type'):
                fuel_grade = data['fuel_grade']
                if '号' in fuel_grade:  # 95号, 92号 и т.д. = бензин
                    data['fuel_type'] = '汽油'
                    logger.debug(f"[Playwright] ✓ Fuel type: 汽油 (из {fuel_grade})")
                elif '柴油' in fuel_grade:
                    data['fuel_type'] = '柴油'
                elif '电' in fuel_grade or '充电' in fuel_grade:
                    data['fuel_type'] = '纯电动'
                elif '混动' in fuel_grade or '油电' in fuel_grade:
                    data['fuel_type'] = '油电混合'
            
            # 8. Извлекаем price, brand, series из title и HTML
            self._extract_metadata(soup, html, data)
            
            # Дополнительно используем методы из основного парсера для извлечения:
            # - изображений
            # - описания
            # - дополнительных характеристик
            try:
                from .detailed_parser import Che168DetailedParser
                parser = Che168DetailedParser()
                parser._extract_images(soup, data)
                parser._extract_description(soup, data)
            except Exception as e:
                logger.warning(f"[Playwright] Не удалось использовать доп. методы парсинга: {e}")
            
            logger.info(f"[Playwright] Извлечено {len([v for v in data.values() if v is not None])} полей")
            
            # ОТЛАДКА: показываем что извлекли
            logger.info(f"[Playwright] Ключевые поля:")
            for key in ['power', 'engine_type', 'engine_volume', 'transmission', 'mileage', 'year', 'registration_date']:
                value = data.get(key)
                if value:
                    logger.info(f"[Playwright]   {key}: {value}")
            
            # КРИТИЧЕСКАЯ ПРОВЕРКА: Если НЕТ значимых полей - возвращаем None
            # Это предотвращает ситуацию когда has_details=true но данных нет
            significant_fields = ['power', 'engine_type', 'engine_volume', 'transmission', 
                                'drive_type', 'fuel_type', 'emission_standard', 'brand_name', 'series_name']
            has_significant = any(data.get(f) and str(data.get(f)).strip() != '' for f in significant_fields)
            
            if not has_significant:
                logger.warning(f"[Playwright] Нет значимых полей для car_id {car_id} - возвращаем None")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"[Playwright] Ошибка извлечения данных: {e}", exc_info=True)
            return None
    
    def _extract_metadata(self, soup: BeautifulSoup, html: str, data: Dict[str, Any]):
        """Извлекает метаданные: price, brand, series из title и HTML"""
        try:
            # 1. Price (цена)
            price_elem = soup.find(string=re.compile(r'¥\d+'))
            if price_elem:
                # Ищем формат "¥12.87万"
                price_match = re.search(r'¥([\d.]+)万', price_elem)
                if price_match:
                    price_wan = float(price_match.group(1))
                    data['price'] = f"{price_wan}万"
                    logger.debug(f"[Playwright] ✓ Price: {data['price']}")
            
            # 2. Brand & Series из title
            title_elem = soup.find('title')
            if title_elem:
                title_text = title_elem.get_text()
                data['title'] = title_text
                
                # Парсим формат "【城市】品牌型号 年款 配置_价格_二手车之家"
                # Например: "【大连】红旗HS5 2023款 2.0T 旗领Pro版_12.8700_二手车之家"
                title_match = re.search(r'】(.+?)\s*(\d{4})款', title_text)
                if title_match:
                    full_name = title_match.group(1).strip()
                    
                    # Разделяем на бренд и серию
                    # Китайские бренды обычно 2-4 иероглифа, затем английские буквы/цифры
                    brand_series_match = re.match(r'([^\x00-\x7F]{2,4})([\x00-\x7F\d\s\-]+)', full_name)
                    if brand_series_match:
                        data['brand_name'] = brand_series_match.group(1).strip()
                        data['series_name'] = brand_series_match.group(2).strip()
                        logger.debug(f"[Playwright] ✓ Brand: {data['brand_name']}, Series: {data['series_name']}")
                    else:
                        # Альтернатива - весь full_name как car_name
                        data['car_name'] = full_name
                        logger.debug(f"[Playwright] ✓ Car name: {data['car_name']}")
            
            # 3. Fuel consumption из текста
            fuel_elem = soup.find(string=re.compile(r'油耗'))
            if fuel_elem:
                parent = fuel_elem.parent
                if parent:
                    text = parent.get_text(strip=True).replace('\xa0', ' ')
                    # Ищем формат "X.XL" или "XL/100km"
                    fuel_match = re.search(r'([\d.]+)\s*L', text)
                    if fuel_match:
                        data['fuel_consumption'] = fuel_match.group(1) + 'L/100km'
                        logger.debug(f"[Playwright] ✓ Fuel consumption: {data['fuel_consumption']}")
        
        except Exception as e:
            logger.warning(f"[Playwright] Ошибка извлечения метаданных: {e}")

