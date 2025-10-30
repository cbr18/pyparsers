# Структура парсеров для dongchedi

## 📋 Три основных парсера для получения полной информации о машине

### 1. **`fetch_cars_by_page(page)` - Базовый парсер списка машин**

**URL**: `https://www.dongchedi.com/motor/pc/sh/sh_sku_list?page={page}`

**Метод**: API запрос (POST/GET)

**Что парсит**:
- Список машин на странице (до 80 машин)
- Базовая информация для каждой машины
- Используется для первоначальной загрузки

**Поля**:
- `title`, `car_name`, `brand_name`, `series_name`
- `sh_price`, `price`
- `year`, `mileage`
- `city`, `car_source_city_name`
- `car_id`, `sku_id`
- `image` - ОДНА картинка

**Результат**: Машины с `has_details = false`

---

### 2. **`fetch_car_detail(sku_id)` - Детальная страница машины**

**URL**: `https://www.dongchedi.com/usedcar/{sku_id}` (например, 21122808)

**Метод**: Selenium + BeautifulSoup

**Что парсит из `__NEXT_DATA__` → `skuDetail`**:

#### Основная информация:
- `title`, `sh_price`
- `car_info` (год, пробег, марка, модель, город)
- `description` (из `sh_car_desc`)

#### 🖼️ **Галерея изображений**:
- `head_images[]` → **`image_gallery`** (все картинки через пробел)
- `image` (первая картинка)
- `image_count` (количество картинок)

#### 👥 Владельцы и история:
- `other_params[]`:
  - `过户次数` → `owner_count` (количество владельцев)
  - `上牌地` → `inspection_date` (место регистрации)
  - `内饰颜色` → `interior_color` (цвет салона)
  - `车身颜色` → `exterior_color` (цвет кузова)

#### 🏢 Информация о дилере:
- `shop_info`:
  - `shop_name`, `shop_address`, `business_time`, `sales_car_num`
  - Объединяется в `dealer_info`

#### ⭐ Сертификация:
- `tags[]` → `certification` (все теги через точку с запятой)

#### 📊 Метрики:
- `favored_count` → `favorite_count` (количество в избранном)

**Результат**: Детальная информация о машине + галерея

---

### 3. **`fetch_car_specifications(car_id)` - Технические характеристики**

**URL**: `https://www.dongchedi.com/auto/params-carIds-{car_id}` (например, 52683)

**Метод**: Selenium + BeautifulSoup

**Что парсит из таблицы параметров**:

#### ⚡ Мощность и производительность:
- `最大功率(kW)` → `power` (мощность)
- `最大扭矩(N·m)` → `torque` (крутящий момент)
- `官方百公里加速时间(s)` → `acceleration` (разгон)
- `最高车速(km/h)` → `max_speed` (макс. скорость)

#### 📐 Размеры:
- `长x宽x高(mm)` → парсится на `length`, `width`, `height`

#### 🔋 Электромобили:
- `纯电续航里程(km)` → `electric_range`
- `充电时间(小时)` → `charging_time`
- `快充时间(小时)` → `fast_charge_time`

#### 🚗 ДВС:
- `发动机` → `engine_type`
- `排量(mL)` → `engine_volume`

#### ⚙️ Трансмиссия и шасси:
- `变速箱` → `transmission_type`
- `驱动方式` → `drive_type`
- `前悬架类型` → `front_suspension`
- `后悬架类型` → `rear_suspension`
- `前制动器类型` → `front_brakes`
- `后制动器类型` → `rear_brakes`

#### 🛞 Колеса:
- `轮胎规格` → `tire_size`
- `轮毂规格` → `wheel_size`

#### 🛡️ Безопасность:
- `主/副驾驶座安全气囊` → `airbag_count`
- `ABS防抱死` → `abs`
- `ESP车身稳定系统` → `esp`
- `TCS牵引力控制` → `tcs`
- `上坡辅助` → `hill_assist`
- `盲区监测` → `blind_spot_monitor`
- `车道偏离预警` → `lane_departure`

#### 🌡️ Комфорт:
- `空调` → `air_conditioning`
- `自动空调` → `climate_control`
- `座椅加热` → `seat_heating`
- `座椅通风` → `seat_ventilation`
- `座椅按摩` → `seat_massage`
- `方向盘加热` → `steering_wheel_heating`

#### 📱 Мультимедиа:
- `GPS导航` → `navigation`
- `音响系统` → `audio_system`
- `扬声器数量` → `speakers_count`
- `蓝牙` → `bluetooth`
- `USB接口` → `usb`
- `AUX接口` → `aux`

#### 💡 Освещение:
- `前大灯类型` → `headlight_type`
- `前雾灯` → `fog_lights`
- `LED大灯` → `led_lights`
- `日间行车灯` → `daytime_running`

#### 📦 Дополнительно:
- `座位数` → `seat_count`
- `车门数` → `door_count`
- `行李厢容积(L)` → `trunk_volume`
- `油箱容积(L)` → `fuel_tank_volume`

**Результат**: Полные технические характеристики

---

## 🔄 Процесс объединения данных

### Метод `enhance_car_with_details(car_obj, sku_id, car_id)`:

1. Вызывает `fetch_car_detail(sku_id)` → детали + **галерея картинок**
2. Вызывает `fetch_car_specifications(car_id)` → характеристики
3. Объединяет все данные в один объект
4. Устанавливает `has_details = true`

---

## 📸 Формат галереи изображений

### Пример данных:

**В JSON (`__NEXT_DATA__`):**
```json
"head_images": [
  "https://p3-dcd.byteimg.com/img1.jpg",
  "https://p3-dcd.byteimg.com/img2.jpg",
  "https://p3-dcd.byteimg.com/img3.jpg"
]
```

**В БД (`image_gallery`):**
```
https://p3-dcd.byteimg.com/img1.jpg https://p3-dcd.byteimg.com/img2.jpg https://p3-dcd.byteimg.com/img3.jpg
```

**Использование (разбить обратно):**
```javascript
const images = car.image_gallery.split(' ');
// ['https://p3-dcd.byteimg.com/img1.jpg', 'https://p3-dcd.byteimg.com/img2.jpg', ...]
```

**Python:**
```python
images = car.image_gallery.split(' ')
```

**Go:**
```go
images := strings.Split(car.ImageGallery, " ")
```

---

## ✅ Итого по картинкам

**Да, поле `image_gallery` парсится в методе `fetch_car_detail(sku_id)`!**

Извлекается из `__NEXT_DATA__` → `skuDetail` → `head_images[]` и сохраняется как строка через пробел.

