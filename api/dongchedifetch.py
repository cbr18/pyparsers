import requests
from typing import Optional
from models.response import ApiResponse
from .base_parser import BaseCarParser

class DongchediParser(BaseCarParser):
    """Парсер для сайта Dongchedi"""
    
    def __init__(self):
        self.api_url = "https://www.dongchedi.com/motor/pc/sh/sh_sku_list?aid=1839&app_name=auto_web_pc&sh_city_name=北京&page=1&limit=30&sort_type=4"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
    
    def fetch_cars(self, source: Optional[str] = None) -> ApiResponse:
        """
        Выполняет запрос к API dongchedi и возвращает распарсенный ApiResponse.
        
        Args:
            source: Игнорируется для этого парсера, так как используется API
            
        Returns:
            ApiResponse: Унифицированный ответ с данными о машинах
        """
        response = requests.post(self.api_url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return ApiResponse(**data)

# Функция для обратной совместимости
def fetch_dongchedi_cars() -> ApiResponse:
    """Функция для обратной совместимости"""
    parser = DongchediParser()
    return parser.fetch_cars()


