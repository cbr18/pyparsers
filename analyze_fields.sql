-- Анализ размеров полей VARCHAR(255) в таблице cars

-- Функция для анализа одного поля
\echo '=== Анализ полей таблицы cars ==='

-- Список полей для анализа
\echo ''
\echo 'Поле: source'
SELECT 
    COUNT(*) as total,
    COUNT(source) as non_null,
    MAX(LENGTH(COALESCE(source, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(source, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(source, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(source, ''))) as p99
FROM cars WHERE source IS NOT NULL;

\echo ''
\echo 'Поле: sku_id'
SELECT 
    COUNT(*) as total,
    COUNT(sku_id) as non_null,
    MAX(LENGTH(COALESCE(sku_id, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(sku_id, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(sku_id, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(sku_id, ''))) as p99
FROM cars WHERE sku_id IS NOT NULL;

\echo ''
\echo 'Поле: car_name'
SELECT 
    COUNT(*) as total,
    COUNT(car_name) as non_null,
    MAX(LENGTH(COALESCE(car_name, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(car_name, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(car_name, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(car_name, ''))) as p99
FROM cars WHERE car_name IS NOT NULL;

\echo ''
\echo 'Поле: brand_name'
SELECT 
    COUNT(*) as total,
    COUNT(brand_name) as non_null,
    MAX(LENGTH(COALESCE(brand_name, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(brand_name, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(brand_name, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(brand_name, ''))) as p99
FROM cars WHERE brand_name IS NOT NULL;

\echo ''
\echo 'Поле: series_name'
SELECT 
    COUNT(*) as total,
    COUNT(series_name) as non_null,
    MAX(LENGTH(COALESCE(series_name, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(series_name, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(series_name, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(series_name, ''))) as p99
FROM cars WHERE series_name IS NOT NULL;

\echo ''
\echo 'Поле: city'
SELECT 
    COUNT(*) as total,
    COUNT(city) as non_null,
    MAX(LENGTH(COALESCE(city, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(city, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(city, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(city, ''))) as p99
FROM cars WHERE city IS NOT NULL;

\echo ''
\echo 'Поле: car_source_city_name'
SELECT 
    COUNT(*) as total,
    COUNT(car_source_city_name) as non_null,
    MAX(LENGTH(COALESCE(car_source_city_name, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(car_source_city_name, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(car_source_city_name, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(car_source_city_name, ''))) as p99
FROM cars WHERE car_source_city_name IS NOT NULL;

\echo ''
\echo 'Поле: shop_id'
SELECT 
    COUNT(*) as total,
    COUNT(shop_id) as non_null,
    MAX(LENGTH(COALESCE(shop_id, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(shop_id, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(shop_id, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(shop_id, ''))) as p99
FROM cars WHERE shop_id IS NOT NULL;

\echo ''
\echo 'Поле: price'
SELECT 
    COUNT(*) as total,
    COUNT(price) as non_null,
    MAX(LENGTH(COALESCE(price, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(price, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(price, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(price, ''))) as p99
FROM cars WHERE price IS NOT NULL;

\echo ''
\echo 'Поле: color'
SELECT 
    COUNT(*) as total,
    COUNT(color) as non_null,
    MAX(LENGTH(COALESCE(color, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(color, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(color, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(color, ''))) as p99
FROM cars WHERE color IS NOT NULL;

\echo ''
\echo 'Поле: transmission'
SELECT 
    COUNT(*) as total,
    COUNT(transmission) as non_null,
    MAX(LENGTH(COALESCE(transmission, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(transmission, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(transmission, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(transmission, ''))) as p99
FROM cars WHERE transmission IS NOT NULL;

\echo ''
\echo 'Поле: fuel_type'
SELECT 
    COUNT(*) as total,
    COUNT(fuel_type) as non_null,
    MAX(LENGTH(COALESCE(fuel_type, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(fuel_type, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(fuel_type, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(fuel_type, ''))) as p99
FROM cars WHERE fuel_type IS NOT NULL;

\echo ''
\echo 'Поле: engine_volume'
SELECT 
    COUNT(*) as total,
    COUNT(engine_volume) as non_null,
    MAX(LENGTH(COALESCE(engine_volume, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(engine_volume, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(engine_volume, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(engine_volume, ''))) as p99
FROM cars WHERE engine_volume IS NOT NULL;

\echo ''
\echo 'Поле: body_type'
SELECT 
    COUNT(*) as total,
    COUNT(body_type) as non_null,
    MAX(LENGTH(COALESCE(body_type, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(body_type, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(body_type, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(body_type, ''))) as p99
FROM cars WHERE body_type IS NOT NULL;

\echo ''
\echo 'Поле: drive_type'
SELECT 
    COUNT(*) as total,
    COUNT(drive_type) as non_null,
    MAX(LENGTH(COALESCE(drive_type, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(drive_type, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(drive_type, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(drive_type, ''))) as p99
FROM cars WHERE drive_type IS NOT NULL;

\echo ''
\echo 'Поле: condition'
SELECT 
    COUNT(*) as total,
    COUNT(condition) as non_null,
    MAX(LENGTH(COALESCE(condition, ''))) as max_len,
    ROUND(AVG(LENGTH(COALESCE(condition, '')))) as avg_len,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY LENGTH(COALESCE(condition, ''))) as p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY LENGTH(COALESCE(condition, ''))) as p99
FROM cars WHERE condition IS NOT NULL;



