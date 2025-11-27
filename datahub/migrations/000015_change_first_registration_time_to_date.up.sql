-- Преобразуем first_registration_time в тип DATE
ALTER TABLE cars
    ALTER COLUMN first_registration_time TYPE DATE
    USING (
        CASE
            WHEN first_registration_time ~ '^\d{4}-\d{2}-\d{2}$' THEN first_registration_time::date
            WHEN first_registration_time ~ '^\d{4}-\d{2}$' THEN (first_registration_time || '-01')::date
            WHEN first_registration_time ~ '^\d{4}$' THEN (first_registration_time || '-01-01')::date
            ELSE NULL
        END
    );

