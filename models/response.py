from pydantic import BaseModel
from typing import Optional, List
from .filtered_car import FilteredCar

class Data(BaseModel):
    has_more: bool
    search_sh_sku_info_list: List[FilteredCar]
    total: int

class ApiResponse(BaseModel):
    data: Data
    message: str
    prompts: Optional[str] = None
    status: int
