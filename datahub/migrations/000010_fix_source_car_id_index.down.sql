-- Удаляем индекс на UUID
DROP INDEX IF EXISTS idx_cars_uuid;

-- Возвращаем старый индекс
DROP INDEX IF EXISTS idx_cars_source_car_id;
CREATE UNIQUE INDEX idx_cars_source_car_id ON cars(source, car_id);

