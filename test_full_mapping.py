#!/usr/bin/env python3
import re
from bs4 import BeautifulSoup

# Загружаем HTML
html_path = '/home/alex/CarsParser/samples/detailche/после того как что-то нажал/车源详情.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

print("=" * 80)
print("ПОЛНЫЙ МАППИНГ ПОЛЕЙ ИЗ HTML В domain.Car")
print("=" * 80)

# ПОЛНЫЙ СПИСОК МЕТОК ИЗ CHE168, которые нужно искать
# Основываясь на структуре domain.Car
all_label_matches = [
    # Основные характеристики
    ('发动机', 'engine_type'),
    ('变速箱', 'transmission'),
    ('百公里油耗', 'fuel_consumption'),
    ('燃料形式', 'fuel_type'),
    ('排量', 'engine_volume'),
    ('排量(L)', 'engine_volume'),
    
    # Мощность и производительность
    ('最大马力(Ps)', 'power'),
    ('最大马力', 'power'),
    ('最大功率(kW)', 'power_kw'),
    ('最大功率', 'power_kw'),
    ('最大扭矩(N·m)', 'torque'),
    ('最大扭矩', 'torque'),
    ('加速时间', 'acceleration'),
    ('0-100km/h加速', 'acceleration'),
    ('最高车速', 'max_speed'),
    ('排放标准', 'emission_standard'),
    
    # Размеры
    ('长x宽x高', 'dimensions'),  # Обрабатываем отдельно
    ('长*宽*高', 'dimensions'),
    ('车身尺寸', 'dimensions'),
    ('轴距', 'wheelbase'),
    ('轴距(mm)', 'wheelbase'),
    ('整备质量', 'curb_weight'),
    ('整备质量(kg)', 'curb_weight'),
    ('车身重量', 'curb_weight'),
    ('总质量', 'gross_weight'),
    
    # Двигатель
    ('发动机型号', 'engine_code'),
    ('气缸数', 'cylinder_count'),
    ('气缸排列形式', 'cylinder_arrangement'),
    ('每缸气门数', 'valve_count'),
    ('压缩比', 'compression_ratio'),
    ('进气形式', 'turbo_type'),
    
    # Трансмиссия
    ('变速箱类型', 'transmission_type'),
    ('档位个数', 'gear_count'),
    ('驱动方式', 'drive_type'),
    ('四驱形式', 'differential_type'),
    
    # Подвеска и тормоза
    ('前悬架类型', 'front_suspension'),
    ('后悬架类型', 'rear_suspension'),
    ('前制动器类型', 'front_brakes'),
    ('后制动器类型', 'rear_brakes'),
    ('驻车制动类型', 'brake_system'),
    
    # Колеса
    ('轮胎规格', 'tire_size'),
    ('前轮胎规格', 'front_tire_size'),
    ('后轮胎规格', 'rear_tire_size'),
    ('轮圈材质', 'wheel_type'),
    
    # Безопасность
    ('安全气囊数量', 'airbag_count'),
    ('主/副驾驶座安全气囊', 'airbag_front'),
    ('ABS防抱死', 'abs'),
    ('车身稳定控制', 'esp'),
    ('牵引力控制', 'tcs'),
    ('上坡辅助', 'hill_assist'),
    ('陡坡缓降', 'hill_descent'),
    ('并线辅助', 'blind_spot_monitor'),
    ('车道偏离预警', 'lane_departure'),
    
    # Электро (для EV)
    ('电池容量', 'battery_capacity'),
    ('纯电续航', 'electric_range'),
    ('快充时间', 'fast_charge_time'),
    ('慢充时间', 'charging_time'),
    
    # Комфорт
    ('空调', 'air_conditioning'),
    ('空调类型', 'climate_control'),
    ('座椅加热', 'seat_heating'),
    ('座椅通风', 'seat_ventilation'),
    ('座椅按摩', 'seat_massage'),
    ('方向盘加热', 'steering_wheel_heating'),
    
    # Мультимедиа
    ('GPS导航', 'navigation'),
    ('导航系统', 'navigation'),
    ('音响品牌', 'audio_system'),
    ('扬声器数量', 'speakers_count'),
    ('蓝牙', 'bluetooth'),
    ('蓝牙/车载电话', 'bluetooth'),
    ('车载电话', 'bluetooth'),
    ('USB接口', 'usb'),
    ('AUX接口', 'aux'),
    
    # Освещение
    ('大灯类型', 'headlight_type'),
    ('前大灯', 'headlight_type'),
    ('前大灯类型', 'headlight_type'),
    ('雾灯', 'fog_lights'),
    ('LED日间行车灯', 'daytime_running'),
    
    # Внешний вид и интерьер
    ('内饰颜色', 'interior_color'),
    ('外观颜色', 'exterior_color'),
    ('车身颜色', 'exterior_color'),
    ('座椅材质', 'upholstery'),
    ('天窗类型', 'sunroof'),
    ('全景天窗', 'panoramic_roof'),
    
    # Дополнительные
    ('座位数', 'seat_count'),
    ('座椅数', 'seat_count'),
    ('门数', 'door_count'),
    ('行李箱容积', 'trunk_volume'),
    ('后备箱容积', 'trunk_volume'),
    ('油箱容积', 'fuel_tank_volume'),
    
    # История (из раздела 档案)
    ('上牌时间', 'registration_date'),
    ('表显里程', 'mileage'),
    ('所在地区', 'city'),
    ('过户次数', 'owner_count'),
    ('年检到期', 'inspection_date'),
    ('保险到期', 'insurance_info'),
    ('保修信息', 'warranty_info'),
]

