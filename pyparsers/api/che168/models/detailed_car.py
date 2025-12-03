from pydantic import BaseModel
from typing import Optional

class Che168DetailedCar(BaseModel):
    """Расширенная модель для детальной информации о машине с che168.com"""
    
    # Основная информация
    car_id: Optional[int] = None
    title: Optional[str] = None
    price: Optional[float] = None  # Цена в wan юаней - NUMERIC(8,2)
    year: Optional[int] = None
    mileage: Optional[str] = None
    city: Optional[str] = None
    brand_name: Optional[str] = None
    series_name: Optional[str] = None
    image: Optional[str] = None  # Главное изображение
    
    # Технические характеристики
    engine_volume: Optional[str] = None
    engine_volume_ml: Optional[int] = None  # Объём двигателя в миллилитрах - INTEGER
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    drive_type: Optional[str] = None
    body_type: Optional[str] = None
    color: Optional[str] = None
    condition: Optional[str] = None
    
    # Дополнительные характеристики
    power: Optional[int] = None  # Мощность в л.с. - SMALLINT
    torque: Optional[float] = None  # Крутящий момент в Н·м - NUMERIC(6,1)
    acceleration: Optional[float] = None  # Разгон до 100 км/ч в секундах - NUMERIC(4,1)
    max_speed: Optional[int] = None  # Максимальная скорость в км/ч - SMALLINT
    fuel_consumption: Optional[float] = None  # Расход топлива л/100км - NUMERIC(4,1)
    emission_standard: Optional[str] = None
    
    # Размеры и вес
    length: Optional[int] = None  # Длина (мм) - SMALLINT
    width: Optional[int] = None  # Ширина (мм) - SMALLINT
    height: Optional[int] = None  # Высота (мм) - SMALLINT
    wheelbase: Optional[int] = None  # Колесная база (мм) - SMALLINT
    curb_weight: Optional[int] = None  # Снаряженная масса (кг) - SMALLINT
    gross_weight: Optional[str] = None
    
    # Двигатель
    engine_type: Optional[str] = None
    engine_code: Optional[str] = None
    cylinder_count: Optional[str] = None
    valve_count: Optional[str] = None
    compression_ratio: Optional[str] = None
    turbo_type: Optional[str] = None
    
    # Электрические характеристики
    battery_capacity: Optional[float] = None  # Емкость батареи в кВт·ч - NUMERIC(6,2)
    electric_range: Optional[int] = None  # Запас хода в км - SMALLINT
    charging_time: Optional[str] = None
    fast_charge_time: Optional[str] = None
    charge_port_type: Optional[str] = None
    
    # Трансмиссия
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
    
    # Комфорт
    air_conditioning: Optional[str] = None
    climate_control: Optional[str] = None
    seat_heating: Optional[str] = None
    seat_ventilation: Optional[str] = None
    seat_massage: Optional[str] = None
    steering_wheel_heating: Optional[str] = None
    
    # Мультимедиа
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
    
    # История
    first_registration_time: Optional[str] = None  # Дата первой регистрации в формате YYYY-MM-DD
    owner_count: Optional[int] = None
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
    
    # Метаданные
    view_count: Optional[int] = None
    favorite_count: Optional[int] = None
    contact_info: Optional[str] = None
    dealer_info: Optional[str] = None
    certification: Optional[str] = None
    
    # Изображения
    image_gallery: Optional[str] = None  # Ссылки через пробел
    image_count: Optional[int] = None
    
    # Дополнительные характеристики
    seat_count: Optional[str] = None
    door_count: Optional[int] = None  # Количество дверей - SMALLINT
    trunk_volume: Optional[str] = None
    fuel_tank_volume: Optional[str] = None
    
    # Описание
    description: Optional[str] = None





