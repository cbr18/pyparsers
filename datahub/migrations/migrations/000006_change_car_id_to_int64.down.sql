-- Откат изменения типа данных car_id с int64 на string
-- Сначала создаем временную колонку для хранения значений string
ALTER TABLE cars ADD COLUMN car_id_str VARCHAR(255);

-- Копируем данные из car_id в car_id_str, преобразуя числа в строки
UPDATE cars SET car_id_str = CAST(car_id AS VARCHAR);

-- Удаляем старую колонку car_id
ALTER TABLE cars DROP COLUMN car_id;

-- Переименовываем car_id_str в car_id
ALTER TABLE cars RENAME COLUMN car_id_str TO car_id;

-- Обновляем индекс, который использует car_id
DROP INDEX IF EXISTS idx_cars_source_car_id;
CREATE UNIQUE INDEX idx_cars_source_car_id ON cars(source, car_id);
