-- Добавляем поля для стоимости утилизационного и таможенного сборов
ALTER TABLE cars
    ADD COLUMN IF NOT EXISTS recycling_fee VARCHAR(31),
    ADD COLUMN IF NOT EXISTS customs_duty VARCHAR(31);

