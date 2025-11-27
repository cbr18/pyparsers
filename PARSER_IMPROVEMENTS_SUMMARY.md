# Улучшения парсера Che168 - Сводка

## Дата: 2025-11-15

## Проблема
- Парсер извлекал только `image_gallery` (2 фото)
- Поле `power` не извлекалось
- Большинство полей из `domain.Car` не заполнялись

## Решение

### 1. Исправлена логика извлечения данных

#### Способ 1: Поиск меток с классом `css-1rynq56`
**Структура**: `<div><div>ЗНАЧЕНИЕ</div><div class="css-1rynq56">МЕТКА</div></div>`

**Ключевое изменение**: Значение может НЕ иметь класса `css-1rynq56`, поэтому теперь ищем среди ВСЕХ прямых потомков родителя, а не только с классом `css-1rynq56`.

**Метки** (Способ 1):
- 发动机 (engine_type)
- 变速箱 (transmission)
- 百公里油耗 (fuel_consumption)
- 燃料形式 (fuel_type)
- 排量 (engine_volume)
- 上牌时间 (first_registration_time)
- 表显里程 (mileage)
- 排放标准 (emission_standard)
- 所在地区 (city)

#### Способ 2: Поиск любых div с метками
**Структура**: `<div><div>МЕТКА(единицы)</div><div>ЗНАЧЕНИЕ</div></div>`

**Расширенный список меток** (110+ полей):

##### Мощность и производительность
- 最大马力(Ps), 最大马力 → power
- 最大功率(kW), 最大功率 → power_kw
- 最大扭矩(N·m), 最大扭矩 → torque
- 加速时间, 0-100km/h加速 → acceleration
- 最高车速 → max_speed

##### Двигатель
- 发动机型号 → engine_code
- 气缸数 → cylinder_count
- 气缸排列形式 → cylinder_arrangement
- 每缸气门数 → valve_count
- 压缩比 → compression_ratio
- 进气形式 → turbo_type

##### Размеры
- 长x宽x高, 长*宽*高, 长×宽×高, 车身尺寸 → dimensions (обрабатывается специально)
- 轴距, 轴距(mm) → wheelbase
- 整备质量, 整备质量(kg) → curb_weight
- 总质量 → gross_weight

##### Трансмиссия и привод
- 变速箱类型 → transmission_type
- 档位个数 → gear_count
- 驱动方式 → drive_type
- 四驱形式 → differential_type

##### Подвеска и тормоза
- 前悬架类型 → front_suspension
- 后悬架类型 → rear_suspension
- 前制动器类型 → front_brakes
- 后制动器类型 → rear_brakes
- 驻车制动类型 → brake_system

##### Колеса
- 轮胎规格 → tire_size
- 前轮胎规格 → front_tire_size
- 后轮胎规格 → rear_tire_size
- 轮圈材质 → wheel_type

##### Безопасность
- 安全气囊数量 → airbag_count
- 主/副驾驶座安全气囊 → airbag_front
- ABS防抱死 → abs
- 车身稳定控制 → esp
- 牵引力控制 → tcs
- 上坡辅助 → hill_assist
- 陡坡缓降 → hill_descent
- 并线辅助 → blind_spot_monitor
- 车道偏离预警 → lane_departure

##### Электромобили
- 电池容量 → battery_capacity
- 纯电续航 → electric_range
- 快充时间 → fast_charge_time
- 慢充时间 → charging_time

##### Комфорт
- 空调, 空调类型 → air_conditioning / climate_control
- 座椅加热 → seat_heating
- 座椅通风 → seat_ventilation
- 座椅按摩 → seat_massage
- 方向盘加热 → steering_wheel_heating

##### Мультимедиа
- GPS导航, 导航系统 → navigation
- 音响品牌 → audio_system
- 扬声器数量 → speakers_count
- 蓝牙, 蓝牙/车载电话, 车载电话 → bluetooth
- USB接口 → usb
- AUX接口 → aux

##### Освещение
- 大灯类型, 前大灯, 前大灯类型 → headlight_type
- 雾灯 → fog_lights
- LED日间行车灯 → daytime_running

##### Интерьер и экстерьер
- 内饰颜色 → interior_color
- 外观颜色, 车身颜色 → exterior_color
- 座椅材质 → upholstery
- 天窗类型 → sunroof
- 全景天窗 → panoramic_roof

##### Дополнительные
- 座位数, 座椅数 → seat_count
- 门数 → door_count
- 行李箱容积, 后备箱容积 → trunk_volume
- 油箱容积 → fuel_tank_volume

### 2. Пост-обработка данных

#### Преобразование dimensions
`4783*1810*1442` → `length: 4783mm, width: 1810mm, height: 1442mm`

#### Преобразование mileage
`5.47万公里` → `54700` (км)

#### Извлечение year
`2016-01-01` (из first_registration_time) → `2016`

### 3. Маппинг в domain.Car

Обновлен `_convert_to_domain_car` в `detailed_api.py` для корректного преобразования всех извлеченных полей в формат Go структуры `domain.Car`.

## Тестирование на локальном HTML

На тестовом HTML файле `车源详情.html`:

**Результат**: Извлечено **34 поля**

### Основные
- engine_type: 2.0T
- transmission: 自动
- fuel_type: 汽油
- fuel_consumption: 6.3L
- engine_volume: 2.0

### Мощность
- power: 184
- power_kw: 135
- torque: 300

### Размеры
- wheelbase: 2920
- curb_weight: 1650

### Двигатель
- engine_code: 274 920
- turbo_type: 涡轮增压

### Трансмиссия
- transmission_type: 手自一体变速箱(AT)
- drive_type: 前置后驱

### Подвеска/Тормоза
- front_suspension: 多连杆式独立悬架
- rear_suspension: 多连杆式独立悬架
- front_brakes: 通风盘式
- rear_brakes: 盘式

### Безопасность
- abs: ●
- hill_assist: ●
- blind_spot_monitor: -

### Комфорт
- bluetooth: ●

## Следующие шаги

1. ✅ Исправить логику извлечения (БЕЗ требования класса css-1rynq56 для значений)
2. ✅ Расширить список меток до 110+ полей
3. ✅ Добавить пост-обработку (dimensions, mileage, year)
4. ✅ Обновить маппинг в domain.Car
5. ⏳ Проверить работу на реальных запросах через API
6. ⏳ Улучшить Selenium клики для раскрытия всей информации

## Файлы изменены

- `pyparsers/api/che168/detailed_parser.py` - основная логика парсинга
- `pyparsers/api/che168/detailed_api.py` - API и конвертация в domain.Car
- `datahub/internal/usecase/enhancement_worker.go` - условие `has_details`

