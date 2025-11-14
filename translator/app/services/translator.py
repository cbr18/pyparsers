"""
Сервис перевода текстов через Yandex Translate API
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
import httpx
from .cache import CacheService
from ..utils.batcher import batch_items, extract_string_values, reconstruct_with_translations

logger = logging.getLogger(__name__)


class TranslatorService:
    """Сервис для перевода текстов через Yandex Translate API"""
    
    def __init__(
        self,
        api_key: str,
        folder_id: str,
        cache_service: CacheService,
        *,
        max_concurrent_batches: int = 3,
    ):
        self.api_key = api_key
        self.folder_id = folder_id
        self.cache_service = cache_service
        self.base_url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
        self.max_retries = 3
        self.retry_delay = 1.0
        self.max_concurrent_batches = max(1, max_concurrent_batches)
        self._numeric_allowed_chars = set("0123456789.,:;+-–—/\\%()[]{}° ")
        
    async def _make_api_request(self, texts: List[str], source_lang: str = "zh", target_lang: str = "ru") -> List[str]:
        """
        Выполняет запрос к Yandex Translate API
        
        Args:
            texts: Список текстов для перевода
            source_lang: Исходный язык
            target_lang: Целевой язык
        
        Returns:
            Список переводов
        """
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "texts": texts,
            "targetLanguageCode": target_lang,
            "sourceLanguageCode": source_lang,
            "folderId": self.folder_id
        }
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(self.base_url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        translations = [item["text"] for item in data.get("translations", [])]
                        logger.info(f"Успешно переведено {len(translations)} текстов через API")
                        return translations
                    
                    elif response.status_code == 429:
                        # Rate limit - увеличиваем задержку
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limit, ожидание {wait_time} секунд (попытка {attempt + 1})")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                        if attempt == self.max_retries - 1:
                            raise Exception(f"API вернул ошибку {response.status_code}")
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        
            except httpx.TimeoutException:
                logger.warning(f"Таймаут запроса (попытка {attempt + 1})")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                
            except Exception as e:
                logger.error(f"Ошибка запроса к API: {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        raise Exception("Превышено максимальное количество попыток")
    
    async def translate_text(self, text: str, source_lang: str = "zh", target_lang: str = "ru") -> str:
        """
        Переводит одиночный текст
        
        Args:
            text: Текст для перевода
            source_lang: Исходный язык
            target_lang: Целевой язык
        
        Returns:
            Переведенный текст
        """
        if not text.strip():
            return text

        if self._is_numeric_only(text):
            return text
        
        # Проверяем кэш
        cached_translation = await self.cache_service.get_translation(text, source_lang, target_lang)
        if cached_translation:
            return cached_translation
        
        # Переводим через API
        translations = await self._make_api_request([text], source_lang, target_lang)
        translation = translations[0] if translations else text
        
        # Сохраняем в кэш
        await self.cache_service.set_translation(text, translation, source_lang, target_lang)
        
        return translation
    
    async def translate_batch(self, texts: List[str], source_lang: str = "zh", target_lang: str = "ru") -> List[str]:
        """
        Переводит список текстов батчами
        
        Args:
            texts: Список текстов для перевода
            source_lang: Исходный язык
            target_lang: Целевой язык
        
        Returns:
            Список переводов
        """
        if not texts:
            return []
        
        # Фильтруем пустые тексты
        non_empty_texts = [text for text in texts if text.strip()]
        if not non_empty_texts:
            return [""] * len(texts)
        
        numeric_texts = {text for text in non_empty_texts if self._is_numeric_only(text)}
        
        # Проверяем кэш для всех текстов
        cached_translations = await self.cache_service.get_batch_translations(non_empty_texts, source_lang, target_lang)
        
        # Определяем, какие тексты нужно перевести
        texts_to_translate = []
        translation_map = {}
        
        for text, cached in zip(non_empty_texts, cached_translations):
            if text in numeric_texts:
                translation_map[text] = text
                continue

            if cached:
                translation_map[text] = cached
            else:
                texts_to_translate.append(text)
        
        # Переводим оставшиеся тексты батчами
        if texts_to_translate:
            batches = [batch for batch in batch_items(texts_to_translate, 10)]
            semaphore = asyncio.Semaphore(self.max_concurrent_batches)

            async def process_batch(batch: List[str]) -> List[str]:
                async with semaphore:
                    translations = await self._make_api_request(batch, source_lang, target_lang)
                await self.cache_service.set_batch_translations(batch, translations, source_lang, target_lang)
                return translations

            tasks = [process_batch(batch) for batch in batches]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for batch, result in zip(batches, results):
                if isinstance(result, Exception):
                    logger.error(f"Ошибка перевода батча: {result}")
                    for text in batch:
                        translation_map[text] = text
                else:
                    for text, translation in zip(batch, result):
                        translation_map[text] = translation
        
        # Формируем результат в том же порядке
        result = []
        for text in texts:
            if text.strip() and text in translation_map:
                result.append(translation_map[text])
            else:
                result.append(text)
        
        return result
    
    async def translate_json(self, data: Dict[str, Any], source_lang: str = "zh", target_lang: str = "ru") -> Dict[str, Any]:
        """
        Переводит все строковые значения в JSON объекте
        
        Args:
            data: JSON объект для перевода
            source_lang: Исходный язык
            target_lang: Целевой язык
        
        Returns:
            JSON объект с переведенными значениями
        """
        # Извлекаем все строковые значения
        string_values = extract_string_values(data)
        
        if not string_values:
            return data
        
        # Переводим все строки
        translations = await self.translate_batch(string_values, source_lang, target_lang)
        
        # Восстанавливаем структуру с переводами
        return reconstruct_with_translations(data, translations)
    
    async def translate_database_batch(self, records: List[Dict[str, Any]], source_lang: str = "zh", target_lang: str = "ru") -> List[Dict[str, Any]]:
        """
        Переводит батч записей из базы данных
        
        Args:
            records: Список записей для перевода
            source_lang: Исходный язык
            target_lang: Целевой язык
        
        Returns:
            Список переведенных записей
        """
        if not records:
            return []
        
        logger.info(f"Начинаем перевод {len(records)} записей из базы данных")
        
        translated_records = []
        total_translated = 0
        
        for i, record in enumerate(records):
            try:
                translated_record = await self.translate_json(record, source_lang, target_lang)
                translated_records.append(translated_record)
                total_translated += 1
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Переведено {i + 1}/{len(records)} записей")
                    
            except Exception as e:
                logger.error(f"Ошибка перевода записи {i}: {e}")
                translated_records.append(record)  # Возвращаем исходную запись
        
        logger.info(f"Завершен перевод базы данных. Переведено: {total_translated}/{len(records)} записей")
        return translated_records
    
    async def get_translation_stats(self) -> Dict[str, Any]:
        """Получает статистику переводов"""
        cache_stats = await self.cache_service.get_cache_stats()
        return {
            "cache_stats": cache_stats,
            "api_key_configured": bool(self.api_key),
            "folder_id_configured": bool(self.folder_id)
        }

    def _is_numeric_only(self, text: str) -> bool:
        if not text:
            return False

        stripped = text.strip()
        if not stripped:
            return False

        has_digit = False
        for char in stripped:
            if char.isdigit():
                has_digit = True
                continue
            if char not in self._numeric_allowed_chars:
                return False

        return has_digit
