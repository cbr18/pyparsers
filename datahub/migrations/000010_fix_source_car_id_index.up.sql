-- Удаляем старый уникальный индекс
DROP INDEX IF EXISTS idx_cars_source_car_id;

-- Создаем частичный уникальный индекс (только для строк где source не пустой и car_id != 0)
-- Это позволит избежать конфликтов при обновлении машин
CREATE UNIQUE INDEX idx_cars_source_car_id ON cars(source, car_id) 
WHERE source != '' AND car_id != 0;

-- Также создаем индекс на UUID для быстрого поиска при обновлении
CREATE INDEX IF NOT EXISTS idx_cars_uuid ON cars(uuid);

