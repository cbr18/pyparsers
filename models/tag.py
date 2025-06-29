from pydantic import BaseModel
from typing import Optional

class Tag(BaseModel):
    background_color: Optional[str]
    logo: Optional[str]
    text: Optional[str]
    text_color: Optional[str]
