-- Удаляем поле даты первой регистрации при откате
ALTER TABLE cars
    DROP COLUMN IF EXISTS first_registration_time;

