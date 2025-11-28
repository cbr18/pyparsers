import asyncio
import logging
import os
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Используем API-based парсер вместо Playwright (быстрее и надёжнее)
from .detailed_parser_api import Che168DetailedParserAPI as Che168DetailedParser
from .models.detailed_car import Che168DetailedCar
from datetime import datetime, timezone
# Определение типа силовой установки перенесено в datahub

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


def _convert_to_domain_car(detailed_car: Che168DetailedCar, car_id: int) -> dict:
    """
    Преобразует Che168DetailedCar в формат domain.Car для Go API
    
    Args:
        detailed_car: Объект Che168DetailedCar
        car_id: ID машины
        
    Returns:
        Словарь в формате domain.Car
    """
    import re
    
    # Преобразуем пробег из строки в километры (int32)
    mileage_km = 0
    if detailed_car.mileage:
        mileage_str = str(detailed_car.mileage)
        num_match = re.search(r'[\d.]+', mileage_str)
        if num_match:
            try:
                num = float(num_match.group())
                if '万' in mileage_str:  # 万公里 = 10,000 км
                    mileage_km = int(num * 10000)
                else:
                    mileage_km = int(num)
            except (ValueError, TypeError):
                pass
    
    # Форматируем время в формате RFC3339
    try:
        # Python 3.2+
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (AttributeError, NameError):
        # Fallback для старых версий Python
        from datetime import timedelta
        utc_offset = timedelta(0)
        current_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Создаем словарь в формате domain.Car
    domain_car = {
        "source": "che168",
        "car_id": car_id,
        "sku_id": str(car_id),
        "title": detailed_car.title or "",
        "car_name": detailed_car.title or "",
        "year": detailed_car.year or 0,
        "mileage": mileage_km,
        "price": detailed_car.price or "",
        "rub_price": 0.0,
        "image": detailed_car.image or "",
        "link": f"https://m.che168.com/cardetail/index?infoid={car_id}",
        "brand_name": detailed_car.brand_name or "",
        "series_name": detailed_car.series_name or "",
        "city": detailed_car.city or "",
        "shop_id": "",
        "tags": "",
        "is_available": True,
        "sort_number": 0,
        "brand_id": 0,
        "series_id": 0,
        "car_source_city_name": detailed_car.city or "",
        "tags_v2": "",
        "description": detailed_car.description or "",
        "color": detailed_car.color or "",
        "transmission": detailed_car.transmission or "",
        "fuel_type": detailed_car.fuel_type or "",
        "engine_volume": detailed_car.engine_volume or "",
        "engine_volume_ml": detailed_car.engine_volume_ml or "",  # Объём двигателя в мл
        "body_type": detailed_car.body_type or "",
        "drive_type": detailed_car.drive_type or "",
        "condition": detailed_car.condition or "",
        "created_at": current_time,
        "updated_at": current_time,
        # Технические характеристики
        "power": None,
        "torque": detailed_car.torque or "",
        "acceleration": detailed_car.acceleration or "",
        "max_speed": detailed_car.max_speed or "",
        "fuel_consumption": detailed_car.fuel_consumption or "",
        "emission_standard": detailed_car.emission_standard or "",
        # Размеры и вес
        "length": detailed_car.length or "",
        "width": detailed_car.width or "",
        "height": detailed_car.height or "",
        "wheelbase": detailed_car.wheelbase or "",
        "curb_weight": detailed_car.curb_weight or "",
        "gross_weight": detailed_car.gross_weight or "",
        # Двигатель
        "engine_type": detailed_car.engine_type or "",
        "engine_code": detailed_car.engine_code or "",
        "cylinder_count": detailed_car.cylinder_count or "",
        "valve_count": detailed_car.valve_count or "",
        "compression_ratio": detailed_car.compression_ratio or "",
        "turbo_type": detailed_car.turbo_type or "",
        # Электрические характеристики
        "battery_capacity": detailed_car.battery_capacity or "",
        "electric_range": detailed_car.electric_range or "",
        "charging_time": detailed_car.charging_time or "",
        "fast_charge_time": detailed_car.fast_charge_time or "",
        "charge_port_type": detailed_car.charge_port_type or "",
        # Трансмиссия
        "transmission_type": detailed_car.transmission_type or "",
        "gear_count": detailed_car.gear_count or "",
        "differential_type": detailed_car.differential_type or "",
        # Подвеска и тормоза
        "front_suspension": detailed_car.front_suspension or "",
        "rear_suspension": detailed_car.rear_suspension or "",
        "front_brakes": detailed_car.front_brakes or "",
        "rear_brakes": detailed_car.rear_brakes or "",
        "brake_system": detailed_car.brake_system or "",
        # Колеса и шины
        "wheel_size": detailed_car.wheel_size or "",
        "tire_size": detailed_car.tire_size or "",
        "wheel_type": detailed_car.wheel_type or "",
        "tire_type": detailed_car.tire_type or "",
        # Безопасность
        "airbag_count": detailed_car.airbag_count or "",
        "abs": detailed_car.abs or "",
        "esp": detailed_car.esp or "",
        "tcs": detailed_car.tcs or "",
        "hill_assist": detailed_car.hill_assist or "",
        "blind_spot_monitor": detailed_car.blind_spot_monitor or "",
        "lane_departure": detailed_car.lane_departure or "",
        # Комфорт
        "air_conditioning": detailed_car.air_conditioning or "",
        "climate_control": detailed_car.climate_control or "",
        "seat_heating": detailed_car.seat_heating or "",
        "seat_ventilation": detailed_car.seat_ventilation or "",
        "seat_massage": detailed_car.seat_massage or "",
        "steering_wheel_heating": detailed_car.steering_wheel_heating or "",
        # Мультимедиа
        "navigation": detailed_car.navigation or "",
        "audio_system": detailed_car.audio_system or "",
        "speakers_count": detailed_car.speakers_count or "",
        "bluetooth": detailed_car.bluetooth or "",
        "usb": detailed_car.usb or "",
        "aux": detailed_car.aux or "",
        # Освещение
        "headlight_type": detailed_car.headlight_type or "",
        "fog_lights": detailed_car.fog_lights or "",
        "led_lights": detailed_car.led_lights or "",
        "daytime_running": detailed_car.daytime_running or "",
        # История
        "owner_count": detailed_car.owner_count or 0,
        "accident_history": detailed_car.accident_history or "",
        "service_history": detailed_car.service_history or "",
        "warranty_info": detailed_car.warranty_info or "",
        "inspection_date": detailed_car.inspection_date or "",
        "insurance_info": detailed_car.insurance_info or "",
        "first_registration_time": detailed_car.first_registration_time if detailed_car.first_registration_time else "",
        # Дополнительные детали
        "interior_color": detailed_car.interior_color or "",
        "exterior_color": detailed_car.exterior_color or "",
        "upholstery": detailed_car.upholstery or "",
        "sunroof": detailed_car.sunroof or "",
        "panoramic_roof": detailed_car.panoramic_roof or "",
        # Метаданные
        "view_count": detailed_car.view_count or 0,
        "favorite_count": detailed_car.favorite_count or 0,
        "contact_info": detailed_car.contact_info or "",
        "dealer_info": detailed_car.dealer_info or "",
        "certification": detailed_car.certification or "",
        # Изображения
        "image_gallery": detailed_car.image_gallery or "",
        "image_count": detailed_car.image_count or 0,
        # Дополнительные характеристики
        "seat_count": detailed_car.seat_count or "",
        "door_count": detailed_car.door_count or "",
        "trunk_volume": detailed_car.trunk_volume or "",
        "fuel_tank_volume": detailed_car.fuel_tank_volume or "",
    }
    
    # Проверяем валидность power - должны быть цифры
    power_value = detailed_car.power
    if power_value:
        power_str = str(power_value).strip()
        if power_str and any(c.isdigit() for c in power_str):
            domain_car["power"] = power_str
        else:
            logger.warning(f"Invalid power value '{power_str}' for car_id={car_id}, skipping")
            domain_car["power"] = None
    
    # Устанавливаем has_details только если power валиден
    # Тип силовой установки (электро/гибрид/ДВС) определяется в datahub
    if domain_car["power"]:
        domain_car["has_details"] = True
        domain_car["last_detail_update"] = current_time
        logger.info(f"car_id={car_id}: power found, has_details=True")
    else:
        domain_car["has_details"] = False
        domain_car["last_detail_update"] = None
        logger.info(f"car_id={car_id}: no power, has_details=False")
    
    return domain_car


