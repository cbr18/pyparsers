from pydantic import BaseModel
from typing import Optional, List
from .tag import Tag

class CarBase(BaseModel):
    title: Optional[str] = None
    sh_price: Optional[str] = None
    image: Optional[str] = None
    link: Optional[str] = None
    car_name: Optional[str] = None
    car_year: Optional[int] = None
    car_mileage: Optional[str] = None
    car_source_city_name: Optional[str] = None

class Car(CarBase):
    authentication_method: Optional[str] = None
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    brand_source_city_name: Optional[str] = None
    car_age: Optional[str] = None
    car_id: Optional[int] = None
    car_source_type: Optional[str] = None
    group_id: Optional[int] = None
    group_id_str: Optional[str] = None
    is_self_trade: Optional[bool] = None
    is_video: Optional[bool] = None
    official_hint_bar: Optional[str] = None
    official_price: Optional[str] = None
    platform_type: Optional[int] = None
    related_video_thumb: Optional[str] = None
    series_id: Optional[int] = None
    series_name: Optional[str] = None
    shop_id: Optional[str] = None
    sku_id: Optional[int] = None
    special_tags: Optional[str] = None
    spu_id: Optional[int] = None
    sub_title: Optional[str] = None
    tags: Optional[List[Tag]] = None
    tags_v2: Optional[str] = None
    transfer_cnt: Optional[int] = None
