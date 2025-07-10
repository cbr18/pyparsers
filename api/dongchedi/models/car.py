from pydantic import BaseModel
from typing import Optional

class DongchediCar(BaseModel):
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
    shop_id: Optional[str] = None
    car_id: Optional[int] = None
    tags_v2: Optional[str] = None 