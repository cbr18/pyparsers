import asyncio
import logging
import os
from typing import Optional, List

from fastapi import APIRouter
from pydantic import BaseModel

from .detailed_parser import Che168DetailedParser
from .models.detailed_car import Che168DetailedCar

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/che168/detailed", tags=["che168-detailed"])


def _get_int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if not raw:
        return max(default, minimum)
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Некорректное значение %s=%s. Используется значение по умолчанию %s.", name, raw, default)
        return max(default, minimum)
    return max(value, minimum)


CHE168_BATCH_MAX_CONCURRENT = _get_int_env("CHE168_BATCH_MAX_CONCURRENT", 5)


async def _parse_car_details_async(car_id: int) -> Optional[Che168DetailedCar]:
    loop = asyncio.get_running_loop()

    def _work() -> Optional[Che168DetailedCar]:
        parser = Che168DetailedParser(headless=True)
        return parser.parse_car_details(car_id)

    return await loop.run_in_executor(None, _work)

class CarDetailRequest(BaseModel):
    car_id: int
    force_update: bool = False

class CarDetailResponse(BaseModel):
    success: bool
    car_id: int
    data: Optional[Che168DetailedCar] = None
    error: Optional[str] = None

class BatchDetailRequest(BaseModel):
    car_ids: List[int]
    force_update: bool = False

class BatchDetailResponse(BaseModel):
    success: bool
    processed: int
    successful: int
    failed: int
    results: List[CarDetailResponse]

@router.post("/parse", response_model=CarDetailResponse)
async def parse_car_details(request: CarDetailRequest):
    """
    Парсит детальную информацию о машине с che168.com
    
    Args:
        request: Запрос с car_id для парсинга
        
    Returns:
        CarDetailResponse с результатом парсинга
    """
    try:
        logger.info(f"Начало парсинга детальной информации для car_id: {request.car_id}")
        
        car_data = await _parse_car_details_async(request.car_id)
        
        if car_data:
            logger.info(f"Успешно получена детальная информация для car_id: {request.car_id}")
            return CarDetailResponse(
                success=True,
                car_id=request.car_id,
                data=car_data
            )
        else:
            logger.warning(f"Не удалось получить детальную информацию для car_id: {request.car_id}")
            return CarDetailResponse(
                success=False,
                car_id=request.car_id,
                error="Не удалось получить детальную информацию"
            )
            
    except Exception as e:
        logger.error(f"Ошибка парсинга car_id {request.car_id}: {e}")
        return CarDetailResponse(
            success=False,
            car_id=request.car_id,
            error=str(e)
        )

@router.post("/parse-batch", response_model=BatchDetailResponse)
async def parse_cars_details_batch(request: BatchDetailRequest):
    """
    Парсит детальную информацию для нескольких машин
    
    Args:
        request: Запрос с списком car_ids для парсинга
        
    Returns:
        BatchDetailResponse с результатами парсинга
    """
    try:
        logger.info(f"Начало пакетного парсинга для {len(request.car_ids)} машин")
        
        semaphore = asyncio.Semaphore(CHE168_BATCH_MAX_CONCURRENT)

        async def process_car(car_id: int) -> CarDetailResponse:
            async with semaphore:
                try:
                    car_data = await _parse_car_details_async(car_id)
                    if car_data:
                        return CarDetailResponse(success=True, car_id=car_id, data=car_data)
                    logger.warning(f"Не удалось получить детальную информацию для car_id: {car_id}")
                    return CarDetailResponse(success=False, car_id=car_id, error="Не удалось получить детальную информацию")
                except Exception as exc:
                    logger.error(f"Ошибка парсинга car_id {car_id}: {exc}")
                    return CarDetailResponse(success=False, car_id=car_id, error=str(exc))

        tasks = [asyncio.create_task(process_car(car_id)) for car_id in request.car_ids]
        results = await asyncio.gather(*tasks)

        successful = sum(1 for result in results if result.success)
        failed = len(results) - successful

        logger.info(f"Пакетный парсинг завершен: успешно {successful}, ошибок {failed}")

        return BatchDetailResponse(
            success=True,
            processed=len(request.car_ids),
            successful=successful,
            failed=failed,
            results=results,
        )
        
    except Exception as e:
        logger.error(f"Ошибка пакетного парсинга: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "che168-detailed-parser"}





