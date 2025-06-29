def decode_sh_price(text: str) -> str:
    """
    Преобразует строку цены из поля sh_price, заменяя спецсимволы на цифры и единицы измерения.
    """
    if not text:
        return ''
    mapping = {
        '\ue54c': '1',
        '\ue463': '2',
        '\ue49d': '3',
        '\ue41d': '4',  # Не подтверждено
        '\ue411': '5',
        '\ue534': '6',
        '\ue3eb': '7',
        '\ue4e3': '8',
        '\ue45d': '9',
        '\ue439': '0',
        '\ue40a': ' mln youan',
    }
    result = ''
    for char in text:
        result += mapping.get(char, char)
    return result
