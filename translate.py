from googletrans import Translator

def translate_text(text: str, dest: str = 'ru') -> str:
    if not text:
        return ''
    translator = Translator()
    try:
        result = translator.translate(text, dest=dest)
        return result.text
    except Exception:
        return text
