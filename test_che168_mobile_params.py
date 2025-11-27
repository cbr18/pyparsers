#!/usr/bin/env python3
"""
Тест клика на секцию "参数" в мобильной версии che168
"""

import json
import re
import time
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

TEST_CAR_ID = 56305293


def test_mobile_with_params_click(car_id: int):
    """Тест мобильной версии с кликом на параметры"""
    
    print(f"\n{'='*80}")
    print(f"ТЕСТ: Клик на '参数' в мобильной версии")
    print(f"car_id: {car_id}")
    print('='*80)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.environ.get("CHROME_BIN", "/usr/bin/chromium"),
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            viewport={'width': 390, 'height': 844},
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )
        
        page = context.new_page()
        
        # Перехватываем API ответы
        api_responses = []
        
        def handle_response(response):
            try:
                url = response.url
                if 'getparamtypeitems' in url.lower() or 'param' in url.lower():
                    try:
                        json_data = response.json()
                        api_responses.append({
                            'url': url,
                            'data': json_data,
                            'size': len(str(json_data))
                        })
                        print(f"  ✓ API: {url[:60]}... ({len(str(json_data))} bytes)")
                    except:
                        pass
            except:
                pass
        
        page.on("response", handle_response)
        
        # Загружаем главную страницу машины
        mobile_url = f"https://m.che168.com/cardetail/index?infoid={car_id}"
        print(f"\n1. Загружаем: {mobile_url}")
        
        page.goto(mobile_url, wait_until='networkidle', timeout=60000)
        time.sleep(3)
        
        # Делаем скриншот до клика
        page.screenshot(path=f'/tmp/che168_mobile_before_{car_id}.png')
        print(f"   Скриншот сохранён: /tmp/che168_mobile_before_{car_id}.png")
        
        # Ищем и кликаем на секцию "参数"
        print(f"\n2. Ищем секцию '参数' для клика...")
        
        # Разные селекторы для поиска секции параметров
        param_selectors = [
            "text=参数",
            "text=全部参数",
            "text=参数配置",
            "text=查看全部参数",
            "[class*='param']",
            "[class*='config']",
            "a:has-text('参数')",
            "div:has-text('参数'):has-text('发动机')",
            # Ищем по структуре - секция с двигателем и КПП
            "div:has-text('2.0T'):has-text('发动机')",
            "div:has-text('自动'):has-text('变速箱')",
        ]
        
        clicked = False
        for selector in param_selectors:
            try:
                elements = page.locator(selector)
                count = elements.count()
                if count > 0:
                    print(f"   Найдено '{selector}': {count} элементов")
                    
                    # Пробуем кликнуть на первый подходящий
                    for i in range(min(count, 3)):
                        try:
                            el = elements.nth(i)
                            text = el.inner_text()[:50] if el.inner_text() else ''
                            print(f"   [{i}] Текст: {text}")
                            
                            # Кликаем если это похоже на секцию параметров
                            if '参数' in text or '发动机' in text or '配置' in text:
                                print(f"   → Кликаем на элемент [{i}]...")
                                el.click(timeout=5000)
                                time.sleep(3)
                                clicked = True
                                break
                        except Exception as e:
                            print(f"   Ошибка клика [{i}]: {e}")
                            continue
                    
                    if clicked:
                        break
            except Exception as e:
                continue
        
        # Пробуем JavaScript клик на элемент с "参数"
        if not clicked:
            print(f"\n   Пробуем JavaScript поиск и клик...")
            try:
                result = page.evaluate("""
                    () => {
                        // Ищем элементы с текстом "参数"
                        const allElements = document.querySelectorAll('*');
                        const found = [];
                        
                        for (let el of allElements) {
                            const text = el.innerText || el.textContent || '';
                            if (text.includes('参数') && text.length < 100) {
                                found.push({
                                    tag: el.tagName,
                                    text: text.substring(0, 50),
                                    className: el.className || '',
                                    clickable: el.onclick !== null || el.tagName === 'A' || el.tagName === 'BUTTON'
                                });
                                
                                // Пробуем кликнуть
                                if (el.onclick || el.tagName === 'A' || el.className.includes('click')) {
                                    el.click();
                                    return {clicked: true, element: el.tagName, text: text.substring(0, 50)};
                                }
                            }
                        }
                        
                        // Ищем секцию с параметрами (发动机, 变速箱)
                        for (let el of allElements) {
                            const text = el.innerText || '';
                            if (text.includes('发动机') && text.includes('变速箱') && text.length < 500) {
                                el.click();
                                return {clicked: true, element: el.tagName, text: text.substring(0, 100)};
                            }
                        }
                        
                        return {clicked: false, found: found.slice(0, 10)};
                    }
                """)
                print(f"   JS результат: {result}")
                if result.get('clicked'):
                    clicked = True
                    time.sleep(3)
            except Exception as e:
                print(f"   JS ошибка: {e}")
        
        # Прокручиваем страницу чтобы найти секцию параметров
        if not clicked:
            print(f"\n   Прокручиваем страницу для поиска...")
            page.evaluate("window.scrollTo(0, 500)")
            time.sleep(1)
            
            # Ищем кликабельные элементы с параметрами
            try:
                clickable = page.evaluate("""
                    () => {
                        const results = [];
                        const elements = document.querySelectorAll('div, a, span, button');
                        
                        for (let el of elements) {
                            const text = (el.innerText || '').trim();
                            const rect = el.getBoundingClientRect();
                            
                            // Ищем элемент с "参数" или характеристиками
                            if ((text.includes('参数') || 
                                 (text.includes('发动机') && text.includes('T')) ||
                                 text.includes('全部参数') ||
                                 text.includes('查看参数')) && 
                                text.length < 200 &&
                                rect.height > 20 && rect.height < 200) {
                                
                                results.push({
                                    tag: el.tagName,
                                    text: text.substring(0, 80),
                                    top: rect.top,
                                    height: rect.height
                                });
                            }
                        }
                        return results;
                    }
                """)
                
                print(f"   Найдено кликабельных элементов: {len(clickable)}")
                for item in clickable[:5]:
                    print(f"     - {item['tag']}: {item['text'][:40]}... (top={item['top']:.0f})")
                
            except Exception as e:
                print(f"   Ошибка: {e}")
        
        # Делаем скриншот после
        page.screenshot(path=f'/tmp/che168_mobile_after_{car_id}.png')
        print(f"\n   Скриншот после: /tmp/che168_mobile_after_{car_id}.png")
        
        # Проверяем текущий URL
        current_url = page.url
        print(f"\n3. Текущий URL: {current_url}")
        
        # Пробуем напрямую открыть страницу параметров
        print(f"\n4. Пробуем прямые URL страницы параметров...")
        
        params_urls = [
            f"https://m.che168.com/cardetail/params?infoid={car_id}",
            f"https://m.che168.com/v9/car/carparams.html?infoid={car_id}",
            f"https://m.che168.com/cardetail/config?infoid={car_id}",
            f"https://m.che168.com/used/{car_id}/config.html",
        ]
        
        for url in params_urls:
            print(f"\n   Пробуем: {url}")
            try:
                response = page.goto(url, wait_until='networkidle', timeout=20000)
                time.sleep(2)
                
                html = page.content()
                title = page.title()
                
                if response and response.status == 200 and '访问出错' not in html and len(html) > 5000:
                    print(f"   ✓ Успех! Title: {title[:50]}")
                    print(f"   HTML size: {len(html)} bytes")
                    
                    # Сохраняем HTML
                    with open(f'/tmp/che168_params_{car_id}.html', 'w') as f:
                        f.write(html)
                    print(f"   HTML сохранён: /tmp/che168_params_{car_id}.html")
                    
                    # Делаем скриншот
                    page.screenshot(path=f'/tmp/che168_params_{car_id}.png')
                    
                    # Ищем мощность на странице
                    soup = BeautifulSoup(html, 'html.parser')
                    page_text = soup.get_text()
                    
                    power_match = re.search(r'(\d+)\s*(?:马力|Ps|HP)', page_text)
                    if power_match:
                        print(f"   ★ МОЩНОСТЬ НАЙДЕНА: {power_match.group(0)}")
                    
                    torque_match = re.search(r'(\d+)\s*N·m', page_text)
                    if torque_match:
                        print(f"   ★ Крутящий момент: {torque_match.group(0)}")
                    
                    break
                else:
                    print(f"   ✗ Не работает (status={response.status if response else 'None'})")
                    
            except Exception as e:
                print(f"   ✗ Ошибка: {e}")
        
        # Выводим перехваченные API
        print(f"\n5. Перехваченные API ответы: {len(api_responses)}")
        for api in api_responses:
            print(f"   - {api['url'][:60]}... ({api['size']} bytes)")
            
            # Если это getparamtypeitems - ищем мощность
            if 'getparamtypeitems' in api['url']:
                data = api['data']
                if data.get('returncode') == 0 and data.get('result'):
                    for section in data['result']:
                        for item in section.get('data', []):
                            name = item.get('name', '')
                            content = item.get('content', '')
                            if '马力' in name or '马力' in content:
                                print(f"      ★ {name}: {content}")
        
        browser.close()
        
        print(f"\n{'='*80}")
        print("ИТОГ:")
        print("="*80)
        print(f"API ответов перехвачено: {len(api_responses)}")
        

