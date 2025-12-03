from pydantic import BaseModel
from typing import Optional

class Che168Car(BaseModel):
    title: Optional[str] = None
    sh_price: Optional[str] = None
    image: Optional[str] = None
    link: Optional[str] = None
    car_name: Optional[str] = None
    car_year: Optional[int] = None
    car_mileage: Optional[str] = None
    car_source_city_name: Optional[str] = None
    brand_name: Optional[str] = None
    series_name: Optional[str] = None
    brand_id: Optional[int] = None
    series_id: Optional[int] = None
    shop_id: Optional[int] = None  # ID магазина - INTEGER
    car_id: Optional[int] = None
    tags_v2: Optional[str] = None
    is_available: Optional[bool] = True
    recycling_fee: Optional[int] = None  # Утильсбор в рублях - INTEGER
    customs_duty: Optional[int] = None  # Таможенная пошлина в рублях - INTEGER
    first_registration_time: Optional[str] = None  # Дата первой регистрации в формате YYYY-MM-DD
    power: Optional[int] = None  # Мощность в л.с. - SMALLINT 