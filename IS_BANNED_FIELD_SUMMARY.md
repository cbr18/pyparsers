# Добавлено поле is_banned

## ✅ Что сделано:

### 1. Модели обновлены:

- **Che168DetailedCar** (`pyparsers/api/che168/models/detailed_car.py`):
  - Добавлено поле: `is_banned: Optional[bool] = False`
  - Расположение: строка 143

- **DongchediCar** (`pyparsers/api/dongchedi/models/car.py`):
  - Добавлено поле: `is_banned: Optional[bool] = False`
  - Расположение: строка 163

### 2. Передача в ответах API:

- **Che168** (`pyparsers/api/che168/detailed_api.py`):
  - Поле передается через `_convert_to_domain_car()` → `domain_car['is_banned']`
  - Расположение: строка 288

- **Dongchedi**:
  - Поле передается через `car_info['is_banned']` в ответах API

---

## 📋 Логика установки is_banned:

### CHE168:

**is_banned = True** когда:
1. API возвращает **403 Forbidden** для `getcarinfo`
2. И не удалось получить **image_gallery** ИЛИ **first_registration_time** через fallback

**Места установки:**
- `_fetch_carinfo_api()` - при 403 ошибке (строка 561)
- `_fetch_carinfo_api()` - в exception handler при 403 (строка 705)
- `parse_car_details()` - проверка критичных данных (строки 379-391)

### DONGCHEDI:

**is_banned = True** когда:
1. Страница заблокирована (captcha, blocked, access denied)
2. И не удалось получить **image_gallery** ИЛИ **first_registration_time**
3. Или `__NEXT_DATA__` не найден и мобильная версия не помогла

**Места установки:**
- При блокировке страницы (строка 752)
- Если `__NEXT_DATA__` не найден и критичные данные не получены (строка 1041)
- В конце парсинга при проверке критичных данных (строки 1174-1188)

---

## 🔍 Когда поле устанавливается:

### CHE168:
- API заблокирован (403) → `is_banned = True`
- Если fallback сработал → `is_banned = True` (API все равно заблокирован)
- Если fallback не сработал и нет критичных данных → `is_banned = True`

### DONGCHEDI:
- Страница заблокирована → `is_banned = True`
- `__NEXT_DATA__` не найден и нет критичных данных → `is_banned = True`
- Мобильная версия не помогла → `is_banned = True`

---

## 📊 Передача в ответах:

Поле `is_banned` передается в ответах API через:
- `domain_car['is_banned']` для che168
- `car_info['is_banned']` для dongchedi

И включается в данные, отправляемые в datahub.

---

## 🎯 Цель:

Информировать клиентов API о том, что источник был заблокирован
и не удалось получить критичные данные (image_gallery или first_registration_time).

