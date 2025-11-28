#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание мастер-списка брендов автомобилей.
Генерирует SQL-файл с чистыми, уникальными брендами.
"""

import os
import sys
import uuid
from typing import Dict, List, Set, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Подключение к БД
db_host = os.getenv('POSTGRES_HOST', 'localhost')
if db_host == 'postgres':
    db_host = 'localhost'
db_port = os.getenv('POSTGRES_PORT', '4827')
if db_port == '5432' or not db_port:
    db_port = '4827'

DB_CONFIG = {
    'host': db_host,
    'port': db_port,
    'database': os.getenv('POSTGRES_DB', 'carsdb'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
}

# =============================================================================
# МАСТЕР-СПИСОК БРЕНДОВ
# Формат: (name_en, name_cn, aliases)
# =============================================================================
MASTER_BRANDS = [
    # Немецкие бренды
    ("BMW", "宝马", ["巴伐利亚发动机制造厂"]),
    ("Mercedes-Benz", "奔驰", ["Mercedes", "MB", "梅赛德斯", "梅赛德斯-奔驰", "Benz"]),
    ("Audi", "奥迪", []),
    ("Volkswagen", "大众", ["VW", "福斯"]),
    ("Porsche", "保时捷", []),
    ("MINI", "迷你", ["Mini", "宝马MINI"]),
    ("smart", "精灵", ["Smart", "smart精灵"]),
    ("Maybach", "迈巴赫", ["Mercedes-Maybach"]),
    
    # Японские бренды
    ("Toyota", "丰田", ["TOYOTA"]),
    ("Honda", "本田", ["HONDA"]),
    ("Nissan", "日产", ["NISSAN", "尼桑"]),
    ("Mazda", "马自达", ["MAZDA"]),
    ("Lexus", "雷克萨斯", ["凌志"]),
    ("Infiniti", "英菲尼迪", []),
    ("Acura", "讴歌", []),
    ("Subaru", "斯巴鲁", []),
    ("Mitsubishi", "三菱", []),
    ("Suzuki", "铃木", []),
    ("Isuzu", "五十铃", []),
    
    # Американские бренды
    ("Ford", "福特", ["FORD"]),
    ("Chevrolet", "雪佛兰", ["Chevy"]),
    ("Buick", "别克", []),
    ("Cadillac", "凯迪拉克", []),
    ("GMC", "通用", []),
    ("Lincoln", "林肯", []),
    ("Jeep", "吉普", []),
    ("Dodge", "道奇", []),
    ("Chrysler", "克莱斯勒", []),
    ("Tesla", "特斯拉", []),
    ("RAM", "公羊", []),
    
    # Корейские бренды
    ("Hyundai", "现代", ["modern", "北京现代"]),
    ("Kia", "起亚", ["KIA"]),
    ("Genesis", "捷尼赛思", ["Genisys"]),
    
    # Европейские бренды (прочие)
    ("Volvo", "沃尔沃", []),
    ("Land Rover", "路虎", ["LandRover"]),
    ("Jaguar", "捷豹", []),
    ("Peugeot", "标致", ["PEUGEOT"]),
    ("Citroen", "雪铁龙", ["Citroën"]),
    ("Renault", "雷诺", []),
    ("Skoda", "斯柯达", ["Škoda"]),
    ("Alfa Romeo", "阿尔法罗密欧", ["Alfa"]),
    ("Fiat", "菲亚特", []),
    
    # Премиум/Люкс бренды
    ("Bentley", "宾利", []),
    ("Rolls-Royce", "劳斯莱斯", ["Rolls Royce"]),
    ("Ferrari", "法拉利", []),
    ("Lamborghini", "兰博基尼", ["Lambo"]),
    ("Maserati", "玛莎拉蒂", []),
    ("Aston Martin", "阿斯顿马丁", ["Aston"]),
    ("McLaren", "迈凯伦", []),
    ("Lotus", "路特斯", ["Lotus Sports Car"]),
    
    # Китайские бренды - основные
    ("BYD", "比亚迪", ["Build Your Dreams"]),
    ("Geely", "吉利", ["Geely Automobile", "吉利汽车"]),
    ("Geely Galaxy", "吉利银河", ["银河"]),
    ("Chery", "奇瑞", ["CHERY"]),
    ("Changan", "长安", ["Chang'an", "长安汽车", "CHANGAN"]),
    ("Great Wall", "长城", ["GWM"]),
    ("Haval", "哈弗", ["HAVAL"]),
    ("WEY", "魏牌", ["Wei Pai", "WEY魏牌"]),
    ("Tank", "坦克", ["tank", "TANK"]),
    ("Hongqi", "红旗", ["Red flag", "红旗汽车"]),
    ("GAC Trumpchi", "广汽传祺", ["传祺", "Trumpchi"]),
    ("Roewe", "荣威", []),
    ("MG", "名爵", ["MG名爵"]),
    ("Baojun", "宝骏", []),
    ("Wuling", "五菱", ["Wuling Automobile", "五菱汽车"]),
    
    # Китайские бренды - электромобили
    ("NIO", "蔚来", ["Weilai", "NIO蔚来"]),
    ("XPeng", "小鹏", ["Xiaopeng", "Xiaopeng Motors", "小鹏汽车"]),
    ("Li Auto", "理想", ["Ideal car", "理想汽车", "LI"]),
    ("Zeekr", "极氪", ["Extremely krypton", "ZEEKR"]),
    ("Leapmotor", "零跑", ["Zero-running car", "零跑汽车"]),
    ("Neta", "哪吒", ["Nezha", "Nezha Automobile", "哪吒汽车"]),
    ("Denza", "腾势", ["DENZA"]),
    ("AION", "埃安", ["Aian", "广汽埃安", "GAC AION"]),
    ("Avatr", "阿维塔", ["Avita"]),
    ("IM Motors", "智己", ["Zhiji Automobile", "智己汽车"]),
    ("Rising Auto", "飞凡", ["Feifan Automobile", "飞凡汽车"]),
    ("Voyah", "岚图", ["Lan Tu", "VOYAH"]),
    ("HiPhi", "高合", ["Gao He"]),
    ("Xiaomi Auto", "小米汽车", ["Xiaomi Car", "小米SU7"]),
    ("Deepal", "深蓝", ["Dark blue car", "深蓝汽车"]),
    
    # Китайские бренды - другие
    ("Changan Auchan", "长安欧尚", ["欧尚"]),
    ("Changan Qiyuan", "长安启源", ["启源"]),
    ("Lynk & Co", "领克", ["Lynk", "LYNK&CO"]),
    ("Exeed", "星途", ["Astral Path", "EXEED"]),
    ("Jetour", "捷途", ["Jietu", "JETOUR"]),
    ("Qichen", "启辰", ["Venucia"]),
    ("FAW Bestune", "奔腾", ["Pentium", "一汽奔腾"]),
    ("BAIC", "北汽", ["Beijing Automobile", "北京汽车"]),
    ("Beijing Offroad", "北京越野", ["Beijing off-road", "BJ"]),
    ("Dongfeng", "东风", ["DongFeng", "东风汽车"]),
    ("Dongfeng Fengshen", "东风风神", ["风神"]),
    ("Dongfeng Fengxing", "东风风行", ["Dongfeng popular", "风行"]),
    ("Dongfeng Scenery", "东风风光", ["风光"]),
    ("JAC", "江淮", ["Jianghuai", "Jianghuai Ruifeng"]),
    ("JMC", "江铃", ["Jiangling"]),
    ("SAIC Maxus", "上汽大通", ["Chase", "大通"]),
    ("Iveco", "依维柯", []),
    ("Foton", "福田", ["Fukuda"]),
    ("Leopard", "方程豹", ["豹"]),
    ("iCAR", "iCAR", ["艾卡"]),
    ("Chery Fengyun", "奇瑞风云", ["风云"]),
    ("Euler", "欧拉", ["ORA"]),
    ("Geely Geometry", "几何汽车", ["Geometry"]),
    ("Haima", "海马", ["Seahorse", "海马汽车"]),
    ("Zotye", "众泰", []),
    ("Soueast", "东南", ["southeast", "东南汽车"]),
    ("Cowin", "凯翼", ["Kaiyi"]),
    ("Golden Dragon", "金龙", ["金龙客车"]),
    ("Yutong", "宇通", ["宇通客车"]),
    ("SWM", "斯威", ["SWM Sway Motors"]),
    
    # Другие/Специальные
    ("AITO", "AITO", ["问界", "AITO asks the world", "Ask the world"]),
    ("Lorinser", "劳伦士", []),
    ("ARCFOX", "极狐", ["ARCFOX Extreme Fox", "Polar fox"]),
    ("Polestar", "极星", []),
    ("Lufeng", "陆风", []),
    ("Cheetah", "猎豹", ["Cheetah Cars", "猎豹汽车"]),
    ("Jetta", "捷达", []),  # VW sub-brand in China
    ("BAIC Magic Speed", "北汽幻速", ["幻速"]),
    ("Weimar", "威马", ["Weima Automobile", "威马汽车"]),
    ("Skyworth", "创维", ["Skyworth Motors", "创维汽车"]),
    ("Weltmeister", "WM", ["威马"]),
    ("Gold Cup", "金杯", ["华晨金杯"]),
    ("Zhidou", "知豆", []),
    
    # Дополнительные бренды
    ("Qoros", "观致", ["观致汽车"]),
    ("Hanteng", "汉腾", ["Hanteng Motors", "汉腾汽车"]),
    ("SRM", "鑫源", ["SRM Xinyuan"]),
    ("SERES", "赛力斯", ["赛力斯汽车"]),
    ("Yuancheng", "远程", ["Remote car", "远程汽车"]),
    ("GAC Haobo", "广汽昊铂", ["Haobo", "昊铂"]),
    ("Yingzhi", "英致", ["Yingshipai"]),
    ("Enranger", "恩途", ["Happy Road"]),
    ("212", "212", ["北京212", "BJ212"]),
    ("Zhijie", "智界", ["Intellectual world", "智界汽车"]),
    ("Sharp World", "极界", ["Sharp World"]),  # Sharp界
    ("Hengchi", "恒驰", ["恒大汽车"]),
    ("GAC Enpulse", "埃安", ["Aian"]),  # already have AION
    ("Dayun", "大运", ["Universiade", "大运汽车"]),
    ("BAW", "北汽制造", ["Beijing Automobile Works", "北京汽车制造"]),
    ("Trumpchi", "传祺", ["GAC Trumpchi"]),  # alias for GAC Trumpchi
    ("Hongguang", "宏光", ["Wuling Hongguang"]),  # Wuling sub-brand
    ("Model", "Model", []),  # Tesla Model series often appears alone
]


def escape_sql(s: str) -> str:
    """Экранирует строку для SQL"""
    if not s:
        return ''
    return s.replace("'", "''")


def generate_brands_sql():
    """Генерирует SQL для создания таблицы брендов"""
    
    # Собираем все бренды
    brands_data = []
    seen_names = set()  # Для проверки дубликатов
    
    for name_en, name_cn, aliases in MASTER_BRANDS:
        # Проверяем на дубликаты
        key = name_en.lower()
        if key in seen_names:
            print(f"⚠️  Дубликат: {name_en}")
            continue
        seen_names.add(key)
        
        # Формируем список алиасов
        all_aliases = set()
        all_aliases.add(name_cn)  # Китайское название как алиас
        all_aliases.update(aliases)
        
        # Убираем пустые и дубликаты основного имени
        all_aliases.discard('')
        all_aliases.discard(name_en)
        all_aliases.discard(name_en.lower())
        
        aliases_str = ','.join(sorted(all_aliases)) if all_aliases else None
        
        brands_data.append({
            'id': str(uuid.uuid4()),
            'name': name_en,
            'orig_name': name_cn,
            'aliases': aliases_str
        })
    
    # Генерируем SQL
    output_file = 'brands_master.sql'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- =============================================================================\n")
        f.write("-- МАСТЕР-СПИСОК БРЕНДОВ АВТОМОБИЛЕЙ\n")
        f.write("-- Сгенерировано автоматически\n")
        f.write("-- =============================================================================\n")
        f.write("-- ВАЖНО: Перед выполнением сделайте бэкап!\n")
        f.write("-- =============================================================================\n\n")
        
        f.write("BEGIN;\n\n")
        
        # Удаляем все существующие бренды (hard delete для чистоты)
        f.write("-- Удаление всех существующих брендов\n")
        f.write("DELETE FROM brands;\n\n")
        
        # Вставляем новые бренды
        f.write("-- Вставка мастер-списка брендов\n")
        f.write("INSERT INTO brands (id, name, orig_name, aliases, created_at, updated_at)\n")
        f.write("VALUES\n")
        
        values = []
        for brand in brands_data:
            name_sql = f"'{escape_sql(brand['name'])}'"
            orig_name_sql = f"'{escape_sql(brand['orig_name'])}'"
            aliases_sql = f"'{escape_sql(brand['aliases'])}'" if brand['aliases'] else 'NULL'
            
            values.append(f"    ('{brand['id']}', {name_sql}, {orig_name_sql}, {aliases_sql}, NOW(), NOW())")
        
        f.write(",\n".join(values))
        f.write(";\n\n")
        
        f.write("COMMIT;\n\n")
        
        # Проверка
        f.write("-- Проверка результатов\n")
        f.write("SELECT COUNT(*) as total_brands FROM brands;\n")
        f.write("SELECT name, orig_name, aliases FROM brands ORDER BY name LIMIT 20;\n")
    
    print(f"✅ Создано {len(brands_data)} брендов")
    print(f"✅ SQL файл: {output_file}")
    
    return brands_data


def generate_brand_mapping_sql():
    """Генерирует SQL для обновления mybrand_id в cars"""
    
    output_file = 'update_cars_mybrand.sql'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- =============================================================================\n")
        f.write("-- ОБНОВЛЕНИЕ ССЫЛОК НА БРЕНДЫ В ТАБЛИЦЕ CARS\n")
        f.write("-- =============================================================================\n\n")
        
        f.write("BEGIN;\n\n")
        
        f.write("-- Обновление mybrand_id на основе brand_name\n")
        f.write("UPDATE cars c\n")
        f.write("SET mybrand_id = b.id\n")
        f.write("FROM brands b\n")
        f.write("WHERE (\n")
        f.write("    LOWER(c.brand_name) = LOWER(b.name)\n")
        f.write("    OR LOWER(c.brand_name) = LOWER(b.orig_name)\n")
        f.write("    OR b.aliases ILIKE '%' || c.brand_name || '%'\n")
        f.write(");\n\n")
        
        f.write("COMMIT;\n\n")
        
        f.write("-- Проверка: машины без mybrand_id\n")
        f.write("SELECT brand_name, COUNT(*) as cnt\n")
        f.write("FROM cars\n")
        f.write("WHERE mybrand_id IS NULL AND brand_name IS NOT NULL AND brand_name != ''\n")
        f.write("GROUP BY brand_name\n")
        f.write("ORDER BY cnt DESC\n")
        f.write("LIMIT 50;\n")
    
    print(f"✅ SQL файл для обновления cars: {output_file}")


def print_recommendations():
    """Выводит рекомендации по предотвращению дублирования"""
    
    print("\n" + "=" * 80)
    print("РЕКОМЕНДАЦИИ ПО ПРЕДОТВРАЩЕНИЮ ДУБЛИРОВАНИЯ БРЕНДОВ")
    print("=" * 80)
    
    print("""
