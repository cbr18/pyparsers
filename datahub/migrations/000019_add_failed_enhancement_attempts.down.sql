-- Удаление поля для счетчика неудачных попыток улучшения
DROP INDEX IF EXISTS idx_cars_failed_enhancement_attempts;
ALTER TABLE cars DROP COLUMN IF EXISTS failed_enhancement_attempts;

