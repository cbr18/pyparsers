# Схема базы данных DataHub

## Таблица: `cars`

### Основные идентификаторы

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| uuid | VARCHAR(36) | string | Уникальный идентификатор (PK) | "550e8400-e29b-41d4-a716-446655440000" |
| source | VARCHAR(255) | string | Источник данных | "dongchedi", "che168", "encar" |
| car_id | BIGINT | int64 | ID автомобиля из источника | 123456, 55406760 |
| sku_id | VARCHAR(255) | string | SKU идентификатор | "abc123def456" |

### Основная информация

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| title | TEXT | string | Полное название | "极狐阿尔法S 2023款 708S+" |
| car_name | VARCHAR(255) | string | Название модели | "极狐阿尔法S", "Macan" |
| year | SMALLINT | int | Год выпуска | 2020, 2023 |
| mileage | INTEGER | int32 | Пробег (км) | 50000, 9200 |
| price | VARCHAR(255) | string | Цена (оригинальная строка) | "450000", "13.88" |
| rub_price | DOUBLE PRECISION | float64 | Цена в рублях | 4500000.0, 1388000.0 |
| final_price | DOUBLE PRECISION | float64 | Финальная цена с учетом сборов | 5000000.0 |
| customs_fee | DOUBLE PRECISION | float64 | Таможенный сбор | 250000.0 |

### Медиа и ссылки

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| image | TEXT | string | Главное изображение (URL) | "https://example.com/car.jpg" |
| image_gallery | TEXT | string | Галерея изображений (через пробел) | "url1 url2 url3" |
| image_count | INTEGER | int | Количество изображений | 15 |
| link | TEXT | string | Ссылка на источник | "https://dongchedi.com/car/123456" |

### Бренд и серия

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| brand_name | VARCHAR(255) | string | Название бренда | "极狐", "BMW", "Macan" |
| brand_id | INTEGER | int | ID бренда из источника | 40, 36 |
| mybrand_id | UUID | *string | UUID бренда в нашей БД | "uuid-here" |
| series_name | VARCHAR(255) | string | Название серии | "阿尔法S", "X系列" |
| series_id | INTEGER | int | ID серии из источника | 2838, 450 |

### Локация

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| city | VARCHAR(255) | string | Город | "北京", "上海", "苏州" |
| car_source_city_name | VARCHAR(255) | string | Полное название города | "北京市", "苏州市" |

### Дилер

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| shop_id | VARCHAR(255) | string | ID магазина/дилера | "647918", "619794" |
| dealer_info | TEXT | string | Информация о дилере | "Автосалон BMW" |
| contact_info | TEXT | string | Контактная информация | "тел: +7..." |

### Технические характеристики

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| color | VARCHAR(255) | string | Цвет | "白色", "蓝色", "红色" |
| interior_color | VARCHAR(255) | string | Цвет салона | "黑色" |
| exterior_color | VARCHAR(255) | string | Цвет кузова | "白色" |
| transmission | VARCHAR(255) | string | Трансмиссия | "自动", "手动" |
| transmission_type | VARCHAR(255) | string | Тип коробки передач | "AT", "MT", "CVT" |
| gear_count | VARCHAR(255) | string | Количество передач | "6", "8" |
| fuel_type | VARCHAR(255) | string | Тип топлива | "纯电动", "增程式", "汽油" |
| engine_volume | VARCHAR(255) | string | Объем двигателя | "0L", "1.5L", "2.0T" |
| engine_volume_ml | VARCHAR(255) | string | Объем двигателя в мл | "1500", "2000" |
| body_type | VARCHAR(255) | string | Тип кузова | "轿车", "SUV", "轿跑车" |
| drive_type | VARCHAR(255) | string | Тип привода | "前驱", "四驱", "后驱" |
| condition | VARCHAR(255) | string | Состояние | "新车", "准新车" |

### Двигатель (ДВС)

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| engine_type | VARCHAR(255) | string | Тип двигателя | "V6", "Inline-4" |
| engine_code | VARCHAR(255) | string | Код двигателя | "B48B20" |
| cylinder_count | VARCHAR(255) | string | Количество цилиндров | "4", "6" |
| valve_count | VARCHAR(255) | string | Количество клапанов | "16", "24" |
| compression_ratio | VARCHAR(255) | string | Степень сжатия | "10.5:1" |
| turbo_type | VARCHAR(255) | string | Тип турбонаддува | "Turbo", "Supercharger" |

