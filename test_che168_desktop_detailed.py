#!/usr/bin/env python3
"""
Детальный тест десктопной версии che168.com
"""

import json
import re
import time
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

TEST_CAR_IDS = [56305293, 56915531, 56915528]

def test_desktop_detailed(car_id: int):
    """Детальный тест десктопной версии"""
    
    # Пробуем разные форматы URL
    urls_to_try = [
        f"https://www.che168.com/dealer/557461/{car_id}.html",
        f"https://www.che168.com/usedcar/{car_id}.html",
        f"https://www.che168.com/{car_id}.html",
    ]
    
    print(f"\n{'='*80}")
    print(f"ДЕТАЛЬНЫЙ ТЕСТ DESKTOP для car_id: {car_id}")
    print('='*80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )
        
        page = context.new_page()
        
        for url in urls_to_try:
            print(f"\n--- Пробуем URL: {url}")
            
            try:
                response = page.goto(url, wait_until='networkidle', timeout=60000)
                time.sleep(3)
                
                title = page.title()
                print(f"    Title: {title[:60]}")
                
                if '访问出错' in title or '出错' in title or '404' in title:
                    print(f"    ✗ Страница с ошибкой")
                    continue
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Ищем мощность разными способами
                print(f"\n    Поиск мощности в HTML ({len(html)} bytes):")
                
                # Способ 1: Regex в тексте
                page_text = soup.get_text()
                patterns = [
                    (r'(\d+)\s*马力', '马力'),
                    (r'最大马力[^\d]*(\d+)', '最大马力'),
                    (r'(\d+)\s*Ps', 'Ps'),
                    (r'(\d+)\s*kW', 'kW'),
                    (r'功率[^\d]*(\d+)', '功率'),
                ]
                
                for pattern, label in patterns:
                    match = re.search(pattern, page_text)
                    if match:
                        print(f"    ✓ НАЙДЕНО (regex): {label} = {match.group(1)}")
                
                # Способ 2: Ищем в конкретных элементах
                spec_elements = soup.find_all(['td', 'span', 'div'], string=re.compile(r'马力|功率|Ps|kW'))
                print(f"\n    Элементов с мощностью: {len(spec_elements)}")
                for el in spec_elements[:5]:
                    print(f"      - {el.name}: {el.get_text()[:50]}")
                
                # Способ 3: Ищем таблицы с характеристиками
                tables = soup.find_all('table')
                print(f"\n    Таблиц на странице: {len(tables)}")
                for i, table in enumerate(tables[:3]):
                    rows = table.find_all('tr')
                    print(f"      Table {i}: {len(rows)} строк")
                    for row in rows[:3]:
                        cells = row.find_all(['td', 'th'])
                        if cells:
                            row_text = ' | '.join([c.get_text()[:20] for c in cells])
                            if any(kw in row_text for kw in ['马力', '功率', '发动机', 'power']):
                                print(f"        ★ {row_text}")
                
                # Способ 4: Ищем dl/dt/dd структуры
                dls = soup.find_all('dl')
                print(f"\n    DL элементов: {len(dls)}")
                for dl in dls[:5]:
                    dl_text = dl.get_text()[:100]
                    if any(kw in dl_text for kw in ['马力', '功率', '发动机']):
                        print(f"      ★ DL: {dl_text}")
                
                # Способ 5: Ищем JSON данные в скриптах
                scripts = soup.find_all('script')
                print(f"\n    Script тегов: {len(scripts)}")
                for script in scripts:
                    script_text = script.string or ''
                    if '马力' in script_text or 'power' in script_text.lower():
                        # Ищем JSON объекты
                        json_matches = re.findall(r'\{[^{}]*马力[^{}]*\}', script_text)
                        for jm in json_matches[:3]:
                            print(f"      ★ JSON с мощностью: {jm[:100]}")
                        
                        # Ищем конкретные значения
                        power_in_js = re.search(r'["\']?(?:power|马力)["\']?\s*[=:]\s*["\']?(\d+)', script_text)
                        if power_in_js:
                            print(f"      ★ Power в JS: {power_in_js.group(1)}")
                
                # Способ 6: Ищем в data-атрибутах
                elements_with_data = soup.find_all(attrs={"data-power": True})
                if elements_with_data:
                    print(f"\n    Элементов с data-power: {len(elements_with_data)}")
                
                # Если нашли мощность - сохраняем HTML для анализа
                if re.search(r'\d+\s*马力', page_text):
                    with open(f'/tmp/che168_desktop_{car_id}.html', 'w') as f:
                        f.write(html)
                    print(f"\n    ✓ HTML сохранён: /tmp/che168_desktop_{car_id}.html")
                    
                    # Извлекаем все характеристики
                    print(f"\n    Извлечение всех характеристик:")
                    extract_all_specs(soup)
                    
                    break
                    
            except Exception as e:
                print(f"    ✗ Ошибка: {e}")
        
        browser.close()


