from pydantic import BaseModel
from typing import Optional

class FilteredCar(BaseModel):
    title: Optional[str]
    sh_price: Optional[str]
    image: Optional[str]
    car_year: Optional[int]
    car_mileage: Optional[str]
    car_source_city_name: Optional[str]
    brand_name: Optional[str]
    series_name: Optional[str]
    car_name: Optional[str]
    car_source_type: Optional[str]
    transfer_cnt: Optional[int] 