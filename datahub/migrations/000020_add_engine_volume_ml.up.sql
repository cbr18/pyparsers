-- Добавление поля для объема двигателя в миллилитрах
ALTER TABLE cars ADD COLUMN IF NOT EXISTS engine_volume_ml VARCHAR(255);



