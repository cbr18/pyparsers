"""
Сервис кэширования переводов в Redis
"""
import hashlib
import json
import logging
import os
from typing import Optional, List
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheService:
    """Сервис для работы с кэшем переводов"""
    
    def __init__(self, redis_url: str = "redis://redis:6379", default_ttl: Optional[int] = None):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        env_ttl = os.getenv("TRANSLATOR_CACHE_TTL")
        try:
            env_ttl_value = int(env_ttl) if env_ttl else None
        except ValueError:
            logger.warning("Некорректное значение TRANSLATOR_CACHE_TTL: %s. Используется значение по умолчанию.", env_ttl)
            env_ttl_value = None
        self.default_ttl = default_ttl if default_ttl is not None else (env_ttl_value if env_ttl_value is not None else 86400)
    
    async def connect(self):
        """Подключение к Redis"""
        try:
            self.redis = redis.from_url(self.redis_url)
            logger.info("Подключение к Redis установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            raise
    
    async def disconnect(self):
        """Отключение от Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Отключение от Redis")
    
    def is_connected(self) -> bool:
        """Проверка подключения к Redis"""
        return self.redis is not None
    
    def _generate_key(self, text: str, source_lang: str = "zh", target_lang: str = "ru") -> str:
        """
        Генерирует ключ для кэша на основе текста и языков
        
        Args:
            text: Исходный текст
            source_lang: Исходный язык
            target_lang: Целевой язык
        
        Returns:
            Ключ для кэша
        """
        key_data = f"{text}|{source_lang}|{target_lang}"
        return f"translate:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get_translation(self, text: str, source_lang: str = "zh", target_lang: str = "ru") -> Optional[str]:
        """
        Получает перевод из кэша
        
        Args:
            text: Исходный текст
            source_lang: Исходный язык
            target_lang: Целевой язык
        
        Returns:
            Переведенный текст или None, если не найден в кэше
        """
        if not self.redis:
            return None
        
        try:
            key = self._generate_key(text, source_lang, target_lang)
            cached_translation = await self.redis.get(key)
            
            if cached_translation:
                logger.info(f"Перевод найден в кэше для текста: {text[:50]}...")
                if self.default_ttl:
                    try:
                        await self.redis.expire(key, self.default_ttl)
                    except Exception as ttl_error:
                        logger.warning(f"Не удалось обновить TTL для ключа {key}: {ttl_error}")
                return cached_translation.decode('utf-8')
            
            return None
        except Exception as e:
            logger.error(f"Ошибка получения из кэша: {e}")
            return None
    
    async def set_translation(self, text: str, translation: str, source_lang: str = "zh", target_lang: str = "ru", ttl: Optional[int] = None):
        """
        Сохраняет перевод в кэш
        
        Args:
            text: Исходный текст
            translation: Переведенный текст
            source_lang: Исходный язык
            target_lang: Целевой язык
            ttl: Время жизни в секундах (по умолчанию 24 часа)
        """
        if not self.redis:
            return
        
        try:
            key = self._generate_key(text, source_lang, target_lang)
            ttl_to_use = ttl if ttl is not None else self.default_ttl
            if ttl_to_use:
                await self.redis.set(key, translation, ex=ttl_to_use)
            else:
                await self.redis.set(key, translation)
            logger.info(f"Перевод сохранен в кэш для текста: {text[:50]}...")
        except Exception as e:
            logger.error(f"Ошибка сохранения в кэш: {e}")
    
    async def get_batch_translations(self, texts: List[str], source_lang: str = "zh", target_lang: str = "ru") -> List[Optional[str]]:
        """
        Получает переводы для списка текстов из кэша
        
        Args:
            texts: Список исходных текстов
            source_lang: Исходный язык
            target_lang: Целевой язык
        
        Returns:
            Список переводов (None для текстов, не найденных в кэше)
        """
        if not self.redis:
            return [None] * len(texts)
        
        try:
            keys = [self._generate_key(text, source_lang, target_lang) for text in texts]
            cached_translations = await self.redis.mget(keys)
            
            result = []
            keys_to_refresh = []
            for i, cached in enumerate(cached_translations):
                if cached:
                    result.append(cached.decode('utf-8'))
                    logger.info(f"Перевод найден в кэше для текста: {texts[i][:50]}...")
                    keys_to_refresh.append(keys[i])
                else:
                    result.append(None)
            
            if keys_to_refresh and self.default_ttl:
                pipe = self.redis.pipeline()
                for key in keys_to_refresh:
                    pipe.expire(key, self.default_ttl)
                await pipe.execute()
            
            return result
        except Exception as e:
            logger.error(f"Ошибка получения батча из кэша: {e}")
            return [None] * len(texts)
    
    async def set_batch_translations(self, texts: List[str], translations: List[str], source_lang: str = "zh", target_lang: str = "ru", ttl: Optional[int] = None):
        """
        Сохраняет переводы для списка текстов в кэш
        
        Args:
            texts: Список исходных текстов
            translations: Список переводов
            source_lang: Исходный язык
            target_lang: Целевой язык
            ttl: Время жизни в секундах
        """
        if not self.redis or len(texts) != len(translations):
            return
        
        try:
            pipe = self.redis.pipeline()
            ttl_to_use = ttl if ttl is not None else self.default_ttl
            for text, translation in zip(texts, translations):
                key = self._generate_key(text, source_lang, target_lang)
                if ttl_to_use:
                    pipe.set(key, translation, ex=ttl_to_use)
                else:
                    pipe.set(key, translation)
            
            await pipe.execute()
            logger.info(f"Сохранено {len(texts)} переводов в кэш")
        except Exception as e:
            logger.error(f"Ошибка сохранения батча в кэш: {e}")
    
    async def clear_cache(self):
        """Очищает весь кэш переводов"""
        if not self.redis:
            return
        
        try:
            keys = await self.redis.keys("translate:*")
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Очищено {len(keys)} записей из кэша")
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")
    
    async def get_cache_stats(self) -> dict:
        """Получает статистику кэша"""
        if not self.redis:
            return {"total_keys": 0, "memory_usage": 0}
        
        try:
            keys = await self.redis.keys("translate:*")
            info = await self.redis.info("memory")
            return {
                "total_keys": len(keys),
                "memory_usage": info.get("used_memory", 0)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики кэша: {e}")
            return {"total_keys": 0, "memory_usage": 0}
