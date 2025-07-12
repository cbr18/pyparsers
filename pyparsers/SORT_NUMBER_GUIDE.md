# Система нумерации sort_number

## Обзор

Система `sort_number` позволяет получать порядковые номера для машин, что дает возможность сортировать их по новизне. Поскольку данные парсятся отсортированными по новизне, `sort_number` отражает порядок появления машин в списке.

**Важно**: Большие номера = новые машины, малые номера = старые машины.

## Как это работает

### 1. Обычный парсинг (страницы)
- **Эндпоинты**: `/cars/dongchedi`, `/cars/che168`, `/cars/dongchedi/page/{page}`, `/cars/che168/page/{page}`
- **Нумерация**: Начинается с 1 для каждой страницы
- **Поля**: Добавляются `sort_number` и `source`

### 2. Полный парсинг
- **Эндпоинты**: `/cars/dongchedi/all`, `/cars/che168/all`
- **Нумерация**: Начинается с 1 и продолжается последовательно через все страницы
- **Поля**: Добавляются `sort_number` и `source`

### 3. Инкрементальное обновление
- **Эндпоинты**: `/cars/dongchedi/incremental`, `/cars/che168/incremental`
- **Нумерация**: Продолжается от максимального `sort_number` существующих машин того же источника + 1, но среди новых машин самые новые получают большие номера
- **Поля**: Добавляются `sort_number` и `source`

## Структура данных

Каждая машина теперь содержит дополнительные поля:

```json
{
  "title": "Название машины",
  "car_id": 12345,
  "sort_number": 5,
  "source": "dongchedi",
  // ... остальные поля
}
```

## Примеры использования

### Получение данных с нумерацией

```bash
# Обычный парсинг
curl http://localhost:8000/cars/dongchedi

# Полный парсинг
curl http://localhost:8000/cars/dongchedi/all

# Инкрементальное обновление
curl -X POST http://localhost:8000/cars/dongchedi/incremental \
  -H "Content-Type: application/json" \
  -d '[
    {"car_id": 123, "sort_number": 5, "source": "dongchedi"},
    {"car_id": 456, "sort_number": 10, "source": "dongchedi"}
  ]'
```

### Сортировка на фронтенде

```javascript
// Сортировка по новизне (новые первыми)
cars.sort((a, b) => b.sort_number - a.sort_number);

// Сортировка по источнику и новизне
cars.sort((a, b) => {
    if (a.source !== b.source) {
        return a.source.localeCompare(b.source);
    }
    return b.sort_number - a.sort_number;
});

// Фильтрация по источнику
const dongchediCars = cars.filter(car => car.source === 'dongchedi');
const che168Cars = cars.filter(car => car.source === 'che168');

// Получение самых новых машин
const newestCars = cars.sort((a, b) => b.sort_number - a.sort_number).slice(0, 10);
```

### Python примеры

```python
import requests

# Получение данных
response = requests.get("http://localhost:8000/cars/dongchedi")
cars = response.json()['data']['search_sh_sku_info_list']

# Сортировка по новизне
sorted_cars = sorted(cars, key=lambda x: x['sort_number'], reverse=True)

# Группировка по источнику
by_source = {}
for car in cars:
    source = car['source']
    if source not in by_source:
        by_source[source] = []
    by_source[source].append(car)

# Сортировка внутри каждого источника
for source in by_source:
    by_source[source].sort(key=lambda x: x['sort_number'], reverse=True)
```

## Логика нумерации

### Инкрементальное обновление

```python
def _get_next_sort_number(existing_cars: List[Dict], source: str) -> int:
    if not existing_cars:
        return 1
    
    # Ищем максимальный sort_number среди машин того же источника
    max_number = 0
    for car in existing_cars:
        if car.get('source') == source and car.get('sort_number'):
            max_number = max(max_number, car['sort_number'])
    
    return max_number + 1
```

### Примеры нумерации

1. **Пустая база** → начинаем с 1
2. **Существующие машины dongchedi**: [1, 3, 5] → новые получают номера 6, 7, 8...
3. **Существующие машины che168**: [2, 4, 6] → новые получают номера 7, 8, 9...
4. **Смешанные источники**: dongchedi [1,3], che168 [2,4] → новые dongchedi получают 4,5..., новые che168 получают 5,6...

### Логика нумерации

- **Обычный парсинг**: Если найдено 10 машин, то номера: 10, 9, 8, 7, 6, 5, 4, 3, 2, 1
- **Полный парсинг**: Если найдено 100 машин, то номера: 100, 99, 98, ..., 2, 1
- **Инкрементальное обновление**: 
  - Если существующие машины имеют max(sort_number) = 5
  - И найдено 3 новые машины: A (новая), B, C (старая)
  - То новые машины получают номера: A=8, B=7, C=6

**Результат**: При сортировке по убыванию `sort_number` получаем самые новые машины первыми.

## Преимущества

1. **Универсальность**: Работает для всех источников данных
2. **Гибкость**: Можно сортировать по источнику и новизне
3. **Эффективность**: Не требует дополнительных запросов к базе данных
4. **Простота**: Легко интегрируется в существующий код

## Ограничения

1. **Повторения**: Номера могут повторяться между разными источниками
2. **Локальность**: Нумерация относительная для каждого источника
3. **Порядок**: Зависит от порядка парсинга страниц

## Тестирование

Запустите тестовый скрипт для проверки работы:

```bash
cd pyparsers
python test_sort_number.py
```

Этот скрипт проверит:
- Обычный парсинг
- Инкрементальное обновление
- Полный парсинг
- Примеры сортировки 