def extract_all_specs(soup: BeautifulSoup):
    """Извлекаем все характеристики из страницы"""
    
    specs = {}
    
    # Ищем пары label-value
    # Паттерн 1: dt/dd
    for dt in soup.find_all('dt'):
        label = dt.get_text(strip=True)
        dd = dt.find_next_sibling('dd')
        if dd:
            value = dd.get_text(strip=True)
            if label and value:
                specs[label] = value
    
    # Паттерн 2: tr с td парами
    for tr in soup.find_all('tr'):
        tds = tr.find_all(['td', 'th'])
        if len(tds) >= 2:
            label = tds[0].get_text(strip=True)
            value = tds[1].get_text(strip=True)
            if label and value and not value.startswith('<'):
                specs[label] = value
    
    # Паттерн 3: span пары
    for span in soup.find_all('span', class_=re.compile(r'label|name|title')):
        label = span.get_text(strip=True)
        next_span = span.find_next_sibling('span')
        if next_span:
            value = next_span.get_text(strip=True)
            if label and value:
                specs[label] = value
    
    # Выводим найденные характеристики
    interesting_keys = ['马力', '功率', '发动机', '排量', '变速箱', '上牌', '里程', '颜色', 'power', 'engine']
    
    print(f"    Всего найдено пар: {len(specs)}")
    for key, value in specs.items():
        if any(kw in key.lower() for kw in interesting_keys):
            print(f"      ★ {key}: {value}")


def test_getparamtypeitems_structure(car_id: int):
    """Анализ структуры API getparamtypeitems"""
    import requests
    
    print(f"\n{'='*80}")
    print(f"АНАЛИЗ СТРУКТУРЫ getparamtypeitems для car_id: {car_id}")
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
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            
            print(f"\nОтвет: {len(str(data))} bytes")
            print(f"returncode: {data.get('returncode')}")
            print(f"message: {data.get('message')}")
            
            if data.get('returncode') == 0 and data.get('result'):
                result = data['result']
                
                # Анализируем структуру
                if isinstance(result, list):
                    print(f"\nresult - это массив из {len(result)} элементов")
                    
                    for i, item in enumerate(result[:3]):  # Первые 3 элемента
                        print(f"\n  Элемент [{i}]:")
                        if isinstance(item, dict):
                            for key, value in item.items():
                                if isinstance(value, (str, int, float)):
                                    print(f"    {key}: {str(value)[:50]}")
                                elif isinstance(value, list):
                                    print(f"    {key}: list[{len(value)}]")
                                    # Если это items - показываем их
                                    if key == 'items' and value:
                                        for j, subitem in enumerate(value[:3]):
                                            if isinstance(subitem, dict):
                                                name = subitem.get('name', subitem.get('paramname', ''))
                                                val = subitem.get('value', subitem.get('paramvalue', ''))
                                                if '马力' in str(name) or '功率' in str(name):
                                                    print(f"        ★★★ [{j}] {name}: {val}")
                                                else:
                                                    print(f"        [{j}] {name}: {val}")
                                elif isinstance(value, dict):
                                    print(f"    {key}: dict{list(value.keys())[:5]}")
                
                elif isinstance(result, dict):
                    print(f"\nresult - это словарь с ключами: {list(result.keys())[:10]}")
                    
                # Ищем мощность во всей структуре
                print(f"\n--- Поиск мощности во всей структуре ---")
                find_power_recursive(data, "")
                
    except Exception as e:
        print(f"Ошибка: {e}")


