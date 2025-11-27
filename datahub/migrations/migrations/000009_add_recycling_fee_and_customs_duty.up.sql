-- Добавление столбцов для утильсбора и таможенного сбора в таблицу cars
ALTER TABLE cars ADD COLUMN IF NOT EXISTS recycling_fee VARCHAR(255);
ALTER TABLE cars ADD COLUMN IF NOT EXISTS customs_duty VARCHAR(255);



