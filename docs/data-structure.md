# Структура данных, возвращаемых парсерами

## Формат отправки в datahub

Данные отправляются в следующем формате:

```json
{
  "task_id": "uuid-задачи",
  "source": "che168" | "dongchedi",
  "task_type": "full" | "incremental",
  "status": "done",
  "data": [
    {
      // Структура машины (см. ниже)
    }
  ]
}
```

## Структура данных для CHE168

### Базовые поля (из Che168Car)

```python
{
    "title": str | None,                    # Название объявления
    "sh_price": str | None,                 # Цена (строка)
    "price": str | None,                    # Цена (преобразована из sh_price)
    "image": str | None,                    # URL главного изображения
    "link": str,                           # URL объявления (всегда в формате https://m.che168.com/cardetail/index?infoid={car_id})
    "car_name": str | None,                # Название машины
    "car_year": int | None,                # Год выпуска
    "year": int | None,                    # Год (дубликат car_year, преобразован в int)
    "car_mileage": str | None,             # Пробег (строка, например "5.2万公里")
    "mileage": int | None,                 # Пробег в км (преобразован из car_mileage)
    "car_source_city_name": str | None,    # Город
    "city": str | None,                    # Город (дубликат car_source_city_name)
    "brand_name": str | None,               # Марка
    "series_name": str | None,              # Модель
    "brand_id": int | None,                # ID марки
    "series_id": int | None,               # ID модели
    "shop_id": int | None,                 # ID магазина
    "car_id": int,                         # ID машины (обязательное поле, генерируется из link если отсутствует)
    "tags_v2": str | None,                 # Теги (через запятую)
    "is_available": bool,                  # Доступность (по умолчанию True)
    "source": "che168",                    # Источник
    "sort_number": int,                    # Порядковый номер на странице
    "recycling_fee": int | None,           # Утильсбор в рублях
    "customs_duty": int | None,            # Таможенная пошлина в рублях
    "first_registration_time": str | None, # Дата первой регистрации (YYYY-MM-DD)
    "power": int | None                    # Мощность в л.с.
}
```

### Дополнительные поля (добавляются при обработке)

- `sort_number` - порядковый номер на странице (добавляется автоматически)
- `source` - всегда "che168" (добавляется автоматически)
- `year` - преобразуется из `car_year` в int
- `mileage` - преобразуется из `car_mileage` в км (int)
- `city` - копируется из `car_source_city_name`
- `price` - копируется из `sh_price` (если не пусто)

## Структура данных для DONGCHEDI

### Базовые поля (из DongchediCar)