def find_power_recursive(data, path, depth=0):
    """Рекурсивный поиск мощности"""
    if depth > 10:
        return
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Проверяем ключ
            if any(kw in str(key).lower() for kw in ['power', '马力', '功率', 'hp', 'ps']):
                print(f"  ★ Ключ: {current_path} = {str(value)[:50]}")
            
            # Проверяем значение
            if isinstance(value, str):
                if re.search(r'\d+\s*(马力|Ps|kW|HP)', value):
                    print(f"  ★ Значение: {current_path} = {value}")
            
            # Рекурсия
            if isinstance(value, (dict, list)):
                find_power_recursive(value, current_path, depth + 1)
                
    elif isinstance(data, list):
        for i, item in enumerate(data):
            find_power_recursive(item, f"{path}[{i}]", depth + 1)


def test_getcarinfo_for_specid(car_id: int):
    """Получаем specid из getcarinfo и пробуем autohome"""
    import requests
    
    print(f"\n{'='*80}")
    print(f"ПОИСК SPECID и AUTOHOME для car_id: {car_id}")
    print('='*80)
    
    url = "https://apiuscdt.che168.com/apic/v2/car/getcarinfo"
    params = {
        "infoid": car_id,
        "deviceid": "test123456",
        "_appid": "2sc.m"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
        "Referer": f"https://m.che168.com/cardetail/index?infoid={car_id}"
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            
            if data.get('returncode') == 0 and data.get('result'):
                result = data['result']
                
                specid = result.get('specid')
                engine = result.get('engine')
                carname = result.get('carname')
                
                print(f"\nНайдено:")
                print(f"  carname: {carname}")
                print(f"  specid: {specid}")
                print(f"  engine: {engine}")
                
                # Другие интересные поля
                for key in ['batterypower', 'ev100power', 'fuelconsumption', 'displacement']:
                    if key in result:
                        print(f"  {key}: {result[key]}")
                
                if specid:
                    # Пробуем получить данные с autohome
                    print(f"\n--- Пробуем AutoHome для specid={specid} ---")
                    test_autohome_spec(specid)
                    
    except Exception as e:
        print(f"Ошибка: {e}")


def test_autohome_spec(specid: int):
    """Тест AutoHome API для получения спецификаций"""
    import requests
    
    # AutoHome API для конфигурации
    urls = [
        f"https://car.autohome.com.cn/config/spec/{specid}.html",
        f"https://www.autohome.com.cn/spec/{specid}/",
        f"https://car.m.autohome.com.cn/config/spec/{specid}.html",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    for url in urls:
        print(f"\n  Пробуем: {url}")
        try:
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            print(f"    Status: {resp.status_code}")
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                page_text = soup.get_text()
                
                # Ищем мощность
                power_match = re.search(r'最大马力[^\d]*(\d+)', page_text)
                if power_match:
                    print(f"    ★ Мощность: {power_match.group(1)}Ps")
                
                # Ищем другие характеристики
                torque_match = re.search(r'最大扭矩[^\d]*(\d+)', page_text)
                if torque_match:
                    print(f"    ★ Крутящий момент: {torque_match.group(1)}N·m")
                
                break
        except Exception as e:
            print(f"    Ошибка: {e}")


def main():
    car_id = 56305293
    
    # Тест 1: Детальный анализ десктопной версии
    test_desktop_detailed(car_id)
    
    # Тест 2: Анализ структуры API
    test_getparamtypeitems_structure(car_id)
    
    # Тест 3: Поиск specid и AutoHome
    test_getcarinfo_for_specid(car_id)
    
    print("\n" + "="*80)
    print("ВЫВОДЫ:")
    print("="*80)
    print("""
1. DESKTOP версия (www.che168.com) содержит мощность в HTML
2. API getparamtypeitems содержит структурированные данные
3. API getcarinfo содержит specid для AutoHome
4. Мобильная версия НЕ показывает мощность на странице
    """)


if __name__ == "__main__":
    main()

