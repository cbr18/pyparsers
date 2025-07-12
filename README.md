# CarsParser - Парсер автомобилей с Selenium

Универсальный парсер для получения данных об автомобилях с различных источников с использованием Selenium.

## Структура проекта

```
CarsParser/
├── api/                    # Парсеры для разных источников
│   ├── base_parser.py     # Базовый класс для парсеров
│   ├── che168fetch.py     # Selenium парсер для Che168
│   ├── dongchedifetch.py  # Парсер для Dongchedi
│   ├── parser_factory.py  # Фабрика парсеров
│   └── __init__.py
├── models/                # Модели данных
│   ├── car.py            # Модель автомобиля
│   ├── response.py       # Модель ответа API
│   ├── brand.py          # Модель бренда
│   └── tag.py            # Модель тега
├── main.py               # Основной файл для запуска
├── translate.py          # Функции перевода
├── converters.py         # Конвертеры данных
└── pyproject.toml        # Зависимости проекта
```

## Установка и запуск

### Установка зависимостей
```bash
uv pip install requests beautifulsoup4 pydantic googletrans==4.0.2 selenium
```

### Установка Chrome и ChromeDriver
1. Установите [Google Chrome](https://www.google.com/chrome/)
2. Скачайте [ChromeDriver](https://chromedriver.chromium.org/) (версия должна соответствовать версии Chrome)
3. Добавьте ChromeDriver в PATH или поместите в папку проекта

### Запуск
```bash
uv run python main.py
```

## Архитектура

### Унифицированный интерфейс
Все парсеры наследуются от `BaseCarParser` и предоставляют единый интерфейс:

```python
from api.parser_factory import ParserFactory

# Получение парсера
parser = ParserFactory.get_parser('che168')

# Получение данных
response = parser.fetch_cars('url')  # Selenium парсинг
```

### Доступные парсеры
- **Che168Parser** - Selenium парсер для сайта Che168
- **DongchediParser** - парсер для API Dongchedi

## API Эндпоинты

### Dongchedi API
- `GET /cars/dongchedi` - Получить первую страницу данных
- `GET /cars/dongchedi/page/{page}` - Получить данные конкретной страницы

### Che168 API
- `GET /cars/che168` - Получить первую страницу данных
- `GET /cars/che168/page/{page}` - Получить данные конкретной страницы

### Примеры использования API

#### Получение первой страницы dongchedi
```bash
curl http://localhost:8000/cars/dongchedifetch
```

#### Получение конкретной страницы dongchedi
```bash
curl http://localhost:8000/cars/dongchedi/page/2
```

#### Получение конкретной страницы che168
```bash
curl http://localhost:8000/cars/che168/page/2
```

#### Загрузка всех страниц dongchedi
```python
import requests

def fetch_all_pages():
    page = 1
    all_cars = []
    
    while True:
        response = requests.get(f"http://localhost:8000/cars/dongchedi/page/{page}")
        data = response.json()
        
        if data["status"] != 200:
            break
            
        cars = data["data"]["search_sh_sku_info_list"]
        all_cars.extend(cars)
        
        if not data["data"]["has_more"]:
            break
            
        page += 1
    
    return all_cars
```

#### Загрузка всех страниц che168
```python
import requests
import time

def fetch_all_che168_pages(max_pages=5, delay=2.0):
    all_cars = []
    
    for page in range(1, max_pages + 1):
        response = requests.get(f"http://localhost:8000/cars/che168/page/{page}")
        data = response.json()
        
        if data["status"] != 200:
            break
            
        cars = data["data"]["search_sh_sku_info_list"]
        all_cars.extend(cars)
        
        if not data["data"]["has_more"]:
            break
            
        # Задержка между запросами для избежания блокировки
        if page < max_pages:
            time.sleep(delay)
    
    return all_cars
```

## Использование

### Базовое использование
```python
from api.parser_factory import ParserFactory

# Тестирование всех парсеров
factory = ParserFactory()
for parser_name in factory.get_available_parsers():
    parser = factory.get_parser(parser_name)
    response = parser.fetch_cars()
    print(f"Найдено машин: {len(response.data.search_sh_sku_info_list)}")
```

### Работа с конкретным парсером
```python
from api.che168fetch import Che168Parser

parser = Che168Parser(headless=True)  # headless=True для работы в фоне
response = parser.fetch_cars('url')   # Парсим с сайта
```

## Особенности

### Che168 Selenium Parser
- Использует Selenium WebDriver для полной имитации браузера
- Обходит блокировки и защиту от парсинга
- Поддерживает прокрутку страницы для загрузки всего контента
- Имитирует человеческое поведение (случайные задержки, движения мыши)
- Работает как с URL, так и с локальными файлами
- Поддерживает пагинацию через API эндпоинт `/cars/che168/page/{page}`
- URL страниц: `https://www.che168.com/china/a0_0msdgscncgpi1lto8csp{pagenumber}exx0/`

### Dongchedi Parser
- Использует официальное API
- Работает стабильно и быстро
- Возвращает структурированные данные
- Поддерживает пагинацию через API эндпоинт `/cars/dongchedi/page/{page}`

## Модели данных

### Car (Автомобиль)
Основные поля:
- `title` - заголовок объявления
- `brand_name` - название бренда
- `car_name` - название модели
- `car_year` - год выпуска
- `sh_price` - цена
- `image` - ссылка на фото
- `link` - ссылка на объявление

### ApiResponse
Унифицированный ответ от всех парсеров:
- `data` - данные с машинами
- `message` - сообщение о статусе
- `status` - HTTP статус

## Настройки Selenium

### Параметры Chrome
```python
parser = Che168Parser(
    headless=True,  # Работа в фоне (без открытия окна браузера)
)
```

### Настройки для обхода блокировки
- Ротация User-Agent
- Случайные размеры окна
- Имитация человеческого поведения
- Скрытие признаков автоматизации

## Расширение функциональности

### Добавление нового парсера
1. Создайте класс, наследующий от `BaseCarParser`
2. Реализуйте метод `fetch_cars()`
3. Зарегистрируйте парсер в `ParserFactory`

```python
from api.base_parser import BaseCarParser
from models.response import ApiResponse

class MyParser(BaseCarParser):
    def fetch_cars(self, source=None) -> ApiResponse:
        # Ваша логика парсинга
        pass

# Регистрация
ParserFactory.register_parser('my_parser', MyParser)
```

### Добавление нового Selenium парсера
```python
from api.base_parser import BaseCarParser
from selenium import webdriver

class MySeleniumParser(BaseCarParser):
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
    
    def _setup_driver(self):
        # Настройка драйвера
        pass
    
    def fetch_cars(self, source='url') -> ApiResponse:
        # Selenium логика
        pass
```

## Устранение проблем

### ChromeDriver не найден
```bash
# Скачайте ChromeDriver с https://chromedriver.chromium.org/
# Добавьте в PATH или поместите в папку проекта
```

### Ошибки Selenium
```python
# Проверьте версию Chrome и ChromeDriver
# Они должны быть совместимы
```

### Медленная работа
```python
# Используйте headless=True для ускорения
parser = Che168Parser(headless=True)
```

## Зависимости

- `requests` - HTTP запросы
- `beautifulsoup4` - парсинг HTML
- `pydantic` - валидация данных
- `googletrans==4.0.2` - перевод текста
- `selenium` - автоматизация браузера

## Производительность

| Парсер | Скорость | Надежность | Обход блокировки |
|--------|----------|------------|------------------|
| Che168 Selenium | Средняя | Высокая | ✅ |
| Dongchedi API | Высокая | Высокая | ✅ |

## Лицензия

MIT License 