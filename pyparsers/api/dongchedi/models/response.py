from pydantic import BaseModel
from typing import Optional, List
from .car import DongchediCar

class DongchediData(BaseModel):
    has_more: bool
    search_sh_sku_info_list: List[DongchediCar]
    total: int

class DongchediApiResponse(BaseModel):
    data: DongchediData
    message: str
    prompts: Optional[str] = None
    status: int 