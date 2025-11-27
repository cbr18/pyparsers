-- Удаляем поле таможенного сбора
ALTER TABLE cars
    DROP COLUMN IF EXISTS customs_fee;



