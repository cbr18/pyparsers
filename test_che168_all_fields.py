#!/usr/bin/env python3
"""
Комплексный тест всех источников che168 на предмет получения всех полей из БД
"""

import json
import re
import time
import os
import requests
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Все поля из таблицы cars
DB_FIELDS = [
    # Основные
    'title', 'car_name', 'year', 'mileage', 'price', 'image', 'link',
    'brand_name', 'series_name', 'city', 'shop_id', 'tags',
    'car_source_city_name', 'description', 'color',
    
    # Технические
    'transmission', 'fuel_type', 'engine_volume', 'body_type', 'drive_type',
    'power', 'torque', 'acceleration', 'max_speed', 'fuel_consumption',
    'emission_standard',
    
    # Размеры
    'length', 'width', 'height', 'wheelbase', 'curb_weight', 'gross_weight',
    
    # Двигатель
    'engine_type', 'engine_code', 'cylinder_count', 'valve_count',
    'compression_ratio', 'turbo_type', 'engine_volume_ml',
    
    # Электро
    'battery_capacity', 'electric_range', 'charging_time', 'fast_charge_time',
    'charge_port_type',
    
    # Трансмиссия/шасси
    'transmission_type', 'gear_count', 'differential_type',
    'front_suspension', 'rear_suspension', 'front_brakes', 'rear_brakes',
    'brake_system',
    
    # Колёса
    'wheel_size', 'tire_size', 'wheel_type', 'tire_type',
    
    # Безопасность
    'airbag_count', 'abs', 'esp', 'tcs', 'hill_assist',
    'blind_spot_monitor', 'lane_departure',
    
    # Комфорт
    'air_conditioning', 'climate_control', 'seat_heating', 'seat_ventilation',
    'seat_massage', 'steering_wheel_heating', 'navigation', 'audio_system',
    'speakers_count', 'bluetooth', 'usb', 'aux',
    
    # Освещение
    'headlight_type', 'fog_lights', 'led_lights', 'daytime_running',
    
    # История
    'owner_count', 'accident_history', 'service_history', 'warranty_info',
    'inspection_date', 'insurance_info', 'first_registration_time',
    
    # Внешний вид
    'interior_color', 'exterior_color', 'upholstery', 'sunroof', 'panoramic_roof',
    
    # Контакты
    'contact_info', 'dealer_info', 'certification',
    
    # Изображения
    'image_gallery', 'image_count',
    
    # Дополнительно
    'seat_count', 'door_count', 'trunk_volume', 'fuel_tank_volume',
]

