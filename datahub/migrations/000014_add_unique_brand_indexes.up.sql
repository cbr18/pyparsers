-- Добавление уникальных индексов на таблицу brands для предотвращения дублирования
-- Индексы case-insensitive и учитывают только не удаленные записи

-- Уникальный индекс по name (case-insensitive)
CREATE UNIQUE INDEX IF NOT EXISTS idx_brands_name_unique_lower 
ON brands (LOWER(name)) 
WHERE deleted_at IS NULL;

-- Уникальный индекс по orig_name (case-insensitive)
CREATE UNIQUE INDEX IF NOT EXISTS idx_brands_orig_name_unique_lower 
ON brands (LOWER(orig_name)) 
WHERE deleted_at IS NULL;

-- Комментарий для документации
COMMENT ON INDEX idx_brands_name_unique_lower IS 'Предотвращает дублирование брендов по английскому названию (case-insensitive)';
COMMENT ON INDEX idx_brands_orig_name_unique_lower IS 'Предотвращает дублирование брендов по китайскому названию (case-insensitive)';