def test_mobile_navigation(car_id: int):
    """Тест навигации в мобильной версии"""
    
    print(f"\n{'='*80}")
    print(f"ТЕСТ: Навигация по мобильной версии")
    print('='*80)
    
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
        
        # Перехватываем все переходы
        urls_visited = []
        
        def handle_request(request):
            if request.resource_type == 'document':
                urls_visited.append(request.url)
        
        page.on("request", handle_request)
        
        # Загружаем страницу
        mobile_url = f"https://m.che168.com/cardetail/index?infoid={car_id}"
        page.goto(mobile_url, wait_until='networkidle', timeout=60000)
        time.sleep(3)
        
        # Получаем все ссылки на странице
        links = page.evaluate("""
            () => {
                const links = [];
                document.querySelectorAll('a').forEach(a => {
                    const href = a.href || '';
                    const text = (a.innerText || '').trim().substring(0, 50);
                    if (href && (href.includes('param') || href.includes('config') || 
                                 text.includes('参数') || text.includes('配置'))) {
                        links.push({href, text});
                    }
                });
                return links;
            }
        """)
        
        print(f"\nСсылки с 'param/config/参数':")
        for link in links:
            print(f"  - {link['text']}: {link['href']}")
        
        # Ищем все кликабельные области
        clickable_areas = page.evaluate("""
            () => {
                const areas = [];
                const elements = document.querySelectorAll('[onclick], [data-href], [data-url], .clickable, [role="button"]');
                
                elements.forEach(el => {
                    const text = (el.innerText || '').trim().substring(0, 100);
                    const onclick = el.getAttribute('onclick') || '';
                    const dataHref = el.getAttribute('data-href') || el.getAttribute('data-url') || '';
                    
                    if (text.includes('参数') || text.includes('配置') || 
                        onclick.includes('param') || dataHref.includes('param')) {
                        areas.push({
                            tag: el.tagName,
                            text: text,
                            onclick: onclick.substring(0, 100),
                            dataHref: dataHref
                        });
                    }
                });
                
                return areas;
            }
        """)
        
        print(f"\nКликабельные области с параметрами:")
        for area in clickable_areas:
            print(f"  - {area['tag']}: {area['text'][:40]}...")
            if area['onclick']:
                print(f"    onclick: {area['onclick']}")
            if area['dataHref']:
                print(f"    data-href: {area['dataHref']}")
        
        # Ищем React/Vue data attributes
        spa_data = page.evaluate("""
            () => {
                const data = [];
                document.querySelectorAll('[data-v-], [data-reactid], [class*="param"], [class*="config"]').forEach(el => {
                    const text = (el.innerText || '').trim().substring(0, 100);
                    if (text.length > 0 && text.length < 200) {
                        data.push({
                            tag: el.tagName,
                            className: el.className,
                            text: text
                        });
                    }
                });
                return data.slice(0, 20);
            }
        """)
        
        print(f"\nSPA элементы (React/Vue):")
        for item in spa_data[:10]:
            print(f"  - {item['tag']}.{item['className'][:30]}: {item['text'][:40]}...")
        
        browser.close()


if __name__ == "__main__":
    # Тест с кликом на параметры
    test_mobile_with_params_click(TEST_CAR_ID)
    
    # Тест навигации
    test_mobile_navigation(TEST_CAR_ID)

