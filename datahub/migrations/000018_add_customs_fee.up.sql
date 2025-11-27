-- Добавляем поле для таможенного сбора (рассчитывается по rub_price)
ALTER TABLE cars
    ADD COLUMN IF NOT EXISTS customs_fee DOUBLE PRECISION DEFAULT 0;



