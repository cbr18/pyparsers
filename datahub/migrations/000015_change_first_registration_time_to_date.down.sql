-- Возвращаем тип VARCHAR для first_registration_time
ALTER TABLE cars
    ALTER COLUMN first_registration_time TYPE VARCHAR(255)
    USING (
        CASE
            WHEN first_registration_time IS NULL THEN NULL
            ELSE to_char(first_registration_time, 'YYYY-MM-DD')
        END
    );

