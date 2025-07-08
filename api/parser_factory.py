from typing import Dict, Type
from .base_parser import BaseCarParser
from .dongchedifetch import DongchediParser

class ParserFactory:
    """Фабрика для создания парсеров (только Dongchedi)"""
    
    _parsers: Dict[str, Type[BaseCarParser]] = {
        'dongchedi': DongchediParser,
    }
    
    @classmethod
    def get_parser(cls, parser_name: str) -> BaseCarParser:
        """
        Создает и возвращает парсер по имени
        
        Args:
            parser_name: Название парсера ('dongchedi')
            
        Returns:
            BaseCarParser: Экземпляр парсера
            
        Raises:
            ValueError: Если парсер с таким именем не найден
        """
        if parser_name not in cls._parsers:
            available = ', '.join(cls._parsers.keys())
            raise ValueError(f"Парсер '{parser_name}' не найден. Доступные: {available}")
        
        return cls._parsers[parser_name]()
    
    @classmethod
    def get_available_parsers(cls) -> list:
        """Возвращает список доступных парсеров"""
        return list(cls._parsers.keys())

    @classmethod
    def register_parser(cls, name: str, parser_class: Type[BaseCarParser]):
        """Регистрирует новый парсер"""
        cls._parsers[name] = parser_class