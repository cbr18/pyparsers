-- Добавляем поле для типа силовой установки
-- Значения: ice (ДВС), electric (электро), hybrid (гибрид), phev (плагин-гибрид), unknown (не определён)
ALTER TABLE cars ADD COLUMN IF NOT EXISTS powertrain_type VARCHAR(20) DEFAULT 'unknown';

-- Индекс для фильтрации по типу
CREATE INDEX IF NOT EXISTS idx_cars_powertrain_type ON cars(powertrain_type);


