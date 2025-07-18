-- Изменение типа данных car_id с string на int64
-- Сначала создаем временную колонку для хранения значений int64
ALTER TABLE cars ADD COLUMN car_id_int BIGINT;

-- Копируем данные из car_id в car_id_int, преобразуя строки в числа
-- Используем NULLIF и CAST для безопасного преобразования
UPDATE cars SET car_id_int = CAST(NULLIF(car_id, '') AS BIGINT) WHERE car_id ~ '^[0-9]+$';

-- Удаляем старую колонку car_id
ALTER TABLE cars DROP COLUMN car_id;

-- Переименовываем car_id_int в car_id
ALTER TABLE cars RENAME COLUMN car_id_int TO car_id;

-- Обновляем индекс, который использует car_id
DROP INDEX IF EXISTS idx_cars_source_car_id;
CREATE UNIQUE INDEX idx_cars_source_car_id ON cars(source, car_id);
