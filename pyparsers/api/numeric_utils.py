import re
import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)

_PS_PATTERN = re.compile(r'\(([\d.,]+)\s*[Pp][Ss]?\)')
_HORSEPOWER_UNIT_PATTERN = re.compile(r'([\d.,]+)\s*(?:[Pp][Ss]?|л\.с\.|HP|hp|马力)')
_KW_PATTERN = re.compile(r'[\d.,]+\s*[Kk][Ww]')
_FIRST_NUMBER_PATTERN = re.compile(r'([\d.,]+)')
_KW_TO_HP = 1.35962

def parse_int_value(value: Union[str, int, float, None]) -> Optional[int]:
    """
    Извлекает целое число из строки или другого типа.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    
    try:
        # Убираем запятые и пробелы
        text = str(value).replace(',', '').replace(' ', '').strip()
        # Ищем первое число в строке
        match = re.search(r'(-?\d+)', text)
        if match:
            return int(match.group(1))
    except (ValueError, TypeError):
        pass
    return None

def parse_float_value(value: Union[str, int, float, None]) -> Optional[float]:
    """
    Извлекает дробное число из строки или другого типа.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    
    try:
        # Убираем запятые и пробелы, заменяем запятую-разделитель на точку если надо
        text = str(value).replace(',', '.').replace(' ', '').strip()
        # Ищем первое число с плавающей точкой
        match = re.search(r'(-?\d+\.?\d*)', text)
        if match:
            return float(match.group(1))
    except (ValueError, TypeError):
        pass
    return None

def _parse_number(text: str) -> Optional[float]:
    match = _FIRST_NUMBER_PATTERN.search(text)
    if not match:
        return None
    number_str = match.group(1).replace(',', '.')
    try:
        return float(number_str)
    except ValueError:
        return None

def normalize_power_value(value: Union[str, int, float, None], assume_kw: bool = False) -> Optional[int]:
    """
    Нормализует значение мощности в лошадиные силы (л.с.).
    Поддерживает форматы: "184hp", "135kW", "200ps", "250马力".
    """
    if value is None:
        return None
    
    value_str = str(value).strip()
    if not value_str:
        return None
        
    normalized = value_str.replace('（', '(').replace('）', ')')

    # 1. Ищем формат (XXX PS)
    match = _PS_PATTERN.search(normalized)
    if match:
        number = _parse_number(match.group(1))
        if number is not None:
            return int(round(number))

    # 2. Ищем единицы измерения л.с./ps/hp/马力
    match = _HORSEPOWER_UNIT_PATTERN.search(normalized)
    if match:
        number = _parse_number(match.group(1))
        if number is not None:
            return int(round(number))

    # 3. Ищем kW
    if _KW_PATTERN.search(normalized.lower()):
        number = _parse_number(normalized)
        if number is not None:
            return int(round(number * _KW_TO_HP))

    # 4. Если форсируем kW
    if assume_kw:
        number = _parse_number(normalized)
        if number is not None:
            return int(round(number * _KW_TO_HP))

    # 5. Просто число
    number = _parse_number(normalized)
    if number is not None:
        return int(round(number))

    return None
