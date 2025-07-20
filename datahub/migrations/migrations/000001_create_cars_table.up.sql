CREATE TABLE IF NOT EXISTS cars (
    id BIGSERIAL PRIMARY KEY,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    source VARCHAR(255) NOT NULL,
    car_id VARCHAR(255) NOT NULL,
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
    is_available BOOLEAN DEFAULT true,
    sort_number INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cars_brand_name ON cars(brand_name);
CREATE INDEX idx_cars_city ON cars(city);
CREATE INDEX idx_cars_year ON cars(year);
CREATE INDEX idx_cars_source ON cars(source);
CREATE INDEX idx_cars_is_available ON cars(is_available);
