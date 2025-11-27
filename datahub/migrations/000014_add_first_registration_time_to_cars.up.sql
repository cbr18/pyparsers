-- Добавляем поле для даты первой регистрации автомобиля
ALTER TABLE cars
    ADD COLUMN IF NOT EXISTS first_registration_time VARCHAR(255);

