-- Добавляем частичный индекс на has_details
-- Частичный индекс (WHERE has_details = true) занимает меньше места
-- и используется только для запросов с has_details=true

CREATE INDEX IF NOT EXISTS idx_cars_has_details 
ON cars(has_details) 
WHERE has_details = true;

-- Композитный индекс для частого запроса: has_details + source
CREATE INDEX IF NOT EXISTS idx_cars_has_details_source 
ON cars(has_details, source) 
WHERE has_details = true;

-- Композитный индекс для фильтрации: has_details + is_available
CREATE INDEX IF NOT EXISTS idx_cars_has_details_available 
ON cars(has_details, is_available) 
WHERE has_details = true AND is_available = true;