async def _parse_car_details_async(car_id: int) -> Optional[Che168DetailedCar]:
    loop = asyncio.get_running_loop()

    def _work() -> Optional[Che168DetailedCar]:
        # API парсер не требует headless параметра
        parser = Che168DetailedParser()
        return parser.parse_car_details(car_id)

    return await loop.run_in_executor(None, _work)

class CarDetailRequest(BaseModel):
    car_id: int
    force_update: bool = False

class CarDetailResponse(BaseModel):
    success: bool
    car_id: int
    data: Optional[dict] = None  # Изменено на dict для совместимости с Go domain.Car
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
            logger.info(f"DEBUG: car_data.first_registration_time = '{car_data.first_registration_time}'")
            # Преобразуем в формат domain.Car для Go API
            domain_car_dict = _convert_to_domain_car(car_data, request.car_id)
            
            # Логируем количество заполненных полей для отладки
            filled_fields = {k: v for k, v in domain_car_dict.items() if v and v != "" and v != 0 and v != 0.0}
            logger.info(f"Преобразовано в domain.Car для car_id {request.car_id}: заполнено {len(filled_fields)} полей из {len(domain_car_dict)}")
            # Логируем названия заполненных полей (первые 20)
            filled_field_names = [k for k, v in filled_fields.items() if v]
            logger.debug(f"Заполненные поля для car_id {request.car_id}: {filled_field_names[:20]}")
            # Специально логируем first_registration_time - ВСЕГДА логируем
            first_reg_value = domain_car_dict.get('first_registration_time')
            logger.info(f"DEBUG first_registration_time для car_id {request.car_id}: значение='{first_reg_value}', тип={type(first_reg_value)}, в словаре={'first_registration_time' in domain_car_dict}")
            
            # Создаем объект, который Go сможет распарсить как domain.Car
            # Используем dict вместо Che168DetailedCar для совместимости
            return CarDetailResponse(
                success=True,
                car_id=request.car_id,
                data=domain_car_dict  # Теперь это dict в формате domain.Car
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
                        # Преобразуем в формат domain.Car для Go API
                        domain_car_dict = _convert_to_domain_car(car_data, car_id)
                        return CarDetailResponse(success=True, car_id=car_id, data=domain_car_dict)
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





