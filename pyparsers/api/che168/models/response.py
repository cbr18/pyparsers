from pydantic import BaseModel
from typing import Optional, List
from .car import Che168Car

class Che168Data(BaseModel):
    has_more: bool
    search_sh_sku_info_list: List[Che168Car]
    total: int

class Che168ApiResponse(BaseModel):
    data: Che168Data
    message: str
    prompts: Optional[str] = None
    status: int 