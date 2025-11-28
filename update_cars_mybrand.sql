-- =============================================================================
-- ОБНОВЛЕНИЕ ССЫЛОК НА БРЕНДЫ В ТАБЛИЦЕ CARS
-- =============================================================================

BEGIN;

-- Обновление mybrand_id на основе brand_name
UPDATE cars c
SET mybrand_id = b.id
FROM brands b
WHERE (
    LOWER(c.brand_name) = LOWER(b.name)
    OR LOWER(c.brand_name) = LOWER(b.orig_name)
    OR b.aliases ILIKE '%' || c.brand_name || '%'
);

COMMIT;

-- Проверка: машины без mybrand_id
SELECT brand_name, COUNT(*) as cnt
FROM cars
WHERE mybrand_id IS NULL AND brand_name IS NOT NULL AND brand_name != ''
GROUP BY brand_name
ORDER BY cnt DESC
LIMIT 50;
