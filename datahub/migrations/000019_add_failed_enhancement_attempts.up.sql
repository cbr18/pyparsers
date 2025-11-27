-- Добавление поля для счетчика неудачных попыток улучшения
ALTER TABLE cars ADD COLUMN IF NOT EXISTS failed_enhancement_attempts INTEGER DEFAULT 0;

-- Создаем индекс для оптимизации запросов по машинам с неудачными попытками
CREATE INDEX IF NOT EXISTS idx_cars_failed_enhancement_attempts ON cars(failed_enhancement_attempts) WHERE failed_enhancement_attempts > 0;

