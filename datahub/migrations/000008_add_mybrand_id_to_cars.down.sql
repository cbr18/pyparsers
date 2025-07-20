-- Удаление внешнего ключа
ALTER TABLE cars DROP CONSTRAINT IF EXISTS fk_cars_mybrand_id;

-- Удаление индекса
DROP INDEX IF EXISTS idx_cars_mybrand_id;

-- Удаление столбца mybrand_id
ALTER TABLE cars DROP COLUMN IF EXISTS mybrand_id;
