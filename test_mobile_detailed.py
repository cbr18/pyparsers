#!/usr/bin/env python3
"""
Детальный тест мобильной версии с анализом UI и API
"""

import json
import re
import time
import os
from playwright.sync_api import sync_playwright

CAR_ID = 56305293


def test_mobile_detailed():
    """Детальный анализ мобильной версии"""
    
    print("="*80)
    print("ДЕТАЛЬНЫЙ АНАЛИЗ МОБИЛЬНОЙ ВЕРСИИ CHE168")
    print("="*80)
    
    api_responses = []
    
    with sync_playwright() as p:
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
        
        # Перехватываем ВСЕ API ответы
        def handle_response(response):
            url = response.url
            if 'api' in url.lower() and 'che168' in url.lower():
                try:
                    data = response.json()
                    api_responses.append({
                        'url': url.split('?')[0],
                        'returncode': data.get('returncode'),
                        'size': len(str(data))
                    })
                    print(f"   API: {url.split('?')[0].split('/')[-1]} ({len(str(data))} bytes)")
                except:
                    pass
        
        page.on("response", handle_response)
        
        # 1. Открываем главную страницу машины
        main_url = f"https://m.che168.com/cardetail/index?infoid={CAR_ID}"
        print(f"\n1. Открываем: {main_url}")
        
        page.goto(main_url, wait_until='networkidle', timeout=60000)
        time.sleep(3)
        
        # Анализируем текст на странице
        page_text = page.inner_text('body')
        
        print(f"\n2. Анализ текста на главной странице:")
        
        # Ищем секцию параметров
        if '参数' in page_text:
            print("   ✓ Найдена секция '参数'")
            
            # Ищем параметры рядом
            params_match = re.search(r'参数[^\n]*\n([^\n]+发动机[^\n]*)', page_text)
            if params_match:
                print(f"   Текст около '参数': {params_match.group(1)[:100]}")
        
        # Ищем мощность на странице
        power_patterns = [
            r'(\d+)\s*马力',
            r'(\d+)\s*Ps',
            r'(\d+)\s*HP',
            r'(\d+)\s*kW',
        ]
        
        for pattern in power_patterns:
            match = re.search(pattern, page_text)
            if match:
                print(f"   ★ Найдена мощность: {match.group(0)}")
                break
        else:
            print("   ✗ Мощность НЕ найдена в тексте страницы")
        
        # 2. Кликаем на секцию параметров
        print(f"\n3. Кликаем на '参数'...")
        
        try:
            # Ищем кликабельный элемент с параметрами
            elements = page.query_selector_all('text=参数')
            print(f"   Найдено {len(elements)} элементов с текстом '参数'")
            
            if elements:
                for i, el in enumerate(elements[:3]):
                    text = el.inner_text()
                    print(f"   [{i}] '{text[:50]}'")
                
                # Кликаем на первый
                elements[0].click()
                print("   ✓ Клик выполнен!")
                time.sleep(3)
                
                # Проверяем изменился ли текст
                new_page_text = page.inner_text('body')
                
                # Ищем мощность после клика
                for pattern in power_patterns:
                    match = re.search(pattern, new_page_text)
                    if match:
                        print(f"   ★ После клика найдена мощность: {match.group(0)}")
                        break
                
                # Проверяем появилось ли модальное окно
                if len(new_page_text) > len(page_text):
                    print(f"   Контент увеличился: {len(page_text)} -> {len(new_page_text)} chars")
                
                # Ищем новые параметры
                new_params = []
                tech_patterns = [
                    r'最大马力[^0-9]*(\d+)',
                    r'最大扭矩[^0-9]*(\d+)',
                    r'最高车速[^0-9]*(\d+)',
                    r'变速箱[^:：]*[:：]\s*([^\n]+)',
                ]
                
                for pattern in tech_patterns:
                    match = re.search(pattern, new_page_text)
                    if match:
                        new_params.append(match.group(0)[:50])
                
                if new_params:
                    print(f"   Новые параметры после клика:")
                    for p in new_params:
                        print(f"     - {p}")
        
        except Exception as e:
            print(f"   Ошибка: {e}")
        
        # 3. Прямой вызов API getparamtypeitems
        print(f"\n4. Прямой API вызов getparamtypeitems...")
        
        result = page.evaluate("""
            async () => {
                const url = 'https://apiuscdt.che168.com/api/v1/car/getparamtypeitems?infoid=56305293&deviceid=test&_appid=2sc.m';
                try {
                    const response = await fetch(url);
                    const data = await response.json();
                    return {
                        success: true,
                        returncode: data.returncode,
                        sections: data.result ? data.result.length : 0,
                        sample: data.result ? data.result[0] : null
                    };
                } catch (e) {
                    return {success: false, error: e.message};
                }
            }
        """)
        
        print(f"   Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        browser.close()
    
    # Итог по API
    print(f"\n5. Всего перехвачено API запросов: {len(api_responses)}")
    for api in api_responses:
        print(f"   - {api['url'].split('/')[-1]}: rc={api['returncode']}, size={api['size']}")


if __name__ == "__main__":
    test_mobile_detailed()

