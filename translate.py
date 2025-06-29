from googletrans import Translator
import re

def translate_text(text: str, dest: str = 'ru') -> str:
    if not text:
        return ''
    
    # Очищаем текст от проблемных символов кодировки
    text = clean_text(text)
    
    translator = Translator()
    try:
        # Используем синхронный метод перевода
        result = translator.translate(text, dest=dest)
        return result.text
    except Exception:
        return text

def clean_text(text: str) -> str:
    """
    Очищает текст от проблемных символов кодировки
    """
    if not text:
        return text
    
    # Удаляем символы, которые могут быть результатом неправильной кодировки
    # Паттерн для поиска символов типа Âí×Ô´ï3
    pattern = r'[ÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ]'
    text = re.sub(pattern, '', text)
    
    # Удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
