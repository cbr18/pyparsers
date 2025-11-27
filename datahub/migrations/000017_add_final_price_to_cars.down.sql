-- Откатываем добавление финальной цены
DROP INDEX IF EXISTS idx_cars_final_price;

ALTER TABLE cars
    DROP COLUMN IF EXISTS final_price;

