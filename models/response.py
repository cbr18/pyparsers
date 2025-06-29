from pydantic import BaseModel
from typing import Optional, List
from .car import Car

class Data(BaseModel):
    has_more: bool
    search_sh_sku_info_list: List[Car]
    total: int

class ApiResponse(BaseModel):
    data: Data
    message: str
    prompts: Optional[str]
    status: int