1. УНИКАЛЬНЫЙ ИНДЕКС НА ТАБЛИЦУ BRANDS:
   ```sql
   CREATE UNIQUE INDEX IF NOT EXISTS idx_brands_name_lower 
   ON brands (LOWER(name)) WHERE deleted_at IS NULL;
   
   CREATE UNIQUE INDEX IF NOT EXISTS idx_brands_orig_name_lower 
   ON brands (LOWER(orig_name)) WHERE deleted_at IS NULL;
   ```

2. ФУНКЦИЯ ПОИСКА ИЛИ СОЗДАНИЯ БРЕНДА (в Go/datahub):
   ```go
   func (r *BrandRepository) FindOrCreate(ctx context.Context, brandName string) (*domain.Brand, error) {
       // Сначала ищем существующий бренд
       brand, err := r.GetByOrigName(ctx, brandName)
       if err != nil {
           return nil, err
       }
       if brand != nil {
           return brand, nil  // Нашли существующий
       }
       
       // Не нашли - НЕ создаем новый, возвращаем nil или ошибку
       // Все новые бренды должны добавляться только вручную!
       return nil, nil
   }
   ```

3. ИЗМЕНИТЬ ЛОГИКУ ПАРСЕРОВ:
   - Парсеры НЕ должны создавать новые бренды автоматически
   - При получении неизвестного brand_name - оставлять mybrand_id = NULL
   - Периодически анализировать машины с mybrand_id = NULL и добавлять 
     недостающие бренды вручную