# Маппинг китайских названий из API на поля БД
API_FIELD_MAPPING = {
    # Базовые параметры
    '车型名称': 'car_name',
    '厂商指导价(元)': 'msrp',
    '厂商': 'manufacturer',
    '级别': 'body_type',
    '能源类型': 'fuel_type',
    '环保标准': 'emission_standard',
    '上市时间': 'launch_date',
    '最大功率(kW)': 'power_kw',
    '最大扭矩(N·m)': 'torque',
    '发动机': 'engine_info',  # Содержит power в тексте
    '变速箱': 'transmission',
    '长*宽*高(mm)': 'dimensions',
    '车身结构': 'body_structure',
    '最高车速(km/h)': 'max_speed',
    '官方0-100km/h加速(s)': 'acceleration',
    'NEDC综合油耗(L/100km)': 'fuel_consumption',
    'WLTC综合油耗(L/100km)': 'fuel_consumption',
    '整车质保': 'warranty_info',
    
    # Кузов
    '长度(mm)': 'length',
    '宽度(mm)': 'width',
    '高度(mm)': 'height',
    '轴距(mm)': 'wheelbase',
    '前轮距(mm)': 'front_track',
    '后轮距(mm)': 'rear_track',
    '接近角(°)': 'approach_angle',
    '离去角(°)': 'departure_angle',
    '车身结构': 'body_type',
    '车门开启方式': 'door_type',
    '车门数(个)': 'door_count',
    '座位数(个)': 'seat_count',
    '油箱容积(L)': 'fuel_tank_volume',
    '后备厢容积(L)': 'trunk_volume',
    '整备质量(kg)': 'curb_weight',
    '最大满载质量(kg)': 'gross_weight',
    
    # Двигатель
    '发动机型号': 'engine_code',
    '排量(mL)': 'engine_volume_ml',
    '排量(L)': 'engine_volume',
    '进气形式': 'turbo_type',
    '发动机布局': 'engine_layout',
    '气缸排列形式': 'cylinder_arrangement',
    '气缸数(个)': 'cylinder_count',
    '每缸气门数(个)': 'valve_count',
    '配气机构': 'valve_mechanism',
    '最大马力(Ps)': 'power',
    '最大功率转速(rpm)': 'power_rpm',
    '最大扭矩转速(rpm)': 'torque_rpm',
    '最大净功率(kW)': 'net_power',
    '燃料形式': 'fuel_type',
    '燃油标号': 'fuel_grade',
    '供油方式': 'fuel_injection',
    '缸盖材料': 'cylinder_head_material',
    '缸体材料': 'cylinder_block_material',
    
    # Трансмиссия
    '挡位个数': 'gear_count',
    '变速箱类型': 'transmission_type',
    '简称': 'transmission_short',
    
    # Шасси
    '驱动方式': 'drive_type',
    '四驱形式': 'awd_type',
    '中央差速器结构': 'differential_type',
    '前悬架类型': 'front_suspension',
    '后悬架类型': 'rear_suspension',
    '助力类型': 'steering_type',
    '车体结构': 'body_structure',
    
    # Тормоза/колёса
    '前制动器类型': 'front_brakes',
    '后制动器类型': 'rear_brakes',
    '驻车制动类型': 'parking_brake',
    '前轮胎规格': 'tire_size',
    '后轮胎规格': 'rear_tire_size',
    '备胎规格': 'spare_tire',
    
    # Безопасность
    '主/副驾驶座安全气囊': 'airbag_count',
    '前/后排侧气囊': 'side_airbags',
    '前/后排头部气囊(气帘)': 'head_airbags',
    '膝部气囊': 'knee_airbag',
    'ABS防抱死': 'abs',
    '制动力分配(EBD/CBC等)': 'ebd',
    '刹车辅助(EBA/BAS/BA等)': 'brake_assist',
    '牵引力控制(ASR/TCS/TRC等)': 'tcs',
    '车身稳定控制(ESC/ESP/DSC等)': 'esp',
    '胎压监测功能': 'tpms',
    '车道偏离预警系统': 'lane_departure',
    '主动刹车/主动安全系统': 'auto_brake',
    '疲劳驾驶提示': 'fatigue_warning',
    'DOW开门预警': 'dow_warning',
    '前方碰撞预警': 'collision_warning',
    
    # Вождение
    '驾驶模式切换': 'drive_modes',
    '发动机启停技术': 'start_stop',
    '自动驻车': 'auto_hold',
    '上坡辅助': 'hill_assist',
    '陡坡缓降': 'hill_descent',
    '前/后驻车雷达': 'parking_sensors',
    '驾驶辅助影像': 'camera_system',
    '巡航系统': 'cruise_control',
    '辅助驾驶系统': 'adas',
    '辅助驾驶等级': 'adas_level',
    '倒车车侧预警系统': 'rear_cross_traffic',
    '卫星导航系统': 'navigation',
    '并线辅助': 'blind_spot_monitor',
    '车道保持辅助系统': 'lane_keep',
    '车道居中保持': 'lane_centering',
    '辅助泊车入位': 'parking_assist',
    
    # Экстерьер
    '轮圈材质': 'wheel_type',
    '电动后备厢': 'power_trunk',
    '感应后备厢': 'hands_free_trunk',
    '车顶行李架': 'roof_rack',
    '发动机电子防盗': 'immobilizer',
    '无钥匙启动系统': 'keyless_start',
    '无钥匙进入功能': 'keyless_entry',
    
    # Освещение
    '近光灯光源': 'headlight_type',
    '远光灯光源': 'high_beam_type',
    'LED日间行车灯': 'daytime_running',
    '自动头灯': 'auto_headlights',
    '前大灯雨雾模式': 'fog_lights',
    '大灯高度可调': 'headlight_adj',
    '大灯延时关闭': 'headlight_delay',
    
    # Крыша/стекло
    '天窗类型': 'sunroof',
    '前/后电动车窗': 'power_windows',
    '车窗一键升降功能': 'one_touch_windows',
    '后排侧隐私玻璃': 'privacy_glass',
    '后雨刷': 'rear_wiper',
    '感应雨刷功能': 'rain_sensing_wipers',
    
    # Зеркала
    '外后视镜功能': 'mirror_features',
    
    # Мультимедиа
    '中控彩色屏幕': 'display_type',
    '中控屏幕尺寸': 'display_size',
    '蓝牙/车载电话': 'bluetooth',
    '手机互联/映射': 'phone_connectivity',
    '语音识别控制系统': 'voice_control',
    '车载智能系统': 'infotainment',
    '车联网': 'connectivity',
    '4G/5G网络': 'cellular',
    'Wi-Fi热点': 'wifi',
    '手机APP远程功能': 'remote_app',
    
    # Руль/панель
    '方向盘材质': 'steering_material',
    '方向盘位置调节': 'steering_adj',
    '换挡形式': 'shifter_type',
    '多功能方向盘': 'multifunction_steering',
    '方向盘加热': 'steering_wheel_heating',
    '行车电脑显示屏幕': 'trip_computer',
    '全液晶仪表盘': 'digital_cluster',
    '液晶仪表尺寸': 'cluster_size',
    'HUD抬头数字显示': 'hud',
    '内后视镜功能': 'interior_mirror',
    
    # Зарядка
    '多媒体/充电接口': 'usb',
    'USB/Type-C接口数量': 'usb_count',
    '行李厢12V电源接口': 'trunk_power',
    
    # Сиденья
    '座椅材质': 'upholstery',
    '主座椅调节方式': 'driver_seat_adj',
    '副座椅调节方式': 'passenger_seat_adj',
    '主/副驾驶座电动调节': 'power_seats',
    '前排座椅功能': 'front_seat_features',
    '电动座椅记忆功能': 'seat_memory',
    '第二排座椅调节': 'rear_seat_adj',
    '第二排座椅功能': 'rear_seat_features',
    '第二排独立座椅': 'captain_chairs',
    '座椅布局': 'seat_layout',
    '后排座椅放倒形式': 'rear_seat_fold',
    '前/后中央扶手': 'armrests',
    '后排杯架': 'rear_cupholders',
    
    # Аудио/свет
    '扬声器数量': 'speakers_count',
    '车内环境氛围灯': 'ambient_lighting',
    
    # Климат
    '空调温度控制方式': 'air_conditioning',
    '后排独立空调': 'rear_ac',
    '后座出风口': 'rear_vents',
    '温度分区控制': 'climate_control',
    '车载空气净化器': 'air_purifier',
    '车内PM2.5过滤装置': 'pm25_filter',
    
    # Регистрация
    '首次上牌时间': 'first_registration_time',
    '车辆年审时间': 'inspection_date',
    '交强险截止日期': 'insurance_info',
}

