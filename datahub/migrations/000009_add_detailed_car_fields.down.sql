-- Удаление полей для детальной информации о машинах
-- Удаление индексов
DROP INDEX IF EXISTS idx_cars_favorite_count;
DROP INDEX IF EXISTS idx_cars_view_count;
DROP INDEX IF EXISTS idx_cars_owner_count;
DROP INDEX IF EXISTS idx_cars_has_details;

-- Удаление дополнительных характеристик
ALTER TABLE cars DROP COLUMN IF EXISTS fuel_tank_volume;
ALTER TABLE cars DROP COLUMN IF EXISTS trunk_volume;
ALTER TABLE cars DROP COLUMN IF EXISTS door_count;
ALTER TABLE cars DROP COLUMN IF EXISTS seat_count;

-- Удаление карусели изображений
ALTER TABLE cars DROP COLUMN IF EXISTS image_count;
ALTER TABLE cars DROP COLUMN IF EXISTS image_gallery;

-- Удаление дополнительных метаданных
ALTER TABLE cars DROP COLUMN IF EXISTS certification;
ALTER TABLE cars DROP COLUMN IF EXISTS dealer_info;
ALTER TABLE cars DROP COLUMN IF EXISTS contact_info;
ALTER TABLE cars DROP COLUMN IF EXISTS favorite_count;
ALTER TABLE cars DROP COLUMN IF EXISTS view_count;

-- Удаление дополнительных деталей
ALTER TABLE cars DROP COLUMN IF EXISTS panoramic_roof;
ALTER TABLE cars DROP COLUMN IF EXISTS sunroof;
ALTER TABLE cars DROP COLUMN IF EXISTS upholstery;
ALTER TABLE cars DROP COLUMN IF EXISTS exterior_color;
ALTER TABLE cars DROP COLUMN IF EXISTS interior_color;

-- Удаление истории и состояния
ALTER TABLE cars DROP COLUMN IF EXISTS insurance_info;
ALTER TABLE cars DROP COLUMN IF EXISTS inspection_date;
ALTER TABLE cars DROP COLUMN IF EXISTS warranty_info;
ALTER TABLE cars DROP COLUMN IF EXISTS service_history;
ALTER TABLE cars DROP COLUMN IF EXISTS accident_history;
ALTER TABLE cars DROP COLUMN IF EXISTS owner_count;

-- Удаление освещения
ALTER TABLE cars DROP COLUMN IF EXISTS daytime_running;
ALTER TABLE cars DROP COLUMN IF EXISTS led_lights;
ALTER TABLE cars DROP COLUMN IF EXISTS fog_lights;
ALTER TABLE cars DROP COLUMN IF EXISTS headlight_type;

-- Удаление мультимедиа и навигации
ALTER TABLE cars DROP COLUMN IF EXISTS aux;
ALTER TABLE cars DROP COLUMN IF EXISTS usb;
ALTER TABLE cars DROP COLUMN IF EXISTS bluetooth;
ALTER TABLE cars DROP COLUMN IF EXISTS speakers_count;
ALTER TABLE cars DROP COLUMN IF EXISTS audio_system;
ALTER TABLE cars DROP COLUMN IF EXISTS navigation;

-- Удаление комфорта и удобства
ALTER TABLE cars DROP COLUMN IF EXISTS steering_wheel_heating;
ALTER TABLE cars DROP COLUMN IF EXISTS seat_massage;
ALTER TABLE cars DROP COLUMN IF EXISTS seat_ventilation;
ALTER TABLE cars DROP COLUMN IF EXISTS seat_heating;
ALTER TABLE cars DROP COLUMN IF EXISTS climate_control;
ALTER TABLE cars DROP COLUMN IF EXISTS air_conditioning;

-- Удаление безопасности
ALTER TABLE cars DROP COLUMN IF EXISTS lane_departure;
ALTER TABLE cars DROP COLUMN IF EXISTS blind_spot_monitor;
ALTER TABLE cars DROP COLUMN IF EXISTS hill_assist;
ALTER TABLE cars DROP COLUMN IF EXISTS tcs;
ALTER TABLE cars DROP COLUMN IF EXISTS esp;
ALTER TABLE cars DROP COLUMN IF EXISTS abs;
ALTER TABLE cars DROP COLUMN IF EXISTS airbag_count;

-- Удаление колес и шин
ALTER TABLE cars DROP COLUMN IF EXISTS tire_type;
ALTER TABLE cars DROP COLUMN IF EXISTS wheel_type;
ALTER TABLE cars DROP COLUMN IF EXISTS tire_size;
ALTER TABLE cars DROP COLUMN IF EXISTS wheel_size;

-- Удаление подвески и тормозов
ALTER TABLE cars DROP COLUMN IF EXISTS brake_system;
ALTER TABLE cars DROP COLUMN IF EXISTS rear_brakes;
ALTER TABLE cars DROP COLUMN IF EXISTS front_brakes;
ALTER TABLE cars DROP COLUMN IF EXISTS rear_suspension;
ALTER TABLE cars DROP COLUMN IF EXISTS front_suspension;

-- Удаление трансмиссии и привода
ALTER TABLE cars DROP COLUMN IF EXISTS differential_type;
ALTER TABLE cars DROP COLUMN IF EXISTS gear_count;
ALTER TABLE cars DROP COLUMN IF EXISTS transmission_type;

-- Удаление электрических характеристик
ALTER TABLE cars DROP COLUMN IF EXISTS charge_port_type;
ALTER TABLE cars DROP COLUMN IF EXISTS fast_charge_time;
ALTER TABLE cars DROP COLUMN IF EXISTS charging_time;
ALTER TABLE cars DROP COLUMN IF EXISTS electric_range;
ALTER TABLE cars DROP COLUMN IF EXISTS battery_capacity;

-- Удаление двигателя и трансмиссии
ALTER TABLE cars DROP COLUMN IF EXISTS turbo_type;
ALTER TABLE cars DROP COLUMN IF EXISTS compression_ratio;
ALTER TABLE cars DROP COLUMN IF EXISTS valve_count;
ALTER TABLE cars DROP COLUMN IF EXISTS cylinder_count;
ALTER TABLE cars DROP COLUMN IF EXISTS engine_code;
ALTER TABLE cars DROP COLUMN IF EXISTS engine_type;

-- Удаление размеров и веса
ALTER TABLE cars DROP COLUMN IF EXISTS gross_weight;
ALTER TABLE cars DROP COLUMN IF EXISTS curb_weight;
ALTER TABLE cars DROP COLUMN IF EXISTS wheelbase;
ALTER TABLE cars DROP COLUMN IF EXISTS height;
ALTER TABLE cars DROP COLUMN IF EXISTS width;
ALTER TABLE cars DROP COLUMN IF EXISTS length;

-- Удаление дополнительных технических характеристик
ALTER TABLE cars DROP COLUMN IF EXISTS emission_standard;
ALTER TABLE cars DROP COLUMN IF EXISTS fuel_consumption;
ALTER TABLE cars DROP COLUMN IF EXISTS max_speed;
ALTER TABLE cars DROP COLUMN IF EXISTS acceleration;
ALTER TABLE cars DROP COLUMN IF EXISTS torque;
ALTER TABLE cars DROP COLUMN IF EXISTS power;

-- Удаление флагов и метаданных
ALTER TABLE cars DROP COLUMN IF EXISTS last_detail_update;
ALTER TABLE cars DROP COLUMN IF EXISTS has_details;

