from abc import ABC, abstractmethod
from typing import Optional
from models.response import ApiResponse

class BaseCarParser(ABC):
    """Базовый класс для всех парсеров автомобилей"""
    
    @abstractmethod
    def fetch_cars(self, source: Optional[str] = None) -> ApiResponse:
        """
        Основной метод для получения данных о машинах
        
        Args:
            source: Источник данных (может быть 'url', путь к файлу и т.д.)  # убран 'local'
            
        Returns:
            ApiResponse: Унифицированный ответ с данными о машинах
        """
        pass
    
    def get_parser_name(self) -> str:
        """Возвращает название парсера"""
        return self.__class__.__name__