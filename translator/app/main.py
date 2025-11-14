"""
Основной файл FastAPI приложения для сервиса перевода
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .api.translate import router as translate_router
from .services.translator import TranslatorService
from .services.cache import CacheService

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные переменные для сервисов
translator_service: TranslatorService = None
cache_service: CacheService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    """
    global translator_service, cache_service
    
    # Инициализация при запуске
    logger.info("Инициализация сервиса перевода...")
    
    try:
        # Получаем конфигурацию из переменных окружения
        api_key = os.getenv("YANDEX_API_KEY")
        folder_id = os.getenv("YANDEX_FOLDER_ID")
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = os.getenv("REDIS_PORT", "6379")
        max_concurrent_env = os.getenv("TRANSLATOR_MAX_CONCURRENT_BATCHES")
        try:
            max_concurrent_batches = int(max_concurrent_env) if max_concurrent_env else 3
        except (TypeError, ValueError):
            logger.warning(
                "Некорректное значение TRANSLATOR_MAX_CONCURRENT_BATCHES: %s. Используется значение по умолчанию.",
                max_concurrent_env,
            )
            max_concurrent_batches = 3
        
        if not api_key or not folder_id:
            raise ValueError("Не указаны YANDEX_API_KEY или YANDEX_FOLDER_ID в переменных окружения")
        
        # Инициализируем сервис кэша
        cache_service = CacheService(f"redis://{redis_host}:{redis_port}")
        await cache_service.connect()
        
        # Инициализируем сервис переводчика
        translator_service = TranslatorService(
            api_key,
            folder_id,
            cache_service,
            max_concurrent_batches=max_concurrent_batches,
        )
        
        # Сервисы доступны через глобальные переменные модуля
        
        logger.info("Сервис перевода успешно инициализирован")
        
    except Exception as e:
        logger.error(f"Ошибка инициализации сервиса: {e}")
        raise
    
    yield
    
    # Очистка при завершении
    logger.info("Завершение работы сервиса перевода...")
    
    if cache_service:
        await cache_service.disconnect()
    
    logger.info("Сервис перевода завершен")


# Создаем FastAPI приложение
app = FastAPI(
    title="Translator Service",
    description="Асинхронный сервис перевода автомобильных данных с кэшированием в Redis",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(translate_router)


@app.get("/")
async def root():
    """
    Корневой эндпоинт
    """
    return {
        "message": "Translator Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "translate_text": "POST /translate/text",
            "translate_json": "POST /translate/json", 
            "translate_database": "POST /translate/db",
            "health_check": "GET /translate/health",
            "stats": "GET /translate/stats",
            "clear_cache": "POST /translate/cache/clear"
        }
    }


@app.get("/health")
@app.head("/health")
async def health():
    """
    Проверка здоровья приложения
    """
    return {
        "data": {
            "status": "ok",
            "service": "translator",
            "version": "1.0.0",
            "cache_connected": cache_service is not None and cache_service.is_connected() if cache_service else False
        },
        "message": "Service is healthy",
        "status": 200
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
