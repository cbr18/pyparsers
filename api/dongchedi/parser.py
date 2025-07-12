import requests
from typing import Optional
from .models.response import DongchediApiResponse, DongchediData
from .models.car import DongchediCar
from ..base_parser import BaseCarParser

class DongchediParser(BaseCarParser):
    """Парсер для сайта Dongchedi"""
    
    def __init__(self):
        self.base_url = "https://www.dongchedi.com/motor/pc/sh/sh_sku_list"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
    
    def _build_url(self, page: int = 1) -> str:
        """Строит URL с параметрами запроса"""
        params = {
            "aid": "1839",
            "app_name": "auto_web_pc",
            "sh_city_name": "北京",
            "page": str(page),
            "limit": "80",
            "sort_type": "4"
        }
        
        # Строим URL с параметрами
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}?{param_string}"
    
    def fetch_cars(self, source: Optional[str] = None) -> DongchediApiResponse:
        """
        Выполняет запрос к API dongchedi и возвращает распарсенный DongchediApiResponse.
        По умолчанию загружает первую страницу.
        
        Args:
            source: Игнорируется для этого парсера, так как используется API
            
        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        return self.fetch_cars_by_page(1)
    
    def fetch_cars_by_page(self, page: int) -> DongchediApiResponse:
        """
        Выполняет запрос к API dongchedi для конкретной страницы.
        
        Args:
            page: Номер страницы (начиная с 1)
            
        Returns:
            DongchediApiResponse: Унифицированный ответ с данными о машинах
        """
        try:
            url = self._build_url(page)
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            # Преобразуем данные в наши модели
            cars = []
            if 'data' in data and 'search_sh_sku_info_list' in data['data']:
                for car_data in data['data']['search_sh_sku_info_list']:
                    car = DongchediCar(**car_data)
                    cars.append(car)
            
            # Если данных нет или список пуст, считаем что страницы не существует
            if not cars:
                return DongchediApiResponse(
                    data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                    message=f"Страница {page} не найдена",
                    status=404
                )
            
            dongchedi_data = DongchediData(
                has_more=data.get('data', {}).get('has_more', False),
                search_sh_sku_info_list=cars,
                total=data.get('data', {}).get('total', 0)
            )
            
            return DongchediApiResponse(
                data=dongchedi_data,
                message=data.get('message', 'Success'),
                status=data.get('status', 200)
            )
            
        except Exception as e:
            return DongchediApiResponse(
                data=DongchediData(has_more=False, search_sh_sku_info_list=[], total=0),
                message=f"Страница {page} не найдена",
                status=404
            ) 