"""
Тестовые данные для демонстрации работы переводчика
"""
import json

# Тестовые данные автомобилей на китайском языке
TEST_CARS_DATA = [
    {
        "title": "极狐阿尔法S 2023款 708S+",
        "car_name": "极狐阿尔法S",
        "brand_name": "极狐",
        "series_name": "阿尔法S",
        "city": "北京",
        "car_source_city_name": "北京市",
        "description": "全新极狐阿尔法S，续航708公里，智能驾驶辅助系统",
        "color": "白色",
        "transmission": "自动",
        "fuel_type": "纯电动",
        "engine_volume": "0L",
        "body_type": "轿车",
        "drive_type": "前驱",
        "condition": "新车"
    },
    {
        "title": "蔚来ES8 2024款 100kWh",
        "car_name": "蔚来ES8",
        "brand_name": "蔚来",
        "series_name": "ES8",
        "city": "上海",
        "car_source_city_name": "上海市",
        "description": "豪华纯电SUV，7座布局，NOMI智能助手",
        "color": "蓝色",
        "transmission": "自动",
        "fuel_type": "纯电动",
        "engine_volume": "0L",
        "body_type": "SUV",
        "drive_type": "四驱",
        "condition": "准新车"
    },
    {
        "title": "理想L9 2023款 Max",
        "car_name": "理想L9",
        "brand_name": "理想",
        "series_name": "L9",
        "city": "深圳",
        "car_source_city_name": "深圳市",
        "description": "增程式电动SUV，6座布局，智能座舱",
        "color": "银色",
        "transmission": "自动",
        "fuel_type": "增程式",
        "engine_volume": "1.5L",
        "body_type": "SUV",
        "drive_type": "四驱",
        "condition": "新车"
    },
    {
        "title": "小鹏P7 2023款 670N+",
        "car_name": "小鹏P7",
        "brand_name": "小鹏",
        "series_name": "P7",
        "city": "广州",
        "car_source_city_name": "广州市",
        "description": "智能电动轿车，XPILOT自动驾驶系统",
        "color": "红色",
        "transmission": "自动",
        "fuel_type": "纯电动",
        "engine_volume": "0L",
        "body_type": "轿车",
        "drive_type": "后驱",
        "condition": "准新车"
    },
    {
        "title": "比亚迪汉EV 2024款 创世版",
        "car_name": "比亚迪汉EV",
        "brand_name": "比亚迪",
        "series_name": "汉EV",
        "city": "杭州",
        "car_source_city_name": "杭州市",
        "description": "旗舰纯电轿车，刀片电池技术，豪华内饰",
        "color": "黑色",
        "transmission": "自动",
        "fuel_type": "纯电动",
        "engine_volume": "0L",
        "body_type": "轿车",
        "drive_type": "四驱",
        "condition": "新车"
    }
]

# Тестовые данные для JSON перевода
TEST_JSON_DATA = {
    "brand": "极狐",
    "model": "阿尔法S",
    "city": "北京",
    "description": "全新极狐阿尔法S，续航708公里",
    "features": ["智能驾驶", "自动泊车", "语音控制"],
    "specs": {
        "range": "708公里",
        "battery": "93.6kWh",
        "acceleration": "4.2秒"
    }
}

# Тестовые данные для батчевого перевода
TEST_BATCH_DATA = [
    {"text": "极狐阿尔法S"},
    {"text": "蔚来ES8"},
    {"text": "理想L9"},
    {"text": "小鹏P7"},
    {"text": "比亚迪汉EV"},
    {"text": "北京"},
    {"text": "上海"},
    {"text": "深圳"},
    {"text": "纯电动"},
    {"text": "智能驾驶"}
]

def save_test_data():
    """Сохраняет тестовые данные в JSON файлы"""
    
    # Сохраняем данные автомобилей
    with open('test_cars.json', 'w', encoding='utf-8') as f:
        json.dump(TEST_CARS_DATA, f, ensure_ascii=False, indent=2)
    
    # Сохраняем JSON данные
    with open('test_json.json', 'w', encoding='utf-8') as f:
        json.dump(TEST_JSON_DATA, f, ensure_ascii=False, indent=2)
    
    # Сохраняем батчевые данные
    with open('test_batch.json', 'w', encoding='utf-8') as f:
        json.dump(TEST_BATCH_DATA, f, ensure_ascii=False, indent=2)
    
    print("Тестовые данные сохранены:")
    print("- test_cars.json - данные автомобилей")
    print("- test_json.json - JSON данные")
    print("- test_batch.json - батчевые данные")

if __name__ == "__main__":
    save_test_data()
