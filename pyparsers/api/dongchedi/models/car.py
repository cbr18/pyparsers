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
    body_type: Optional[str] = None
    drive_type: Optional[str] = None
    condition: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
