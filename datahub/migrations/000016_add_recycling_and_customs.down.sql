-- Удаляем дополнительные поля стоимости утилизации и таможенного сбора
ALTER TABLE cars
    DROP COLUMN IF EXISTS recycling_fee,
    DROP COLUMN IF EXISTS customs_duty;

