-- Добавляем столбец final_price для хранения финальной цены в рублях
ALTER TABLE cars
    ADD COLUMN IF NOT EXISTS final_price DOUBLE PRECISION DEFAULT 0;

-- Инициализируем финальную цену текущим значением rub_price, чтобы не потерять данные
UPDATE cars
SET final_price = rub_price
WHERE final_price IS NULL OR final_price = 0;

-- Индекс для ускорения фильтрации и сортировки по финальной цене
CREATE INDEX IF NOT EXISTS idx_cars_final_price ON cars(final_price);

