-- Удаление столбцов для утильсбора и таможенного сбора из таблицы cars
ALTER TABLE cars DROP COLUMN IF EXISTS recycling_fee;
ALTER TABLE cars DROP COLUMN IF EXISTS customs_duty;



