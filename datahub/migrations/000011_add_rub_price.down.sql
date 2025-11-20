-- Удаление индекса
DROP INDEX IF EXISTS idx_cars_rub_price;

-- Удаление столбца rub_price
ALTER TABLE cars DROP COLUMN IF EXISTS rub_price;



