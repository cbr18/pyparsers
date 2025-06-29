import requests
from models.response import ApiResponse

API_URL = "https://www.dongchedi.com/motor/pc/sh/sh_sku_list?aid=1839&app_name=auto_web_pc&sh_city_name=北京&page=1&limit=30&sort_type=4"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

def fetch_dongchedi_cars() -> ApiResponse:
    """
    Выполняет запрос к API dongchedi и возвращает распарсенный ApiResponse.
    """
    response = requests.post(API_URL, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    return ApiResponse(**data)
