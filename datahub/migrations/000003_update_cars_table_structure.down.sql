-- Откат изменений структуры таблицы cars

-- Создаем временную таблицу со старой структурой
CREATE TABLE cars_old (
    id SERIAL PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE,
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Копируем данные из новой таблицы в старую
INSERT INTO cars_old (
    uuid, source, car_id, sku_id, title, car_name, year, mileage, price,
    image, link, brand_name, series_name, city, shop_id, tags,
    is_available, sort_number, created_at, updated_at
)
SELECT
    uuid, source, car_id, sku_id, title, car_name, year, mileage, price,
    image, link, brand_name, series_name, city, shop_id, tags,
    is_available, sort_number, created_at, updated_at
FROM cars;

-- Удаляем новую таблицу
DROP TABLE cars;

-- Переименовываем старую таблицу
ALTER TABLE cars_old RENAME TO cars;

-- Создаем индексы для оптимизации запросов
CREATE INDEX idx_cars_source ON cars(source);
CREATE INDEX idx_cars_brand_name ON cars(brand_name);
CREATE INDEX idx_cars_city ON cars(city);
CREATE INDEX idx_cars_year ON cars(year);
CREATE INDEX idx_cars_sort_number ON cars(sort_number);
CREATE INDEX idx_cars_created_at ON cars(created_at);
CREATE INDEX idx_cars_updated_at ON cars(updated_at);
