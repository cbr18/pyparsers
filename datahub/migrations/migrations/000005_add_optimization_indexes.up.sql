-- Создаем составной индекс для часто используемых полей в фильтрах
CREATE INDEX IF NOT EXISTS idx_cars_filter_common ON cars(source, brand_name, city, year, is_available);

-- Создаем индекс для полнотекстового поиска по названию и описанию
CREATE INDEX IF NOT EXISTS idx_cars_title_description ON cars USING gin(to_tsvector('russian', title || ' ' || COALESCE(description, '')));

-- Создаем индекс для сортировки по дате создания и номеру сортировки
CREATE INDEX IF NOT EXISTS idx_cars_sort_created ON cars(sort_number DESC, created_at DESC);

-- Создаем уникальный индекс для комбинации source и car_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_cars_source_car_id ON cars(source, car_id);