### Электрические характеристики

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| battery_capacity | VARCHAR(255) | string | Емкость батареи (кВт·ч) | "93.6kWh", "100kWh" |
| electric_range | VARCHAR(255) | string | Запас хода (км) | "708公里", "500" |
| charging_time | VARCHAR(255) | string | Время зарядки | "8小时" |
| fast_charge_time | VARCHAR(255) | string | Время быстрой зарядки | "30分钟" |
| charge_port_type | VARCHAR(255) | string | Тип зарядного порта | "CCS", "CHAdeMO" |

### Производительность

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| power | VARCHAR(255) | string | Мощность (л.с./кВт) | "300马力", "220kW" |
| torque | VARCHAR(255) | string | Крутящий момент (Н·м) | "400N·m" |
| acceleration | VARCHAR(255) | string | Разгон до 100 км/ч (сек) | "4.2秒", "5.5" |
| max_speed | VARCHAR(255) | string | Максимальная скорость (км/ч) | "200", "180" |
| fuel_consumption | VARCHAR(255) | string | Расход топлива (л/100км) | "8.5", "6.2" |
| emission_standard | VARCHAR(255) | string | Экологический класс | "Euro 6", "国六" |

### Размеры и вес

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| length | VARCHAR(255) | string | Длина (мм) | "4930", "4850" |
| width | VARCHAR(255) | string | Ширина (мм) | "1940", "1900" |
| height | VARCHAR(255) | string | Высота (мм) | "1770", "1700" |
| wheelbase | VARCHAR(255) | string | Колесная база (мм) | "2920", "2800" |
| curb_weight | VARCHAR(255) | string | Снаряженная масса (кг) | "2100", "1950" |
| gross_weight | VARCHAR(255) | string | Полная масса (кг) | "2500" |
| trunk_volume | VARCHAR(255) | string | Объем багажника | "550L" |
| fuel_tank_volume | VARCHAR(255) | string | Объем топливного бака | "70L" |

### Трансмиссия и привод

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| differential_type | VARCHAR(255) | string | Тип дифференциала | "Limited Slip" |

### Подвеска и тормоза

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| front_suspension | VARCHAR(255) | string | Передняя подвеска | "McPherson" |
| rear_suspension | VARCHAR(255) | string | Задняя подвеска | "Multi-link" |
| front_brakes | VARCHAR(255) | string | Передние тормоза | "Ventilated Disc" |
| rear_brakes | VARCHAR(255) | string | Задние тормоза | "Disc" |
| brake_system | VARCHAR(255) | string | Тормозная система | "ABS+EBD" |

### Колеса и шины

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| wheel_size | VARCHAR(255) | string | Размер колес | "19寸", "20x8.5J" |
| tire_size | VARCHAR(255) | string | Размер шин | "255/45R19" |
| wheel_type | VARCHAR(255) | string | Тип колес | "Alloy" |
| tire_type | VARCHAR(255) | string | Тип шин | "Summer", "All-season" |

### Безопасность

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| airbag_count | VARCHAR(255) | string | Количество подушек безопасности | "8", "6" |
| abs | VARCHAR(255) | string | АБС | "有", "Yes" |
| esp | VARCHAR(255) | string | ESP | "有", "Yes" |
| tcs | VARCHAR(255) | string | TCS | "有" |
| hill_assist | VARCHAR(255) | string | Помощь при трогании на подъеме | "有" |
| blind_spot_monitor | VARCHAR(255) | string | Мониторинг слепых зон | "有" |
| lane_departure | VARCHAR(255) | string | Система предупреждения о покидании полосы | "有" |

### Комфорт

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| air_conditioning | VARCHAR(255) | string | Кондиционер | "有" |
| climate_control | VARCHAR(255) | string | Климат-контроль | "有", "双区" |
| seat_heating | VARCHAR(255) | string | Подогрев сидений | "有", "前排" |
| seat_ventilation | VARCHAR(255) | string | Вентиляция сидений | "有" |
| seat_massage | VARCHAR(255) | string | Массаж сидений | "有" |
| steering_wheel_heating | VARCHAR(255) | string | Подогрев руля | "有" |
| upholstery | VARCHAR(255) | string | Обивка салона | "真皮", "Leather" |
| sunroof | VARCHAR(255) | string | Люк | "有" |
| panoramic_roof | VARCHAR(255) | string | Панорамная крыша | "有" |

