"""
Модуль для асинхронной работы с браузером с использованием Playwright.
"""

import asyncio
import json
import re
import uuid
import datetime
import logging
from typing import Dict, Any, Optional, Tuple, List
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, Playwright

# Настройка логирования
logger = logging.getLogger(__name__)

class AsyncBrowserManager:
    """
    Менеджер для асинхронной работы с браузером.
    Использует Playwright для автоматизации браузера.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page_pool = []
        self._max_pages = 5
        self._semaphore = asyncio.Semaphore(self._max_pages)
        self._initialized = False

    async def initialize(self):
        """
        Инициализирует Playwright и браузер.
        """
        if self._initialized:
            return

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-web-security"
                ]
            )

            # Создаем контекст браузера с настройками
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="Europe/Moscow",
                ignore_https_errors=True
            )

            # Отключаем загрузку изображений и других ресурсов для ускорения
            await self._context.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,otf,eot}", lambda route: route.abort())
            await self._context.route("**/*.{css,less}", lambda route: route.abort())

            self._initialized = True
            logger.info("Browser manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize browser manager: {str(e)}")
            await self.close()
            raise

    async def get_page(self) -> Page:
        """
        Получает страницу из пула или создает новую.

        Returns:
            Page: Страница браузера
        """
        await self.initialize()

        async with self._semaphore:
            if self._page_pool:
                page = self._page_pool.pop()
            else:
                page = await self._context.new_page()

            return page

    async def release_page(self, page: Page):
        """
        Возвращает страницу в пул.

        Args:
            page: Страница браузера
        """
        if len(self._page_pool) < self._max_pages:
            # Очищаем cookies и localStorage
            await page.context.clear_cookies()
            try:
                await page.evaluate("localStorage.clear()")
            except:
                pass

            # Возвращаем страницу в пул
            self._page_pool.append(page)
        else:
            # Закрываем страницу, если пул полон
            await page.close()

    async def close(self):
        """
        Закрывает браузер и освобождает ресурсы.
        """
        # Закрываем все страницы в пуле
        for page in self._page_pool:
            try:
                await page.close()
            except:
                pass

        self._page_pool = []

        # Закрываем контекст и браузер
        if self._context:
            try:
                await self._context.close()
            except:
                pass
            self._context = None

        if self._browser:
            try:
                await self._browser.close()
            except:
                pass
            self._browser = None

        # Закрываем Playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except:
                pass
            self._playwright = None

        self._initialized = False
        logger.info("Browser manager closed")


# Создаем глобальный экземпляр менеджера браузера
browser_manager = AsyncBrowserManager()


async def fetch_car_detail_async(car_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Асинхронно парсит детальную информацию о машине по car_id через Playwright.

    Args:
        car_id: ID машины

    Returns:
        Tuple[Dict[str, Any], Dict[str, Any]]: Данные о машине и метаданные
    """
    url = f"https://www.dongchedi.com/usedcar/{car_id}"
    page = None

    try:
        # Получаем страницу из пула
        page = await browser_manager.get_page()

        # Устанавливаем таймаут для загрузки страницы
        page.set_default_timeout(30000)

        # Загружаем страницу
        await page.goto(url, wait_until="domcontentloaded")

        # Ждем загрузки контента
        await asyncio.sleep(2)

        # Прокручиваем страницу для загрузки динамического контента
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

        # Получаем HTML-код страницы
        html_content = await page.content()

        # Парсим HTML с помощью BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Добавляем текущее время для полей created_at и updated_at
        current_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Генерируем UUID для новой записи
        car_uuid = str(uuid.uuid4())

        # Создаем базовую информацию о машине
        car_info = {
            "uuid": car_uuid,
            "title": None,
            "sh_price": None,
            "price": None,
            "image": None,
            "link": url,
            "car_name": None,
            "car_year": None,
            "year": None,
            "car_mileage": None,
            "mileage": None,
            "car_source_city_name": None,
            "city": None,
            "brand_name": None,
            "series_name": None,
            "brand_id": None,
            "series_id": None,
            "shop_id": None,
            "car_id": car_id,
            "tags_v2": None,
            "tags": None,
            "sku_id": car_id,
            "sort_number": 1,
            "source": "dongchedi",
            "is_available": True,
            "description": None,
            "color": None,
            "transmission": None,
            "fuel_type": None,
            "engine_volume": None,
            "body_type": None,
            "drive_type": None,
            "condition": None,
            "created_at": current_time,
            "updated_at": current_time
        }

        # Ищем JSON-данные в скриптах
        scripts = soup.find_all('script')
        json_data_found = False

        for script in scripts:
            if hasattr(script, 'string') and script.string:
                script_content = script.string
                if '__NEXT_DATA__' in script_content:
                    try:
                        start = script_content.find('{')
                        end = script_content.rfind('}') + 1
                        if start != -1 and end != 0:
                            json_data = json.loads(script_content[start:end])
                            if 'props' in json_data and 'pageProps' in json_data['props']:
                                page_props = json_data['props']['pageProps']
                                if 'skuDetail' in page_props:
                                    sku_detail = page_props['skuDetail']
                                    car_info.update({
                                        'title': sku_detail.get('title', ''),
                                        'sh_price': sku_detail.get('sh_price', ''),
                                        'car_mileage': sku_detail.get('car_info', {}).get('mileage', ''),
                                        'car_year': sku_detail.get('car_info', {}).get('year', ''),
                                        'year': sku_detail.get('car_info', {}).get('year', ''),
                                        'brand_name': sku_detail.get('car_info', {}).get('brand_name', ''),
                                        'series_name': sku_detail.get('car_info', {}).get('series_name', ''),
                                        'car_name': sku_detail.get('car_info', {}).get('car_name', ''),
                                        'image': sku_detail.get('image', ''),
                                        'shop_id': sku_detail.get('shop_info', {}).get('shop_id', ''),
                                        'brand_id': sku_detail.get('car_info', {}).get('brand_id', 0),
                                        'series_id': sku_detail.get('car_info', {}).get('series_id', 0),
                                        'car_source_city_name': sku_detail.get('car_info', {}).get('city', ''),
                                        'city': sku_detail.get('car_info', {}).get('city', ''),
                                        'description': sku_detail.get('description', ''),
                                        'color': sku_detail.get('car_info', {}).get('color', ''),
                                        'transmission': sku_detail.get('car_info', {}).get('transmission', ''),
                                        'fuel_type': sku_detail.get('car_info', {}).get('fuel_type', ''),
                                        'engine_volume': sku_detail.get('car_info', {}).get('engine_volume', ''),
                                        'body_type': sku_detail.get('car_info', {}).get('body_type', ''),
                                        'drive_type': sku_detail.get('car_info', {}).get('drive_type', ''),
                                        'condition': sku_detail.get('car_info', {}).get('condition', ''),
                                    })
                                    json_data_found = True
                                    break
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Failed to parse JSON from script: {str(e)}")
                        continue

        # Если JSON-данные не найдены, пытаемся извлечь информацию из HTML
        if not json_data_found:
            # Извлекаем заголовок
            title_tag = soup.find('title')
            if title_tag:
                car_info['title'] = title_tag.get_text().strip()
                car_info['car_name'] = title_tag.get_text().strip()

            # Извлекаем цену
            price_selectors = [
                'span.tw-text-color-red-500',
                'p.tw-text-color-red-500',
                'span[class*="price"]',
                'b.num-price',
                '.price',
                '[class*="price"]'
            ]

            for selector in price_selectors:
                price_elements = soup.select(selector)
                if price_elements:
                    for elem in price_elements:
                        price_text = elem.get_text().strip()
                        if any(char in price_text for char in ['万', '元', '¥', '￥']):
                            car_info['sh_price'] = price_text
                            break
                    if car_info['sh_price']:
                        break

            # Извлекаем описание из мета-тегов
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description and hasattr(meta_description, 'get'):
                content = meta_description.get('content', '')
                if content:
                    car_info['tags_v2'] = content

        # Определяем доступность машины
        page_text = soup.get_text()
        available_indicators = [
            "询底价", "点击查看联系电话", "我要优惠", "立即查询",
            "询价", "联系", "电话", "咨询", "优惠"
        ]
        unavailable_indicators = [
            "已售", "售出", "已卖出", "下架", "已下架", "已成交",
            "sold", "sale", "unavailable", "not available"
        ]

        is_available = False
        if any(indicator in page_text for indicator in available_indicators):
            is_available = True
        elif any(indicator in page_text for indicator in unavailable_indicators):
            is_available = False
        else:
            is_available = car_info['sh_price'] is not None and car_info['sh_price'] != ''

        car_info['is_available'] = is_available

        # Применяем декодер к нужным полям
        from converters import decode_dongchedi_detail, decode_dongchedi_list_sh_price

        for key in ["title", "car_name", "sh_price"]:
            if car_info.get(key):
                car_info[key] = decode_dongchedi_detail(car_info[key])

        # Преобразуем списки в строки для полей tags и tags_v2
        for key in ["tags", "tags_v2"]:
            if car_info.get(key) is not None and not isinstance(car_info[key], str):
                try:
                    car_info[key] = json.dumps(car_info[key])
                except:
                    car_info[key] = str(car_info[key])

        # Устанавливаем цену из sh_price
        if car_info.get('sh_price'):
            price_str = str(car_info['sh_price'])
            price_numeric = re.sub(r'[^\d.]', '', price_str)
            if price_numeric:
                car_info['price'] = price_numeric

        # Возвращаем данные о машине и метаданные
        return car_info, {"is_available": is_available, "status": 200, "link": url}

    except Exception as e:
        logger.error(f"Error fetching car detail for {car_id}: {str(e)}")
        return None, {"is_available": False, "error": str(e), "status": 500}

    finally:
        # Возвращаем страницу в пул
        if page:
            await browser_manager.release_page(page)


async def fetch_multiple_car_details(car_ids: List[str]) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Асинхронно парсит детальную информацию о нескольких машинах.

    Args:
        car_ids: Список ID машин

    Returns:
        List[Tuple[Dict[str, Any], Dict[str, Any]]]: Список кортежей с данными о машинах и метаданными
    """
    # Создаем задачи для каждого ID машины
    tasks = [fetch_car_detail_async(car_id) for car_id in car_ids]

    # Выполняем задачи параллельно
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Обрабатываем результаты
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Error fetching car detail for {car_ids[i]}: {str(result)}")
            processed_results.append((None, {"is_available": False, "error": str(result), "status": 500}))
        else:
            processed_results.append(result)

    return processed_results
