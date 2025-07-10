from typing import Dict, Type
from .base_parser import BaseCarParser
# Здесь могут быть другие импорты и код, если нужно

class ParserFactory:
    """Фабрика для создания парсеров (заглушка)"""
    _parsers: Dict[str, Type[BaseCarParser]] = {}
    
    @classmethod
    def get_parser(cls, parser_name: str) -> BaseCarParser:
        raise ValueError(f"Парсер '{parser_name}' не найден. Зарегистрируйте парсер через register_parser().")
    
    @classmethod
    def get_available_parsers(cls) -> list:
        return list(cls._parsers.keys())

    @classmethod
    def register_parser(cls, name: str, parser_class: Type[BaseCarParser]):
        cls._parsers[name] = parser_class