### Мультимедиа

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| navigation | VARCHAR(255) | string | Навигация | "有", "GPS" |
| audio_system | VARCHAR(255) | string | Аудиосистема | "BOSE", "Harman Kardon" |
| speakers_count | VARCHAR(255) | string | Количество динамиков | "12", "16" |
| bluetooth | VARCHAR(255) | string | Bluetooth | "有" |
| usb | VARCHAR(255) | string | USB | "有", "2个" |
| aux | VARCHAR(255) | string | AUX | "有" |

### Освещение

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| headlight_type | VARCHAR(255) | string | Тип фар | "LED", "Xenon" |
| fog_lights | VARCHAR(255) | string | Противотуманные фары | "有" |
| led_lights | VARCHAR(255) | string | LED освещение | "有" |
| daytime_running | VARCHAR(255) | string | Дневные ходовые огни | "有" |

### История и состояние

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| first_registration_time | DATE | string | Дата первой регистрации | "2020-05-01", "2023-01-01" |
| owner_count | INTEGER | int | Количество владельцев | 1, 2, 0 |
| accident_history | TEXT | string | История ДТП | "无事故" |
| service_history | TEXT | string | История обслуживания | "定期保养" |
| warranty_info | TEXT | string | Информация о гарантии | "3年保修" |
| inspection_date | VARCHAR(255) | string | Дата техосмотра | "2024-12-01" |
| insurance_info | TEXT | string | Информация о страховке | "全险" |

### Дополнительные характеристики

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| seat_count | VARCHAR(255) | string | Количество мест | "5", "7" |
| door_count | VARCHAR(255) | string | Количество дверей | "4", "5" |

### Сборы

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| recycling_fee | VARCHAR(31) | string | Утильсбор | "20000" |
| customs_duty | VARCHAR(31) | string | Таможенный сбор | "150000" |

### Метаданные

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| tags | TEXT | string | Теги (старый формат) | "tag1,tag2" |
| tags_v2 | TEXT | string | Теги (новый формат) | "认证,精品" |
| certification | TEXT | string | Сертификация | "认证车" |
| description | TEXT | string | Описание | "全新极狐阿尔法S，续航708公里" |
| is_available | BOOLEAN | bool | Доступность | true, false |
| sort_number | INTEGER | int | Порядок сортировки | 100, 0 |
| view_count | INTEGER | int | Количество просмотров | 150, 0 |
| favorite_count | INTEGER | int | Количество добавлений в избранное | 25, 0 |
| has_details | BOOLEAN | bool | Наличие детальной информации | true, false |
| last_detail_update | TIMESTAMP | time.Time | Время последнего обновления деталей | "2024-01-15 10:30:00" |
| failed_enhancement_attempts | INTEGER | int | Счетчик неудачных попыток улучшения | 0, 3 |
| created_at | TIMESTAMP WITH TIME ZONE | time.Time | Время создания | "2024-01-01 12:00:00+00" |
| updated_at | TIMESTAMP WITH TIME ZONE | time.Time | Время обновления | "2024-01-15 15:30:00+00" |

---

## Таблица: `brands`

| Поле | Тип PostgreSQL | Тип Go | Описание | Пример |
|------|----------------|--------|----------|--------|
| id | UUID | string | Уникальный идентификатор (PK) | "550e8400-e29b-41d4-a716-446655440000" |
| name | VARCHAR(255) | *string | Название бренда (переведенное) | "BMW", "Mercedes-Benz" |
| orig_name | VARCHAR(255) | *string | Оригинальное название бренда | "宝马", "奔驰" |
| aliases | TEXT | *string | Список алиасов (через запятую) | "BMW,巴伐利亚,宝马" |
| created_at | TIMESTAMP WITH TIME ZONE | time.Time | Время создания | "2024-01-01 12:00:00+00" |
| updated_at | TIMESTAMP WITH TIME ZONE | time.Time | Время обновления | "2024-01-15 15:30:00+00" |
| deleted_at | TIMESTAMP WITH TIME ZONE | *time.Time | Время удаления (soft delete) | NULL |

---

## Статистика

- **Таблица `cars`**: 140+ полей
- **Таблица `brands`**: 7 полей

## Индексы

### Таблица `cars`
- `uuid` (PRIMARY KEY)
- `source + car_id` (UNIQUE)
- `brand_name`
- `city`
- `year`
- `is_available`
- `has_details`
- `rub_price`
- `final_price`
- `mybrand_id`
- `owner_count`
- `view_count`
- `favorite_count`
- `failed_enhancement_attempts` (partial, WHERE > 0)

### Таблица `brands`
- `id` (PRIMARY KEY)
- `deleted_at` (для soft delete)




