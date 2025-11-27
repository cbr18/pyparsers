import re
from datetime import datetime
from typing import Optional


def normalize_first_registration_date(raw_value: Optional[str]) -> Optional[str]:
    """
    Normalize different date-like strings (e.g. "2018-03", "2018年03月", "2018/03/15")
    to ISO format YYYY-MM-DD so it can be stored in DATE columns.
    """
    if not raw_value:
        return None

    text = str(raw_value).strip()
    if not text:
        return None

    # Extract numeric chunks (year, month, day) regardless of separators
    numbers = re.findall(r"\d+", text)
    if not numbers:
        return None

    try:
        year = int(numbers[0])
    except ValueError:
        return None

    if year < 1900 or year > 2100:
        return None

    try:
        month = int(numbers[1]) if len(numbers) > 1 else 1
    except ValueError:
        month = 1
    if month < 1 or month > 12:
        month = 1

    try:
        day = int(numbers[2]) if len(numbers) > 2 else 1
    except ValueError:
        day = 1
    if day < 1 or day > 31:
        day = 1

    try:
        normalized = datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        # Fallback to first day of month even if day was invalid
        normalized = datetime(year, month, 1).strftime("%Y-%m-%d")

    return normalized