```python
{
    "uuid": str | None,                    # UUID машины (генерируется автоматически)
    "title": str | None,                    # Название объявления
    "sh_price": str | None,                 # Цена (строка, закодированная)
    "price": float | None,                  # Цена в wan юаней (10,000 юаней)
    "image": str | None,                    # URL главного изображения
    "link": str | None,                     # URL объявления
    "car_name": str | None,                 # Название машины
    "car_year": int | None,                 # Год выпуска
    "year": int | None,                     # Год (копия car_year)
    "car_mileage": str | None,              # Пробег (строка)
    "mileage": int | None,                  # Пробег в км
    "car_source_city_name": str | None,     # Город (из API)
    "city": str | None,                     # Город (декодированный)
    "brand_name": str | None,                # Марка
    "series_name": str | None,               # Модель
    "brand_id": int | None,                  # ID марки
    "series_id": int | None,                 # ID модели
    "shop_id": int | None,                   # ID магазина
    "car_id": int | None,                   # ID машины
    "sku_id": str | None,                   # SKU ID (строка!)
    "tags_v2": str | None,                  # Теги v2 (JSON строка)
    "tags": str | None,                     # Теги (JSON строка)
    "source": "dongchedi",                  # Источник
    "is_available": bool,                   # Доступность
    "sort_number": int,                     # Порядковый номер
    "description": str | None,               # Описание
    "color": str | None,                    # Цвет
    "transmission": str | None,              # Трансмиссия
    "fuel_type": str | None,                # Тип топлива
    "engine_volume": str | None,            # Объем двигателя (строка)
    "engine_volume_ml": int | None,         # Объем двигателя в мл
    "body_type": str | None,                # Тип кузова
    "drive_type": str | None,                # Тип привода
    "condition": str | None,                 # Состояние
    "created_at": str | None,               # Дата создания (RFC3339)
    "updated_at": str | None,               # Дата обновления (RFC3339)
    
    # Технические характеристики
    "power": int | None,                    # Мощность в л.с.
    "torque": float | None,                 # Крутящий момент в Н·м
    "acceleration": float | None,            # Разгон до 100 км/ч (сек)
    "max_speed": int | None,                # Максимальная скорость (км/ч)
    "fuel_consumption": float | None,        # Расход топлива (л/100км)
    "emission_standard": str | None,        # Экологический стандарт
    
    # Размеры и вес
    "length": int | None,                   # Длина (мм)
    "width": int | None,                    # Ширина (мм)
    "height": int | None,                   # Высота (мм)
    "wheelbase": int | None,                # Колесная база (мм)
    "curb_weight": int | None,              # Снаряженная масса (кг)
    "gross_weight": str | None,              # Полная масса
    
    # Двигатель
    "engine_type": str | None,              # Тип двигателя
    "engine_code": str | None,              # Код двигателя
    "cylinder_count": str | None,           # Количество цилиндров
    "valve_count": str | None,              # Количество клапанов
    "compression_ratio": str | None,         # Степень сжатия
    "turbo_type": str | None,               # Тип турбонаддува
    
    # Электрические характеристики
    "battery_capacity": float | None,       # Емкость батареи (кВт·ч)
    "electric_range": int | None,           # Запас хода (км)
    "charging_time": str | None,            # Время зарядки
    "fast_charge_time": str | None,        # Время быстрой зарядки
    "charge_port_type": str | None,         # Тип разъема зарядки
    
    # Трансмиссия
    "transmission_type": str | None,         # Тип трансмиссии
    "gear_count": str | None,               # Количество передач
    "differential_type": str | None,         # Тип дифференциала
    
    # Подвеска и тормоза
    "front_suspension": str | None,         # Передняя подвеска
    "rear_suspension": str | None,          # Задняя подвеска
    "front_brakes": str | None,             # Передние тормоза
    "rear_brakes": str | None,              # Задние тормоза
    "brake_system": str | None,             # Тормозная система
    
    # Колеса и шины
    "wheel_size": str | None,               # Размер колес
    "tire_size": str | None,                # Размер шин
    "wheel_type": str | None,               # Тип колес
    "tire_type": str | None,                # Тип шин
    
    # Безопасность
    "airbag_count": str | None,             # Количество подушек безопасности
    "abs": str | None,                      # ABS
    "esp": str | None,                      # ESP
    "tcs": str | None,                      # TCS
    "hill_assist": str | None,              # Помощь при подъеме
    "blind_spot_monitor": str | None,       # Мониторинг слепых зон
    "lane_departure": str | None,           # Предупреждение о смене полосы
    
    # Комфорт
    "air_conditioning": str | None,         # Кондиционер
    "climate_control": str | None,          # Климат-контроль
    "seat_heating": str | None,             # Подогрев сидений
    "seat_ventilation": str | None,         # Вентиляция сидений
    "seat_massage": str | None,             # Массаж сидений
    "steering_wheel_heating": str | None,   # Подогрев руля
    
    # Мультимедиа
    "navigation": str | None,               # Навигация
    "audio_system": str | None,             # Аудиосистема
    "speakers_count": str | None,           # Количество динамиков
    "bluetooth": str | None,                # Bluetooth
    "usb": str | None,                      # USB
    "aux": str | None,                      # AUX
    
    # Освещение
    "headlight_type": str | None,           # Тип фар
    "fog_lights": str | None,               # Противотуманные фары
    "led_lights": str | None,               # LED фары
    "daytime_running": str | None,          # Дневные ходовые огни
    
    # История
    "first_registration_time": str | None,  # Дата первой регистрации
    "owner_count": int | None,              # Количество владельцев
    "accident_history": str | None,         # История аварий
    "service_history": str | None,          # История обслуживания
    "warranty_info": str | None,            # Информация о гарантии
    "inspection_date": str | None,          # Дата техосмотра
    "insurance_info": str | None,           # Информация о страховке
    
    # Дополнительно
    "interior_color": str | None,           # Цвет салона
    "exterior_color": str | None,           # Цвет кузова
    "upholstery": str | None,               # Обивка
    "sunroof": str | None,                  # Люк
    "panoramic_roof": str | None,           # Панорамная крыша
    
    # Метаданные
    "view_count": int | None,               # Количество просмотров
    "favorite_count": int | None,          # Количество избранного
    "contact_info": str | None,            # Контактная информация
    "dealer_info": str | None,              # Информация о дилере
    "certification": str | None,           # Сертификация
    
    # Изображения
    "image_gallery": str | None,            # Галерея изображений (JSON строка)
    "image_count": int | None,              # Количество изображений
    
    # Дополнительные характеристики
    "seat_count": str | None,               # Количество мест
    "door_count": int | None,               # Количество дверей
    "trunk_volume": str | None,             # Объем багажника
    "fuel_tank_volume": str | None,         # Объем топливного бака
    
    # Таможенные сборы
    "recycling_fee": int | None,            # Утильсбор в рублях
    "customs_duty": int | None,             # Таможенная пошлина в рублях
    
    # Флаги
    "has_details": bool | None,            # Есть ли детальная информация
    "last_detail_update": str | None        # Дата последнего обновления деталей
}
```

## Важные замечания

### CHE168
- `car_id` - обязательное поле, генерируется из `link` (MD5 hash) если отсутствует
- `link` - всегда нормализуется в формат `https://m.che168.com/cardetail/index?infoid={car_id}`
- `year` - фильтруется: машины старше 2017 года пропускаются
- `mileage` - преобразуется из строки (например "5.2万公里") в км (int)

### DONGCHEDI
- `sku_id` - всегда строка (преобразуется из int если нужно)
- `tags` и `tags_v2` - JSON строки (списки преобразуются в JSON)
- `sh_price` - декодируется специальной функцией
- `created_at` и `updated_at` - формат RFC3339 (YYYY-MM-DDTHH:MM:SSZ)

## Пример полного payload для отправки в datahub

```json
{
  "task_id": "c4c3b203-8989-41fb-8fc3-4a92c8a433cb",
  "source": "che168",
  "task_type": "incremental",
  "status": "done",
  "data": [
    {
      "title": "2020年 奔驰 C200",
      "sh_price": "25.8",
      "price": "25.8",
      "image": "https://image.che168.com/...",
      "link": "https://m.che168.com/cardetail/index?infoid=123456",
      "car_name": "奔驰 C200",
      "car_year": 2020,
      "year": 2020,
      "car_mileage": "5.2万公里",
      "mileage": 52000,
      "car_source_city_name": "北京",
      "city": "北京",
      "brand_name": "奔驰",
      "series_name": "C级",
      "brand_id": 1,
      "series_id": 10,
      "shop_id": 100,
      "car_id": 123456,
      "tags_v2": "精品车,一手车",
      "is_available": true,
      "source": "che168",
      "sort_number": 1
    }
  ]
}
```