4. НОРМАЛИЗАЦИЯ brand_name В ПАРСЕРАХ:
   - Удалять модели из brand_name (если "BMW 3 Series" -> "BMW")
   - Приводить к каноническому виду (если "宝马" -> "BMW")

5. CRON-ЗАДАЧА ДЛЯ СВЯЗЫВАНИЯ:
   ```bash
   # Раз в день запускать скрипт, который:
   # 1. Находит машины с mybrand_id = NULL
   # 2. Пытается найти бренд по brand_name/aliases
   # 3. Логирует неизвестные brand_name для ручной обработки
   ```

6. ВАЛИДАЦИЯ В API:
   - Эндпоинт /cars должен принимать только mybrand_id из списка существующих
   - Не позволять создавать новые бренды через API

7. МОНИТОРИНГ:
   - Алерт если появляются новые уникальные brand_name которых нет в brands
   - Дашборд с количеством машин без mybrand_id
""")


def main():
    print("=" * 80)
    print("СОЗДАНИЕ МАСТЕР-СПИСКА БРЕНДОВ")
    print("=" * 80)
    print()
    
    # Генерируем SQL для брендов
    brands_data = generate_brands_sql()
    
    # Генерируем SQL для обновления cars
    generate_brand_mapping_sql()
    
    # Выводим рекомендации
    print_recommendations()
    
    print("\n" + "=" * 80)
    print("ГОТОВО!")
    print("=" * 80)
    print(f"\nФайлы созданы:")
    print(f"  1. brands_master.sql - основной SQL для заполнения таблицы brands")
    print(f"  2. update_cars_mybrand.sql - SQL для обновления mybrand_id в cars")
    print(f"\nПорядок выполнения:")
    print(f"  1. Сделайте бэкап БД")
    print(f"  2. Выполните brands_master.sql")
    print(f"  3. Выполните update_cars_mybrand.sql")
    print(f"  4. Проверьте машины без mybrand_id и при необходимости добавьте бренды")


if __name__ == '__main__':
    main()

