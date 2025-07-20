-- Обновление структуры таблицы cars

-- Сначала создаем временную таблицу с новой структурой
CREATE TABLE cars_new (
    uuid VARCHAR(36) PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    car_id VARCHAR(255),
    sku_id VARCHAR(255),
    title TEXT,
    car_name VARCHAR(255),
    year SMALLINT,
    mileage INTEGER,
    price VARCHAR(255),
    image TEXT,
    link TEXT,
    brand_name VARCHAR(255),
    series_name VARCHAR(255),
    city VARCHAR(255),
    shop_id VARCHAR(255),
    tags TEXT,
    is_available BOOLEAN DEFAULT TRUE,
    sort_number INTEGER DEFAULT 0,
    brand_id INTEGER,
    series_id INTEGER,
    car_source_city_name VARCHAR(255),
    tags_v2 TEXT,
    description TEXT,
    color VARCHAR(255),
    transmission VARCHAR(255),
    fuel_type VARCHAR(255),
    engine_volume VARCHAR(255),
    body_type VARCHAR(255),
    drive_type VARCHAR(255),
    condition VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Копируем данные из старой таблицы в новую
INSERT INTO cars_new (
    uuid, source, car_id, sku_id, title, car_name, year, mileage, price,
    image, link, brand_name, series_name, city, shop_id, tags,
    is_available, sort_number, created_at, updated_at
)
SELECT
    uuid, source, car_id, sku_id, title, car_name, year, mileage, price,
    image, link, brand_name, series_name, city, shop_id, tags,
    is_available, sort_number, created_at, updated_at
FROM cars;

-- Удаляем старую таблицу
DROP TABLE cars;

-- Переименовываем новую таблицу
ALTER TABLE cars_new RENAME TO cars;

-- Создаем индексы для оптимизации запросов
CREATE INDEX idx_cars_source ON cars(source);
CREATE INDEX idx_cars_brand_name ON cars(brand_name);
CREATE INDEX idx_cars_city ON cars(city);
CREATE INDEX idx_cars_year ON cars(year);
CREATE INDEX idx_cars_sort_number ON cars(sort_number);
CREATE INDEX idx_cars_created_at ON cars(created_at);
CREATE INDEX idx_cars_updated_at ON cars(updated_at);
