# 🚀 Быстрый старт: Автоматическое обогащение машин

## Запуск системы

```bash
docker compose up --build
```

**Что происходит автоматически:**
1. ✅ Применяются миграции (новые поля в БД)
2. ✅ Запускается EnhancementWorker
3. ✅ Начинается автоматическое обогащение машин

---

## Проверка статуса

```bash
# Статус воркера
curl http://localhost:8080/enhancement/status
```

**Ответ:**
```json
{
  "is_running": true,
  "batch_size": 10,
  "delay_between_batches_sec": 300,
  "delay_between_cars_sec": 2,
  "max_concurrent": 3,
  "cars_without_details": {
    "dongchedi": 150
  }
}
```

---

## Управление процессом

### Остановить воркер:
```bash
curl -X POST http://localhost:8080/enhancement/stop
```

### Запустить воркер:
```bash
curl -X POST http://localhost:8080/enhancement/start
```

### Ускорить обработку:
```bash
curl -X POST http://localhost:8080/enhancement/config \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 50,
    "delay_between_batches_sec": 60,
    "delay_between_cars_sec": 1,
    "max_concurrent": 10
  }'
```

---

## Проверка данных в БД

### Количество машин с деталями:
```sql
SELECT COUNT(*) FROM cars WHERE has_details = true;
```

### Количество машин без деталей:
```sql
SELECT COUNT(*) FROM cars WHERE has_details = false OR has_details IS NULL;
```

### Пример машины с деталями:
```sql
SELECT 
  uuid, title, has_details, 
  image_gallery, image_count,
  power, torque, acceleration,
  dealer_info, certification,
  owner_count
FROM cars 
WHERE has_details = true 
LIMIT 1;
```

### Проверка галереи изображений:
```sql
SELECT uuid, title, image_count, 
  LENGTH(image_gallery) as gallery_length,
  SUBSTRING(image_gallery, 1, 100) as gallery_preview
FROM cars 
WHERE image_gallery IS NOT NULL 
LIMIT 5;
```

---

## Что парсится

### Из детальной страницы (sku_id):
- 🖼️ **Галерея изображений** (head_images → через пробел)
- 👥 **Владельцы** (过户次数)
- 🎨 **Цвета** (车身颜色, 内饰颜色)
- 🏢 **Дилер** (shop_info)
- ⭐ **Сертификация** (tags)
- 📊 **Метрики** (favored_count)

### Из страницы характеристик (car_id):
- ⚡ **Мощность** (最大功率)
- 🔧 **Крутящий момент** (最大扭矩)
- 🏁 **Разгон** (百公里加速时间)
- 📐 **Размеры** (长x宽x高)
- 🔋 **Электро** (续航里程, 充电时间)
- ⚙️ **Подвеска** (前/后悬架类型)
- 🛡️ **Безопасность** (气囊, ABS, ESP)
- 🌡️ **Комфорт** (空调, 座椅加热/通风/按摩)
- 📱 **Мультимедиа** (导航, 音响)
- 💡 **Освещение** (LED大灯, 雾灯)

---

## Логи

### Проверка логов воркера:
```bash
docker logs carcatch-datahub | grep -i "enhancement"
```

**Пример логов:**
```
2025/10/20 21:15:40 Enhancement worker started in background
2025/10/20 21:15:40 Starting enhancement batch processing...
2025/10/20 21:15:40 Found 10 cars without details, processing...
2025/10/20 21:15:45 [1/10] Successfully enhanced car xxx (sku_id: 21122808)
2025/10/20 21:15:47 [2/10] Successfully enhanced car yyy (sku_id: 21122809)
...
2025/10/20 21:16:20 Batch processing completed: enhanced 10 out of 10 cars
```

---

## Решенные проблемы

### ❌ Проблема: Duplicate key error
```
ERROR: duplicate key value violates unique constraint "idx_cars_source_car_id"
Key (source, car_id)=(, 0) already exists.
```

### ✅ Решение:
1. Изменен индекс на частичный:
   ```sql
   CREATE UNIQUE INDEX idx_cars_source_car_id ON cars(source, car_id) 
   WHERE source != '' AND car_id != 0;
   ```

2. `UpdateCar` использует `.Updates()` - не обновляет `source` и `car_id`

3. Удален `car_postgres.go` - везде GORM

---

## Итог

✅ **Да, в БД все нормально заносится!**

- Миграции работают
- GORM корректно обрабатывает все поля
- Индексы не конфликтуют
- Воркер автоматически обогащает данные
- Галерея изображений парсится и сохраняется через пробел

**Просто запустите `docker compose up` и система сама заполнит БД!** 🎉

