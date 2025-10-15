"""
Утилиты для батчинга данных
"""
from typing import List, TypeVar, Iterator

T = TypeVar('T')


def batch_items(items: List[T], batch_size: int = 10) -> Iterator[List[T]]:
    """
    Разбивает список элементов на батчи заданного размера
    
    Args:
        items: Список элементов для разбиения
        batch_size: Размер батча (по умолчанию 10)
    
    Yields:
        Список элементов батча
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def extract_string_values(data: dict) -> List[str]:
    """
    Извлекает все строковые значения из словаря
    
    Args:
        data: Словарь для извлечения строковых значений
    
    Returns:
        Список строковых значений
    """
    string_values = []
    
    def _extract_recursive(obj):
        if isinstance(obj, dict):
            for value in obj.values():
                _extract_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                _extract_recursive(item)
        elif isinstance(obj, str) and obj.strip():
            string_values.append(obj.strip())
    
    _extract_recursive(data)
    return string_values


def reconstruct_with_translations(original_data: dict, translations: List[str]) -> dict:
    """
    Восстанавливает структуру данных с переводами
    
    Args:
        original_data: Исходная структура данных
        translations: Список переводов в том же порядке, что и извлеченные строки
    
    Returns:
        Словарь с переведенными значениями
    """
    result = {}
    translation_index = 0
    
    def _reconstruct_recursive(obj):
        nonlocal translation_index
        
        if isinstance(obj, dict):
            new_dict = {}
            for key, value in obj.items():
                new_dict[key] = _reconstruct_recursive(value)
            return new_dict
        elif isinstance(obj, list):
            return [_reconstruct_recursive(item) for item in obj]
        elif isinstance(obj, str) and obj.strip():
            if translation_index < len(translations):
                translated = translations[translation_index]
                translation_index += 1
                return translated
            return obj
        else:
            return obj
    
    return _reconstruct_recursive(original_data)
