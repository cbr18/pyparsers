-- Проверка цен в базе данных

-- Посмотрим на примеры цен из базы
SELECT 
    uuid,
    car_id,
    source,
    brand_name,
    price,
    rub_price,
    created_at
FROM cars 
WHERE price IS NOT NULL AND price != ''
LIMIT 20;

-- Посмотрим статистику по rub_price
SELECT 
    source,
    COUNT(*) as total_cars,
    COUNT(CASE WHEN rub_price = 0 THEN 1 END) as zero_rub_price,
    COUNT(CASE WHEN rub_price > 0 THEN 1 END) as nonzero_rub_price,
    AVG(CASE WHEN rub_price > 0 THEN rub_price END) as avg_nonzero_rub_price
FROM cars
GROUP BY source;

-- Посмотрим на разные форматы цен
SELECT DISTINCT 
    LEFT(price, 20) as price_sample,
    COUNT(*) as count
FROM cars 
WHERE price IS NOT NULL AND price != ''
GROUP BY LEFT(price, 20)
ORDER BY count DESC
LIMIT 30;


