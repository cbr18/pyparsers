from pydantic import BaseModel
from typing import Optional

class BrandInfo(BaseModel):
    brand_id: int
    image_url: str
    brand_name: str
    pinyin: str
    brand_activity_tag: Optional[str]
    ad_materiel: Optional[str]
    discount_tag: Optional[str]
    business_status: int
    on_sale_series_count: int

class Brand(BaseModel):
    type: int
    info: BrandInfo
    unique_id: int
    unique_id_str: str
