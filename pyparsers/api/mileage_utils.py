import re
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

"""
Утилиты для нормализации пробега.
Возвращает значение в километрах и метаданные с выбранным правилом и предупреждениями.
"""

_EMPTY_MARKERS = {"", "-", "--", "—", "null", "none", "暂无", "未填", "未知"}


def _clean_raw(raw: Any) -> str:
    raw_str = str(raw).strip()
    # Удаляем распространённые разделители
    return raw_str.replace("，", ",").strip()


def normalize_mileage(
    raw: Any,
    *,
    year_hint: Optional[int] = None,
    source: Optional[str] = None,
) -> Tuple[Optional[int], Dict[str, Any]]:
    """
    Нормализует пробег в километры.

    Args:
        raw: исходное значение (строка/число)
        year_hint: год выпуска для эвристик
        source: имя источника для метаданных

    Returns:
        (mileage_km | None, meta: dict)
    """
    meta: Dict[str, Any] = {"raw": raw, "unit": None, "rule": None, "warnings": [], "source": source}

    if raw is None:
        meta["warnings"].append("empty")
        return None, meta

    raw_str = _clean_raw(raw)
    if raw_str.lower() in _EMPTY_MARKERS:
        meta["warnings"].append("empty")
        return None, meta

    # Признаки юнита
    lower = raw_str.lower()
    unit = None
    if re.search(r"(万|w)\s*(公里|km|千米)?", lower):
        unit = "wan_km"
    elif re.search(r"(公里|千米|km)\b", lower):
        unit = "km"

    # Число
    num_match = re.search(r"(\d+\.?\d*)", lower)
    if not num_match:
        meta["warnings"].append("no_number")
        return None, meta

    try:
        number = float(num_match.group(1))
    except ValueError:
        meta["warnings"].append("nan")
        return None, meta

    meta["number"] = number
    meta["unit"] = unit

    # Эвристика юнитов, если не указаны явно.
    if unit is None:
        if number <= 50:
            unit = "wan_km"  # типичный формат площадок без юнита
            meta["rule"] = "assume_wan_threshold"
        elif number >= 500:
            unit = "km"
            meta["rule"] = "assume_km_threshold"
        else:
            unit = "km"
            meta["rule"] = "assume_km_default"

    km = int(number * 10000) if unit == "wan_km" else int(number)
    meta["km"] = km

    # Санити-проверки
    if km <= 0:
        meta["warnings"].append("non_positive")
        return None, meta

    if km > 1_500_000:
        meta["warnings"].append("too_high")
        return None, meta

    current_year = datetime.utcnow().year
    if year_hint and (current_year - year_hint) >= 3 and km < 3_000:
        meta["warnings"].append("too_low_for_age")

    return km, meta

