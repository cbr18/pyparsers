from pydantic import BaseModel
from typing import Optional

class DongchediCar(BaseModel):
    uuid: Optional[str] = None
    title: Optional[str] = None
    sh_price: Optional[str] = None
    price: Optional[str] = None
    image: Optional[str] = None
    link: Optional[str] = None
    car_name: Optional[str] = None
    car_year: Optional[int] = None
    year: Optional[int] = None
    car_mileage: Optional[str] = None
    mileage: Optional[int] = None
    car_source_city_name: Optional[str] = None
    brand_name: Optional[str] = None
    series_name: Optional[str] = None
    brand_id: Optional[int] = None
    series_id: Optional[int] = None
    shop_id: Optional[str] = None
    car_id: Optional[str] = None  # Changed from int to str to match Go struct
    tags_v2: Optional[str] = None
    tags: Optional[str] = None
    sku_id: Optional[str] = None  # Changed from int to str to match Go struct
    source: Optional[str] = "dongchedi"
    city: Optional[str] = None
    is_available: Optional[bool] = True
    sort_number: Optional[int] = 0
    description: Optional[str] = None
    color: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    engine_volume: Optional[str] = None
    engine_volume_ml: Optional[str] = None  # Объем двигателя в миллилитрах
    body_type: Optional[str] = None
    drive_type: Optional[str] = None
    condition: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # Флаги и метаданные
    has_details: Optional[bool] = False
    last_detail_update: Optional[str] = None

    # Дополнительные технические характеристики
    power: Optional[str] = None
    torque: Optional[str] = None
    acceleration: Optional[str] = None
    max_speed: Optional[str] = None
    fuel_consumption: Optional[str] = None
    emission_standard: Optional[str] = None

    # Размеры и вес
    length: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    wheelbase: Optional[str] = None
    curb_weight: Optional[str] = None
    gross_weight: Optional[str] = None

    # Двигатель и трансмиссия (для ДВС)
    engine_type: Optional[str] = None
    engine_code: Optional[str] = None
    cylinder_count: Optional[str] = None
    valve_count: Optional[str] = None
    compression_ratio: Optional[str] = None
    turbo_type: Optional[str] = None

    # Электрические характеристики (для электромобилей)
    battery_capacity: Optional[str] = None
    electric_range: Optional[str] = None
    charging_time: Optional[str] = None
    fast_charge_time: Optional[str] = None
    charge_port_type: Optional[str] = None

    # Трансмиссия и привод
    transmission_type: Optional[str] = None
    gear_count: Optional[str] = None
    differential_type: Optional[str] = None

    # Подвеска и тормоза
    front_suspension: Optional[str] = None
    rear_suspension: Optional[str] = None
    front_brakes: Optional[str] = None
    rear_brakes: Optional[str] = None
    brake_system: Optional[str] = None

    # Колеса и шины
    wheel_size: Optional[str] = None
    tire_size: Optional[str] = None
    wheel_type: Optional[str] = None
    tire_type: Optional[str] = None

    # Безопасность
    airbag_count: Optional[str] = None
    abs: Optional[str] = None
    esp: Optional[str] = None
    tcs: Optional[str] = None
    hill_assist: Optional[str] = None
    blind_spot_monitor: Optional[str] = None
    lane_departure: Optional[str] = None

    # Комфорт и удобство
    air_conditioning: Optional[str] = None
    climate_control: Optional[str] = None
    seat_heating: Optional[str] = None
    seat_ventilation: Optional[str] = None
    seat_massage: Optional[str] = None
    steering_wheel_heating: Optional[str] = None

    # Мультимедиа и навигация
    navigation: Optional[str] = None
    audio_system: Optional[str] = None
    speakers_count: Optional[str] = None
    bluetooth: Optional[str] = None
    usb: Optional[str] = None
    aux: Optional[str] = None

    # Освещение
    headlight_type: Optional[str] = None
    fog_lights: Optional[str] = None
    led_lights: Optional[str] = None
    daytime_running: Optional[str] = None

    # История и состояние
    first_registration_time: Optional[str] = None  # Дата первой регистрации (как на площадке)
    owner_count: Optional[int] = 0
    accident_history: Optional[str] = None
    service_history: Optional[str] = None
    warranty_info: Optional[str] = None
    inspection_date: Optional[str] = None
    insurance_info: Optional[str] = None

    # Дополнительные детали
    interior_color: Optional[str] = None
    exterior_color: Optional[str] = None
    upholstery: Optional[str] = None
    sunroof: Optional[str] = None
    panoramic_roof: Optional[str] = None

    # Дополнительные метаданные
    view_count: Optional[int] = 0
    favorite_count: Optional[int] = 0
    contact_info: Optional[str] = None
    dealer_info: Optional[str] = None
    certification: Optional[str] = None

    # Карусель изображений
    image_gallery: Optional[str] = None
    image_count: Optional[int] = 0

    # Дополнительные характеристики
    seat_count: Optional[str] = None
    door_count: Optional[str] = None
    trunk_volume: Optional[str] = None
    fuel_tank_volume: Optional[str] = None

    # Таможенные и утилизационные сборы
    recycling_fee: Optional[str] = None  # Утильсбор
    customs_duty: Optional[str] = None  # Таможенный сбор
