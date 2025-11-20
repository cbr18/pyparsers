-- Добавление столбца rub_price для хранения цены в рублях
ALTER TABLE cars ADD COLUMN IF NOT EXISTS rub_price DOUBLE PRECISION DEFAULT 0;

-- Создание индекса для быстрого поиска по цене в рублях
CREATE INDEX IF NOT EXISTS idx_cars_rub_price ON cars(rub_price);