TEST_CAR_ID = 56305293


def extract_from_api(car_id: int) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Извлечение из API getparamtypeitems
    Возвращает (extracted_data, raw_api_data)
    """
    url = "https://apiuscdt.che168.com/api/v1/car/getparamtypeitems"
    params = {
        "infoid": car_id,
        "deviceid": f"test_{car_id}",
        "_appid": "2sc.m"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
        "Referer": f"https://m.che168.com/cardetail/index?infoid={car_id}"
    }
    
    extracted = {}
    raw_data = {}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        data = resp.json()
        
        if data.get('returncode') != 0:
            return extracted, raw_data
        
        result = data.get('result', [])
        
        for section in result:
            title = section.get('title', '')
            items = section.get('data', [])
            
            for item in items:
                name = item.get('name', '').strip()
                content = item.get('content', '').strip()
                
                if not content or content == '-':
                    continue
                
                raw_data[name] = content
                
                # Маппинг на поля БД
                if name in API_FIELD_MAPPING:
                    field = API_FIELD_MAPPING[name]
                    extracted[field] = content
                
                # Специальная обработка мощности
                if '最大马力' in name:
                    extracted['power'] = content + 'Ps'
                
                # Извлечение из составных полей
                if name == '发动机' and '马力' in content:
                    power_match = re.search(r'(\d+)\s*马力', content)
                    if power_match and 'power' not in extracted:
                        extracted['power'] = power_match.group(1) + 'Ps'
                    extracted['engine_info'] = content
                
                # Размеры из составного поля
                if '长*宽*高' in name:
                    dims = re.findall(r'(\d+)', content)
                    if len(dims) >= 3:
                        extracted['length'] = dims[0]
                        extracted['width'] = dims[1]
                        extracted['height'] = dims[2]
        
        return extracted, raw_data
        
    except Exception as e:
        print(f"API Error: {e}")
        return extracted, raw_data


def extract_from_carinfo_api(car_id: int) -> Dict[str, Any]:
    """Извлечение из API getcarinfo"""
    url = "https://apiuscdt.che168.com/apic/v2/car/getcarinfo"
    params = {
        "infoid": car_id,
        "deviceid": f"test_{car_id}",
        "_appid": "2sc.m"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
        "Referer": f"https://m.che168.com/cardetail/index?infoid={car_id}"
    }
    
    extracted = {}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        data = resp.json()
        
        if data.get('returncode') != 0:
            return extracted
        
        result = data.get('result', {})
        
        # Маппинг полей
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
            'specid': 'spec_id',
            'dealerid': 'shop_id',
            'dealername': 'dealer_info',
            'dealerphone': 'contact_info',
            'carimage': 'image',
            'carimages': 'image_gallery',
        }
        
        for api_key, db_field in field_map.items():
            if api_key in result and result[api_key]:
                extracted[db_field] = result[api_key]
        
        return extracted
        
    except Exception as e:
        print(f"CarInfo API Error: {e}")
        return extracted


def extract_from_mobile(car_id: int) -> Dict[str, Any]:
    """Извлечение из мобильной версии"""
    extracted = {}
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
                viewport={'width': 390, 'height': 844},
                locale='zh-CN'
            )
            
            page = context.new_page()
            
            mobile_url = f"https://m.che168.com/cardetail/index?infoid={car_id}"
            page.goto(mobile_url, wait_until='networkidle', timeout=60000)
            time.sleep(5)
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            # Title
            title_tag = soup.find('title')
            if title_tag:
                extracted['page_title'] = title_tag.get_text()
            
            # Ищем данные
            patterns = {
                'power': r'(\d+)\s*马力',
                'torque': r'(\d+)\s*N·m',
                'mileage': r'(\d+\.?\d*)\s*万公里',
                'year': r'20[12]\d年',
            }
            
            for field, pattern in patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    extracted[field] = match.group(1) if match.lastindex else match.group(0)
            
            # Ищем дату регистрации
            reg_match = re.search(r'(\d{4})[年/-](\d{1,2})', page_text)
            if reg_match:
                extracted['first_registration_time'] = f"{reg_match.group(1)}-{reg_match.group(2).zfill(2)}"
            
            browser.close()
            
        except Exception as e:
            print(f"Mobile Error: {e}")
    
    return extracted


def extract_from_desktop(car_id: int) -> Dict[str, Any]:
    """Извлечение из десктопной версии"""
    extracted = {}
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True,
                executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN'
            )
            
            page = context.new_page()
            
            desktop_url = f"https://www.che168.com/dealer/557461/{car_id}.html"
            page.goto(desktop_url, wait_until='networkidle', timeout=60000)
            time.sleep(3)
            
            title = page.title()
            if '访问出错' in title or '404' in title:
                browser.close()
                return extracted
            
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()
            
            # Title - содержит название машины
            extracted['page_title'] = title
            title_match = re.search(r'【[^】]+】(.+?)_', title)
            if title_match:
                extracted['car_name'] = title_match.group(1)
            
            # Ищем данные в тексте
            patterns = {
                'power': (r'(\d+)\s*马力', lambda m: m.group(1) + 'Ps'),
                'torque': (r'(\d+)\s*N·m', lambda m: m.group(1) + 'N·m'),
                'max_speed': (r'最高车速[^\d]*(\d+)', lambda m: m.group(1) + 'km/h'),
                'acceleration': (r'0-100[^\d]*(\d+\.?\d*)', lambda m: m.group(1) + 's'),
                'fuel_consumption': (r'油耗[^\d]*(\d+\.?\d*)', lambda m: m.group(1) + 'L/100km'),
                'wheelbase': (r'轴距[^\d]*(\d+)', lambda m: m.group(1) + 'mm'),
            }
            
            for field, (pattern, formatter) in patterns.items():
                match = re.search(pattern, page_text)
                if match:
                    extracted[field] = formatter(match)
            
            # Ищем таблицы с характеристиками
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if label and value and value != '-':
                            if '马力' in label:
                                extracted['power'] = value
                            elif '变速箱' in label:
                                extracted['transmission'] = value
                            elif '排量' in label:
                                extracted['engine_volume'] = value
            
            browser.close()
            
        except Exception as e:
            print(f"Desktop Error: {e}")
    
    return extracted


def main():
    """Главная функция тестирования"""
    
    print("\n" + "="*100)
    print("КОМПЛЕКСНЫЙ ТЕСТ ВСЕХ ИСТОЧНИКОВ CHE168")
    print("Цель: определить какие поля БД можно получить из каждого источника")
    print("="*100)
    
    car_id = TEST_CAR_ID
    
    # Тест 1: API getparamtypeitems
    print(f"\n{'='*60}")
    print("ИСТОЧНИК 1: API getparamtypeitems")
    print("="*60)
    
    api_data, api_raw = extract_from_api(car_id)
    print(f"Извлечено полей: {len(api_data)}")
    print(f"Всего параметров в API: {len(api_raw)}")
    
    # Тест 2: API getcarinfo
    print(f"\n{'='*60}")
    print("ИСТОЧНИК 2: API getcarinfo")
    print("="*60)
    
    carinfo_data = extract_from_carinfo_api(car_id)
    print(f"Извлечено полей: {len(carinfo_data)}")
    
    # Тест 3: Mobile
    print(f"\n{'='*60}")
    print("ИСТОЧНИК 3: Mobile версия (m.che168.com)")
    print("="*60)
    
    mobile_data = extract_from_mobile(car_id)
    print(f"Извлечено полей: {len(mobile_data)}")
    
    # Тест 4: Desktop
    print(f"\n{'='*60}")
    print("ИСТОЧНИК 4: Desktop версия (www.che168.com)")
    print("="*60)
    
    desktop_data = extract_from_desktop(car_id)
    print(f"Извлечено полей: {len(desktop_data)}")
    
    # Объединяем все данные
    all_sources = {
        'api_params': api_data,
        'api_carinfo': carinfo_data,
        'mobile': mobile_data,
        'desktop': desktop_data,
    }
    
    # Создаём матрицу покрытия
    print("\n" + "="*100)
    print("МАТРИЦА ПОКРЫТИЯ ПОЛЕЙ БД")
    print("="*100)
    
    # Категории полей
    field_categories = {
        'Основные': ['car_name', 'brand_name', 'series_name', 'price', 'mileage', 'city', 'year'],
        'Регистрация': ['first_registration_time', 'inspection_date', 'insurance_info'],
        'Двигатель': ['power', 'torque', 'engine_type', 'engine_code', 'engine_volume', 'cylinder_count', 'turbo_type'],
        'Трансмиссия': ['transmission', 'transmission_type', 'gear_count', 'drive_type'],
        'Размеры': ['length', 'width', 'height', 'wheelbase', 'curb_weight', 'gross_weight'],
        'Динамика': ['max_speed', 'acceleration', 'fuel_consumption'],
        'Подвеска/Тормоза': ['front_suspension', 'rear_suspension', 'front_brakes', 'rear_brakes'],
        'Колёса': ['tire_size', 'wheel_type', 'wheel_size'],
        'Безопасность': ['airbag_count', 'abs', 'esp', 'tcs', 'hill_assist', 'lane_departure', 'blind_spot_monitor'],
        'Комфорт': ['air_conditioning', 'climate_control', 'seat_heating', 'navigation', 'bluetooth'],
        'Освещение': ['headlight_type', 'fog_lights', 'led_lights', 'daytime_running'],
        'Внешний вид': ['color', 'interior_color', 'sunroof', 'panoramic_roof'],
        'Контакты': ['shop_id', 'dealer_info', 'contact_info'],
        'Изображения': ['image', 'image_gallery', 'image_count'],
        'Электро': ['battery_capacity', 'electric_range', 'charging_time'],
        'Дополнительно': ['seat_count', 'door_count', 'trunk_volume', 'fuel_tank_volume', 'warranty_info'],
    }
    
    coverage_stats = {source: 0 for source in all_sources.keys()}
    
    for category, fields in field_categories.items():
        print(f"\n{category}:")
        print("-" * 80)
        print(f"{'Поле':<25} {'API Params':<12} {'API CarInfo':<12} {'Mobile':<12} {'Desktop':<12}")
        print("-" * 80)
        
        for field in fields:
            row = f"{field:<25}"
            for source, data in all_sources.items():
                has_field = field in data and data[field]
                marker = "✓" if has_field else "-"
                row += f" {marker:<11}"
                if has_field:
                    coverage_stats[source] += 1
            print(row)
    
    # Итоговая статистика
    print("\n" + "="*100)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("="*100)
    
    total_fields = sum(len(fields) for fields in field_categories.values())
    
    for source, count in coverage_stats.items():
        pct = (count / total_fields) * 100
        print(f"{source:<20}: {count}/{total_fields} полей ({pct:.1f}%)")
    
    # Детальный вывод API данных
    print("\n" + "="*100)
    print("ДЕТАЛЬНЫЕ ДАННЫЕ ИЗ API getparamtypeitems")
    print("="*100)
    
    # Группируем по категориям
    print("\nВсе доступные параметры из API:")
    for name, value in sorted(api_raw.items()):
        db_field = API_FIELD_MAPPING.get(name, '???')
        print(f"  {name:<35} -> {db_field:<25} = {str(value)[:40]}")
    
    # Сохраняем результаты
    results = {
        'car_id': car_id,
        'sources': {
            'api_params': {'fields': len(api_data), 'raw_params': len(api_raw)},
            'api_carinfo': {'fields': len(carinfo_data)},
            'mobile': {'fields': len(mobile_data)},
            'desktop': {'fields': len(desktop_data)},
        },
        'coverage': coverage_stats,
        'api_raw_data': api_raw,
        'extracted': all_sources
    }
    
    with open('/tmp/che168_fields_analysis.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n\nРезультаты сохранены в /tmp/che168_fields_analysis.json")
    
    # Рекомендации
    print("\n" + "="*100)
    print("РЕКОМЕНДАЦИИ")
    print("="*100)
    print("""
1. API getparamtypeitems - ЛУЧШИЙ ИСТОЧНИК
   - Содержит ~200+ параметров
   - Структурированные данные
   - Быстрый доступ (1-2 сек)
   
2. API getcarinfo - ДОПОЛНЕНИЕ
   - Базовые данные о машине
   - Информация о дилере
   - Изображения
   
3. Desktop версия - РЕЗЕРВНЫЙ
   - Можно использовать для fallback
   - Медленнее (10+ сек)
   
4. Mobile версия - НЕ РЕКОМЕНДУЕТСЯ
   - Мало данных
   - Нет технических характеристик
    """)


if __name__ == "__main__":
    main()

