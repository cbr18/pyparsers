#!/usr/bin/env python3
"""
Детальный анализ структуры API getparamtypeitems
"""

import json
import re
import requests

def analyze_getparamtypeitems(car_id: int):
    """Полный анализ структуры API"""
    
    print(f"\n{'='*80}")
    print(f"ПОЛНЫЙ АНАЛИЗ API getparamtypeitems для car_id: {car_id}")
    print('='*80)
    
    url = "https://apiuscdt.che168.com/api/v1/car/getparamtypeitems"
    params = {
        "infoid": car_id,
        "deviceid": "test123456",
        "_appid": "2sc.m"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
        "Referer": f"https://m.che168.com/cardetail/index?infoid={car_id}"
    }
    
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    data = resp.json()
    
    if data.get('returncode') != 0:
        print(f"Ошибка: {data.get('message')}")
        return
    
    result = data.get('result', [])
    
    print(f"\nВсего секций: {len(result)}")
    print("\nСТРУКТУРА ДАННЫХ:")
    print("-"*60)
    
    extracted = {}
    
    for i, section in enumerate(result):
        title = section.get('title', '')
        items = section.get('data', [])
        
        print(f"\n[{i}] {title} ({len(items)} элементов)")
        
        for j, item in enumerate(items):
            name = item.get('name', '')
            content = item.get('content', '')
            
            # Выделяем важные поля
            important = any(kw in name for kw in ['马力', '功率', '发动机', '排量', '变速箱', '扭矩', '加速', '油耗', '里程'])
            marker = "★" if important else " "
            
            if content and content != '-':
                print(f"    {marker} [{j}] {name}: {content}")
                
                # Извлекаем данные
                if '马力' in name or '马力' in content:
                    power_match = re.search(r'(\d+)\s*马力', content)
                    if power_match:
                        extracted['power'] = power_match.group(1) + 'Ps'
                        print(f"         >>> Извлечено power: {extracted['power']}")
                
                if '扭矩' in name:
                    torque_match = re.search(r'(\d+)', content)
                    if torque_match:
                        extracted['torque'] = torque_match.group(1) + 'N·m'
                
                if '变速箱' in name:
                    extracted['transmission'] = content
                
                if '排量' in name or '排  量' in name:
                    extracted['displacement'] = content
                
                if '油耗' in name:
                    extracted['fuel_consumption'] = content
                
                if '加速' in name:
                    extracted['acceleration'] = content
    
    print("\n" + "="*60)
    print("ИЗВЛЕЧЁННЫЕ ДАННЫЕ:")
    print("="*60)
    for key, value in extracted.items():
        print(f"  {key}: {value}")
    
    return extracted


def extract_power_from_api(car_id: int) -> dict:
    """
    Извлекает мощность и другие данные из API getparamtypeitems
    Это функция, которую можно использовать в парсере
    """
    
    url = "https://apiuscdt.che168.com/api/v1/car/getparamtypeitems"
    params = {
        "infoid": car_id,
        "deviceid": "test123456",
        "_appid": "2sc.m"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
        "Referer": f"https://m.che168.com/cardetail/index?infoid={car_id}"
    }
    
    extracted = {}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        
        if data.get('returncode') != 0:
            return extracted
        
        result = data.get('result', [])
        
        # Маппинг китайских названий на поля
        field_mapping = {
            '最大马力(Ps)': 'power',
            '最大功率(kW)': 'power_kw',
            '最大扭矩(N·m)': 'torque',
            '变速箱': 'transmission',
            '排量(mL)': 'displacement',
            '排  量': 'displacement',
            '综合油耗(L/100km)': 'fuel_consumption',
            '百公里油耗': 'fuel_consumption',
            '官方0-100km/h加速(s)': 'acceleration',
            '长(mm)': 'length',
            '宽(mm)': 'width',
            '高(mm)': 'height',
            '轴距(mm)': 'wheelbase',
            '整备质量(kg)': 'curb_weight',
            '座位数': 'seat_count',
            '车门数': 'door_count',
            '发动机': 'engine_info',
            '前制动器类型': 'front_brakes',
            '后制动器类型': 'rear_brakes',
            '前悬架类型': 'front_suspension',
            '后悬架类型': 'rear_suspension',
            '驱动方式': 'drive_type',
            '前轮胎规格': 'tire_size',
        }
        
        for section in result:
            items = section.get('data', [])
            for item in items:
                name = item.get('name', '').strip()
                content = item.get('content', '').strip()
                
                if not content or content == '-':
                    continue
                
                # Прямой маппинг
                if name in field_mapping:
                    field = field_mapping[name]
                    extracted[field] = content
                
                # Извлекаем мощность из content типа "2.0T 220马力 L4"
                if '马力' in content and 'power' not in extracted:
                    power_match = re.search(r'(\d+)\s*马力', content)
                    if power_match:
                        extracted['power'] = power_match.group(1) + 'Ps'
                
                # Извлекаем engine_info
                if name == '发动机' or '发动机' in name:
                    extracted['engine_info'] = content
                    # Также извлекаем мощность если есть
                    if '马力' in content and 'power' not in extracted:
                        power_match = re.search(r'(\d+)\s*马力', content)
                        if power_match:
                            extracted['power'] = power_match.group(1) + 'Ps'
        
        return extracted
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return extracted


def test_multiple_cars():
    """Тест на нескольких машинах"""
    
    test_ids = [56305293, 56915531, 56915528, 56915533]
    
    print("\n" + "="*80)
    print("ТЕСТ ИЗВЛЕЧЕНИЯ НА НЕСКОЛЬКИХ МАШИНАХ")
    print("="*80)
    
    results = []
    
    for car_id in test_ids:
        print(f"\n--- car_id: {car_id} ---")
        data = extract_power_from_api(car_id)
        
        power = data.get('power', 'НЕ НАЙДЕНО')
        engine = data.get('engine_info', 'НЕ НАЙДЕНО')
        
        print(f"  power: {power}")
        print(f"  engine_info: {engine}")
        
        results.append({
            'car_id': car_id,
            'power': power,
            'engine_info': engine,
            'all_fields': len(data)
        })
    
    print("\n" + "="*80)
    print("ИТОГИ:")
    print("="*80)
    
    success = sum(1 for r in results if r['power'] != 'НЕ НАЙДЕНО')
    print(f"Успешно извлечено power: {success}/{len(results)}")
    
    return results


if __name__ == "__main__":
    # Полный анализ одной машины
    analyze_getparamtypeitems(56305293)
    
    # Тест на нескольких машинах
    test_multiple_cars()