data = {}

# Способ 1: css-1rynq56, метка после значения
all_text_divs = soup.find_all('div', class_=lambda x: x and 'css-1rynq56' in str(x))
print(f"\n1. Поиск в div'ах с css-1rynq56: {len(all_text_divs)} элементов")

label_texts = [label for label, _ in all_label_matches]
for div in all_text_divs:
    div_text = div.get_text(strip=True)
    
    if div_text in label_texts:
        parent = div.find_parent('div')
        if parent:
            siblings = parent.find_all('div', class_=lambda x: x and 'css-1rynq56' in str(x), recursive=False)
            
            for i, sibling in enumerate(siblings):
                if sibling == div and i > 0:
                    value_text = siblings[i-1].get_text(strip=True)
                    label_text = div_text
                    
                    for mapping_label, field_name in all_label_matches:
                        if data.get(field_name):
                            continue
                        if label_text == mapping_label or label_text in mapping_label or mapping_label in label_text:
                            data[field_name] = value_text
                            print(f"  ✓ {field_name}: {value_text}")
                            break
                    break

# Способ 2: любые div, метка перед значением
print(f"\n2. Поиск в любых div'ах (метка перед значением)")
all_divs = soup.find_all('div')

found_count = 0
for div in all_divs:
    div_text = div.get_text(strip=True)
    
    for label_pattern, field_name in all_label_matches:
        if div_text == label_pattern:
            if data.get(field_name):
                continue
            
            parent = div.find_parent('div')
            if parent:
                children = parent.find_all('div', recursive=False)
                
                try:
                    label_idx = children.index(div)
                    if label_idx + 1 < len(children):
                        value_div = children[label_idx + 1]
                        value_text = value_div.get_text(strip=True)
                        
                        if value_text and value_text not in label_texts:
                            data[field_name] = value_text
                            print(f"  ✓ {field_name}: {value_text}")
                            found_count += 1
                except ValueError:
                    pass

print(f"\n  Найдено {found_count} новых полей способом 2")

# Специальная обработка для dimensions
if 'dimensions' in data:
    dims_text = data['dimensions']
    dims = re.findall(r'(\d+)', dims_text)
    if len(dims) >= 3:
        data['length'] = dims[0] + 'mm'
        data['width'] = dims[1] + 'mm'
        data['height'] = dims[2] + 'mm'
        print(f"\n  Размеры разобраны: {data['length']} x {data['width']} x {data['height']}")

# Специальная обработка для mileage (убираем "万公里" и преобразуем)
if 'mileage' in data:
    mileage_text = data['mileage']
    match = re.search(r'(\d+\.?\d*)万公里', mileage_text)
    if match:
        mileage_wan = float(match.group(1))
        mileage_km = int(mileage_wan * 10000)
        data['mileage'] = str(mileage_km)
        print(f"\n  Пробег преобразован: {mileage_text} -> {mileage_km} км")

# Специальная обработка для year (из даты регистрации)
if 'registration_date' in data:
    reg_date = data['registration_date']
    year_match = re.search(r'(\d{4})', reg_date)
    if year_match:
        data['year'] = year_match.group(1)
        print(f"\n  Год из даты регистрации: {data['year']}")

print("\n" + "=" * 80)
print("ИТОГОВЫЙ РЕЗУЛЬТАТ")
print("=" * 80)
print(f"\nВсего полей извлечено: {len(data)}")
print("\nПо категориям:")

categories = {
    'Основные': ['engine_type', 'transmission', 'fuel_type', 'fuel_consumption', 'engine_volume', 'year', 'mileage', 'city'],
    'Мощность': ['power', 'power_kw', 'torque', 'acceleration', 'max_speed', 'emission_standard'],
    'Размеры': ['length', 'width', 'height', 'wheelbase', 'curb_weight', 'gross_weight'],
    'Двигатель': ['engine_code', 'cylinder_count', 'valve_count', 'compression_ratio', 'turbo_type'],
    'Трансмиссия': ['transmission_type', 'gear_count', 'drive_type'],
    'Подвеска/Тормоза': ['front_suspension', 'rear_suspension', 'front_brakes', 'rear_brakes'],
    'Безопасность': ['airbag_count', 'abs', 'esp', 'tcs', 'hill_assist', 'blind_spot_monitor', 'lane_departure'],
    'Комфорт': ['air_conditioning', 'climate_control', 'seat_heating', 'navigation', 'bluetooth', 'usb'],
    'Интерьер': ['interior_color', 'exterior_color', 'seat_count', 'trunk_volume'],
    'История': ['registration_date', 'owner_count', 'warranty_info', 'insurance_info'],
}

for category, fields in categories.items():
    found_in_category = [f for f in fields if f in data]
    if found_in_category:
        print(f"\n{category}:")
        for field in found_in_category:
            print(f"  {field:25s}: {data[field]}")

print("\n" + "=" * 80)

