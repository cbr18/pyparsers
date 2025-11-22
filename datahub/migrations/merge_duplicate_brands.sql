-- Скрипт для объединения дублирующихся брендов
-- Объединяет все алиасы из дубликатов в одну запись

-- Сначала объединяем все алиасы для каждого уникального бренда
WITH merged_aliases AS (
    SELECT 
        name,
        orig_name,
        string_agg(DISTINCT COALESCE(aliases, ''), ',' ORDER BY COALESCE(aliases, '')) FILTER (WHERE aliases IS NOT NULL AND aliases != '') as all_aliases
    FROM brands
    WHERE deleted_at IS NULL
    GROUP BY name, orig_name
    HAVING COUNT(*) > 1
),
-- Находим минимальный ID для каждого дублирующегося бренда (оставляем его)
first_ids AS (
    SELECT 
        b.id,
        b.name,
        b.orig_name,
        ROW_NUMBER() OVER (PARTITION BY b.name, b.orig_name ORDER BY b.created_at) as rn
    FROM brands b
    WHERE deleted_at IS NULL
      AND EXISTS (
          SELECT 1 FROM merged_aliases m 
          WHERE m.name = b.name AND m.orig_name = b.orig_name
      )
),
-- Обновляем первую запись, объединяя все алиасы
to_update AS (
    SELECT 
        fi.id,
        ma.all_aliases,
        -- Объединяем существующие алиасы с новыми (если есть)
        CASE 
            WHEN b.aliases IS NOT NULL AND b.aliases != '' THEN
                b.aliases || ',' || ma.all_aliases
            ELSE ma.all_aliases
        END as merged_aliases
    FROM first_ids fi
    JOIN brands b ON b.id = fi.id
    JOIN merged_aliases ma ON ma.name = fi.name AND ma.orig_name = fi.orig_name
    WHERE fi.rn = 1
)
-- Обновляем алиасы в первой записи
UPDATE brands
SET aliases = tu.merged_aliases,
    updated_at = NOW()
FROM to_update tu
WHERE brands.id = tu.id;

-- Удаляем дубликаты (оставляем только первую запись для каждой пары name/orig_name)
WITH first_ids AS (
    SELECT 
        id,
        ROW_NUMBER() OVER (PARTITION BY name, orig_name ORDER BY created_at) as rn
    FROM brands
    WHERE deleted_at IS NULL
      AND (name, orig_name) IN (
          SELECT name, orig_name 
          FROM brands 
          WHERE deleted_at IS NULL 
          GROUP BY name, orig_name 
          HAVING COUNT(*) > 1
      )
)
UPDATE brands
SET deleted_at = NOW(),
    updated_at = NOW()
FROM first_ids fi
WHERE brands.id = fi.id AND fi.rn > 1;

-- Проверка результата
SELECT 
    name, 
    orig_name, 
    COUNT(*) as count 
FROM brands 
WHERE deleted_at IS NULL 
GROUP BY name, orig_name 
HAVING COUNT(*) > 1 
ORDER BY count DESC;

