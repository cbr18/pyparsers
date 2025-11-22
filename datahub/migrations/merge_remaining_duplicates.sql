-- Объединение оставшихся дубликатов по name (независимо от orig_name)
-- Для брендов, где name одинаковый, но orig_name разный

WITH brand_groups AS (
    SELECT 
        name,
        -- Берем первый непустой orig_name или просто первый
        (array_agg(DISTINCT orig_name ORDER BY orig_name))[1] as primary_orig_name,
        -- Объединяем все orig_name
        string_agg(DISTINCT orig_name, ',' ORDER BY orig_name) as all_orig_names,
        -- Объединяем все алиасы
        string_agg(DISTINCT COALESCE(aliases, ''), ',' ORDER BY COALESCE(aliases, '')) 
            FILTER (WHERE aliases IS NOT NULL AND aliases != '') as all_aliases,
        min(created_at) as min_created_at
    FROM brands
    WHERE deleted_at IS NULL
    GROUP BY name
    HAVING COUNT(DISTINCT orig_name) > 1
),
first_ids AS (
    SELECT 
        b.id,
        bg.name,
        bg.primary_orig_name,
        bg.all_aliases,
        ROW_NUMBER() OVER (PARTITION BY bg.name ORDER BY b.created_at) as rn
    FROM brands b
    JOIN brand_groups bg ON bg.name = b.name
    WHERE b.deleted_at IS NULL
)
-- Обновляем первую запись, объединяя все данные
UPDATE brands
SET orig_name = fi.primary_orig_name,
    aliases = CASE 
        WHEN brands.aliases IS NOT NULL AND brands.aliases != '' AND fi.all_aliases IS NOT NULL THEN
            brands.aliases || ',' || fi.all_aliases
        WHEN fi.all_aliases IS NOT NULL THEN fi.all_aliases
        ELSE brands.aliases
    END,
    updated_at = NOW()
FROM first_ids fi
WHERE brands.id = fi.id AND fi.rn = 1;

-- Удаляем оставшиеся дубликаты (по name)
WITH first_ids AS (
    SELECT 
        id,
        ROW_NUMBER() OVER (PARTITION BY name ORDER BY created_at) as rn
    FROM brands
    WHERE deleted_at IS NULL
      AND name IN (
          SELECT name 
          FROM brands 
          WHERE deleted_at IS NULL 
          GROUP BY name 
          HAVING COUNT(DISTINCT orig_name) > 1
      )
)
UPDATE brands
SET deleted_at = NOW(),
    updated_at = NOW()
FROM first_ids fi
WHERE brands.id = fi.id AND fi.rn > 1;

-- Финальная проверка
SELECT 
    'Дубликаты по name' as check_type,
    COUNT(*) as duplicates
FROM (
    SELECT name 
    FROM brands 
    WHERE deleted_at IS NULL 
    GROUP BY name 
    HAVING COUNT(*) > 1
) dup;

