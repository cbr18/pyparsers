from typing import List, Optional

from pydantic import BaseModel

from .car import EncarCar


class EncarData(BaseModel):
    has_more: bool
    search_sh_sku_info_list: List[EncarCar]
    total: int


class EncarApiResponse(BaseModel):
    data: EncarData
    message: str
    prompts: Optional[str] = None
    status: int
