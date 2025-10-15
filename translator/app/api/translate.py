"""
API эндпоинты для сервиса перевода
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..services.translator import TranslatorService
from ..services.cache import CacheService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translate", tags=["translate"])

def get_translator_service() -> TranslatorService:
    """Dependency для получения сервиса переводчика"""
    from ..main import translator_service
    if translator_service is None:
        raise HTTPException(status_code=500, detail="Сервис переводчика не инициализирован")
    return translator_service


def get_cache_service() -> CacheService:
    """Dependency для получения сервиса кэша"""
    from ..main import cache_service
    if cache_service is None:
        raise HTTPException(status_code=500, detail="Сервис кэша не инициализирован")
    return cache_service


class TextTranslateRequest(BaseModel):
    """Запрос на перевод текста"""
    text: str
    source_lang: str = "zh"
    target_lang: str = "ru"


class TextTranslateResponse(BaseModel):
    """Ответ с переводом текста"""
    original_text: str
    translated_text: str
    source_lang: str
    target_lang: str


class JsonTranslateRequest(BaseModel):
    """Запрос на перевод JSON"""
    data: Dict[str, Any]
    source_lang: str = "zh"
    target_lang: str = "ru"


class JsonTranslateResponse(BaseModel):
    """Ответ с переводом JSON"""
    original_data: Dict[str, Any]
    translated_data: Dict[str, Any]
    source_lang: str
    target_lang: str


class DatabaseTranslateRequest(BaseModel):
    """Запрос на перевод базы данных"""
    records: List[Dict[str, Any]]
    source_lang: str = "zh"
    target_lang: str = "ru"


class DatabaseTranslateResponse(BaseModel):
    """Ответ с переводом базы данных"""
    total_records: int
    translated_records: List[Dict[str, Any]]
    source_lang: str
    target_lang: str


@router.post("/text", response_model=TextTranslateResponse)
async def translate_text(
    request: TextTranslateRequest,
    translator: TranslatorService = Depends(get_translator_service)
):
    """
    Переводит одиночный текст
    """
    try:
        logger.info(f"Запрос на перевод текста: {request.text[:50]}...")
        
        translated_text = await translator.translate_text(
            request.text, 
            request.source_lang, 
            request.target_lang
        )
        
        logger.info(f"Текст успешно переведен")
        
        return TextTranslateResponse(
            original_text=request.text,
            translated_text=translated_text,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
    except Exception as e:
        logger.error(f"Ошибка перевода текста: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка перевода: {str(e)}")


@router.post("/json", response_model=JsonTranslateResponse)
async def translate_json(
    request: JsonTranslateRequest,
    translator: TranslatorService = Depends(get_translator_service)
):
    """
    Переводит все строковые значения в JSON объекте
    """
    try:
        logger.info(f"Запрос на перевод JSON с {len(request.data)} полями")
        
        translated_data = await translator.translate_json(
            request.data,
            request.source_lang,
            request.target_lang
        )
        
        logger.info(f"JSON успешно переведен")
        
        return JsonTranslateResponse(
            original_data=request.data,
            translated_data=translated_data,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
    except Exception as e:
        logger.error(f"Ошибка перевода JSON: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка перевода: {str(e)}")


@router.post("/db", response_model=DatabaseTranslateResponse)
async def translate_database(
    request: DatabaseTranslateRequest,
    translator: TranslatorService = Depends(get_translator_service)
):
    """
    Переводит батч записей из базы данных
    """
    try:
        logger.info(f"Запрос на перевод базы данных: {len(request.records)} записей")
        
        translated_records = await translator.translate_database_batch(
            request.records,
            request.source_lang,
            request.target_lang
        )
        
        logger.info(f"База данных успешно переведена: {len(translated_records)} записей")
        
        return DatabaseTranslateResponse(
            total_records=len(request.records),
            translated_records=translated_records,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
    except Exception as e:
        logger.error(f"Ошибка перевода базы данных: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка перевода: {str(e)}")


@router.get("/stats")
async def get_translation_stats(
    translator: TranslatorService = Depends(get_translator_service)
):
    """
    Получает статистику переводов
    """
    try:
        stats = await translator.get_translation_stats()
        return stats
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


@router.post("/cache/clear")
async def clear_cache(
    cache: CacheService = Depends(get_cache_service)
):
    """
    Очищает кэш переводов
    """
    try:
        await cache.clear_cache()
        return {"message": "Кэш успешно очищен"}
    except Exception as e:
        logger.error(f"Ошибка очистки кэша: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка очистки кэша: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats(
    cache: CacheService = Depends(get_cache_service)
):
    """
    Получает статистику кэша
    """
    try:
        stats = await cache.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Ошибка получения статистики кэша: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики кэша: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Проверка здоровья сервиса
    """
    return {
        "status": "healthy",
        "service": "translator",
        "version": "1.0.0"
    }
