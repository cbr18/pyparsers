-- Пример SQL скрипта для заполнения поля aliases в таблице brands
-- Включает примеры как для INSERT (новые записи), так и для UPDATE (существующие)

-- ============================================
-- ВАРИАНТ 1: INSERT - создание новых брендов с алиасами
-- ============================================

-- Пример создания новых брендов с алиасами
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES 
    ('BMW', '宝马', 'BMW,巴伐利亚,巴伐利亚发动机制造厂', NOW(), NOW()),
    ('Mercedes-Benz', '奔驰', 'Mercedes-Benz,Mercedes,MB,梅赛德斯,梅赛德斯-奔驰', NOW(), NOW()),
    ('Audi', '奥迪', 'Audi,奥迪', NOW(), NOW()),
    ('Volkswagen', '大众', 'Volkswagen,VW,大众', NOW(), NOW()),
    ('Toyota', '丰田', 'Toyota,丰田', NOW(), NOW()),
    ('Honda', '本田', 'Honda,本田', NOW(), NOW())
ON CONFLICT DO NOTHING;  -- Пропускаем, если бренд уже существует

-- Или с проверкой существования:
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
SELECT 'BMW', '宝马', 'BMW,巴伐利亚,巴伐利亚发动机制造厂', NOW(), NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM brands 
    WHERE name = 'BMW' OR orig_name = '宝马'
);

-- ============================================
-- ВАРИАНТ 2: UPDATE - обновление существующих брендов
-- ============================================

-- Обновление одного бренда
UPDATE brands 
SET aliases = 'BMW,巴伐利亚,巴伐利亚发动机制造厂',
    updated_at = NOW()
WHERE (name = 'BMW' OR orig_name = '宝马')
  AND deleted_at IS NULL;

-- Обновление нескольких брендов
UPDATE brands 
SET aliases = 'Mercedes-Benz,Mercedes,MB,梅赛德斯,梅赛德斯-奔驰',
    updated_at = NOW()
WHERE (name = 'Mercedes-Benz' OR orig_name = '奔驰')
  AND deleted_at IS NULL;

UPDATE brands 
SET aliases = 'Audi,奥迪',
    updated_at = NOW()
WHERE (name = 'Audi' OR orig_name = '奥迪')
  AND deleted_at IS NULL;

-- Массовое обновление через CASE
UPDATE brands 
SET aliases = CASE 
    WHEN name = 'BMW' OR orig_name = '宝马' THEN 'BMW,巴伐利亚,巴伐利亚发动机制造厂'
    WHEN name = 'Mercedes-Benz' OR orig_name = '奔驰' THEN 'Mercedes-Benz,Mercedes,MB,梅赛德斯,梅赛德斯-奔驰'
    WHEN name = 'Audi' OR orig_name = '奥迪' THEN 'Audi,奥迪'
    WHEN name = 'Volkswagen' OR orig_name = '大众' THEN 'Volkswagen,VW,大众'
    WHEN name = 'Toyota' OR orig_name = '丰田' THEN 'Toyota,丰田'
    WHEN name = 'Honda' OR orig_name = '本田' THEN 'Honda,本田'
    ELSE aliases
END,
updated_at = NOW()
WHERE (name IN ('BMW', 'Mercedes-Benz', 'Audi', 'Volkswagen', 'Toyota', 'Honda')
   OR orig_name IN ('宝马', '奔驰', '奥迪', '大众', '丰田', '本田'))
  AND deleted_at IS NULL;

-- ============================================
-- ВАРИАНТ 3: INSERT ... ON CONFLICT UPDATE (UPSERT)
-- ============================================

-- Создание или обновление бренда с алиасами
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('BMW', '宝马', 'BMW,巴伐利亚,巴伐利亚发动机制造厂', NOW(), NOW())
ON CONFLICT (id) DO UPDATE
SET aliases = EXCLUDED.aliases,
    updated_at = NOW();

-- Или более сложный вариант с поиском по name/orig_name:
-- (требует уникального индекса на name или orig_name)
INSERT INTO brands (name, orig_name, aliases, created_at, updated_at)
VALUES ('BMW', '宝马', 'BMW,巴伐利亚,巴伐利亚发动机制造厂', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- ВАРИАНТ 4: Добавление алиасов к существующим (если поле уже заполнено)
-- ============================================

-- Добавление нового алиаса к существующим (если его еще нет)
UPDATE brands 
SET aliases = CASE 
    WHEN aliases IS NULL OR aliases = '' THEN 'новый_алиас'
    WHEN aliases NOT LIKE '%новый_алиас%' THEN aliases || ',новый_алиас'
    ELSE aliases
END,
updated_at = NOW()
WHERE (name = 'BMW' OR orig_name = '宝马')
  AND deleted_at IS NULL;

-- ============================================
-- ПРОВЕРКА: Просмотр текущих данных
-- ============================================

-- Просмотр всех брендов с алиасами
SELECT id, name, orig_name, aliases, created_at, updated_at
FROM brands 
WHERE deleted_at IS NULL
ORDER BY COALESCE(name, orig_name);

-- Просмотр брендов без алиасов (для заполнения)
SELECT id, name, orig_name, aliases
FROM brands 
WHERE deleted_at IS NULL
  AND (aliases IS NULL OR aliases = '')
ORDER BY COALESCE(name, orig_name);

-- Проверка поиска по алиасам
SELECT id, name, orig_name, aliases
FROM brands 
WHERE deleted_at IS NULL
  AND (name = 'BMW' OR orig_name = 'BMW' OR aliases ILIKE '%BMW%');


