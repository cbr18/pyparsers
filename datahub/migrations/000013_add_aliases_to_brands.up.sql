-- Добавление столбца aliases для хранения списка алиасов бренда
ALTER TABLE brands ADD COLUMN IF NOT EXISTS aliases TEXT;

