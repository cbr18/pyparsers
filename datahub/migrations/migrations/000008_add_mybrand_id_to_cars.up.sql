-- Добавление столбца mybrand_id в таблицу cars
ALTER TABLE cars ADD COLUMN IF NOT EXISTS mybrand_id UUID;

-- Создание индекса для mybrand_id
CREATE INDEX IF NOT EXISTS idx_cars_mybrand_id ON cars(mybrand_id);

-- Добавление внешнего ключа
ALTER TABLE cars ADD CONSTRAINT fk_cars_mybrand_id FOREIGN KEY (mybrand_id) REFERENCES brands(id) ON DELETE SET NULL;
