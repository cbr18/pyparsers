import asyncio
import aiohttp
import logging
import re
import gc
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from collections import OrderedDict
from threading import Lock as ThreadLock
from concurrent.futures import ThreadPoolExecutor
from models import Task, TaskStatus, TaskType
from api.dongchedi.parser import DongchediParser
from api.che168.parser import Che168Parser
from converters import decode_dongchedi_list_sh_price
from car_filter import filter_cars_by_year, is_electric_car
import uuid
from api.memory_optimized import MemoryOptimizedList

logger = logging.getLogger(__name__)
INCREMENTAL_EXISTING_LIMIT = int(os.getenv("INCREMENTAL_EXISTING_LIMIT", "15000"))
TASK_TTL_HOURS = int(os.getenv("TASK_TTL_HOURS", "24"))  # Задачи старше 24 часов удаляются
MAX_TASKS = int(os.getenv("MAX_TASKS", "1000"))  # Максимум задач в памяти

class TaskService:
    def __init__(self, datahub_url: Optional[str] = None, datahub_timeout: Optional[int] = None):
        env_datahub_url = os.getenv("DATAHUB_URL")
        env_datahub_timeout = os.getenv("DATAHUB_TIMEOUT")

        self.datahub_url = datahub_url or env_datahub_url or "http://localhost:8080"
        if datahub_timeout is not None:
            self.datahub_timeout = datahub_timeout
        elif env_datahub_timeout:
            try:
                self.datahub_timeout = int(env_datahub_timeout)
            except ValueError:
                logger.warning("Invalid DATAHUB_TIMEOUT value '%s', fallback to 1800 seconds", env_datahub_timeout)
                self.datahub_timeout = 1800
        else:
            self.datahub_timeout = 1800

        self._session_timeout = aiohttp.ClientTimeout(total=self.datahub_timeout)
        self.tasks: OrderedDict[str, Task] = OrderedDict()  # Используем OrderedDict для LRU
        self.session: Optional[aiohttp.ClientSession] = None
        self._source_locks: OrderedDict[str, asyncio.Lock] = OrderedDict()
        self._source_locks_max_size = 50  # Максимум 50 блокировок
        self._source_locks_lock = ThreadLock()
        # Executor для выполнения синхронных операций парсеров в отдельных потоках
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="parser")
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self._session_timeout)
        return self.session
    
    async def close_session(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def shutdown_executor(self):
        """Закрыть executor для парсеров"""
        if self._executor:
            self._executor.shutdown(wait=True)
    
    def create_task(self, source: str, task_type: TaskType = TaskType.FULL, id_field: Optional[str] = None, existing_ids: Optional[List[str]] = None) -> Task:
        """Создать новую задачу"""
        # Очищаем старые задачи перед созданием новой
        self._cleanup_old_tasks()
        
        # Если достигли лимита, удаляем самые старые задачи
        if len(self.tasks) >= MAX_TASKS:
            # Удаляем 10% самых старых задач
            to_remove = MAX_TASKS // 10
            for _ in range(to_remove):
                if self.tasks:
                    self.tasks.popitem(last=False)
        
        task_id = str(uuid.uuid4())
        now = datetime.now()
        
        task = Task(
            id=task_id,
            source=source,
            task_type=task_type,
            id_field=id_field,
            existing_ids=existing_ids,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now
        )
        
        self.tasks[task_id] = task
        # Перемещаем в конец (LRU)
        self.tasks.move_to_end(task_id)
        logger.info(f"Created task {task_id} for source {source}")
        return task
    
    def update_task_status(self, task_id: str, status: TaskStatus):
        """Обновить статус задачи"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.tasks[task_id].updated_at = datetime.now()
            # Перемещаем в конец (LRU)
            self.tasks.move_to_end(task_id)
            logger.info(f"Updated task {task_id} status to {status}")
    
    def _cleanup_old_tasks(self):
        """Удаляет задачи старше TTL"""
        now = datetime.now()
        cutoff_time = now - timedelta(hours=TASK_TTL_HOURS)
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if task.created_at < cutoff_time:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            logger.info(f"Removed old task {task_id} (older than {TASK_TTL_HOURS} hours)")
    
    def _get_source_lock(self, key: str) -> asyncio.Lock:
        with self._source_locks_lock:
            # Если блокировка уже существует, перемещаем её в конец (LRU)
            if key in self._source_locks:
                lock = self._source_locks.pop(key)
                self._source_locks[key] = lock
                return lock
            
            # Если достигли лимита, удаляем самую старую блокировку
            if len(self._source_locks) >= self._source_locks_max_size:
                self._source_locks.popitem(last=False)
            
            # Создаём новую блокировку
            lock = asyncio.Lock()
            self._source_locks[key] = lock
            return lock

    def _normalize_car_data(self, car_dict: dict, source: str) -> dict:
        """Нормализует данные машины для отправки в datahub"""
        normalized = {}
        
        # Обязательные поля
        if 'car_id' not in car_dict or car_dict['car_id'] is None:
            logger.warning(f"Missing car_id in car data, skipping normalization")
            return None
        
        normalized['car_id'] = int(car_dict['car_id'])
        normalized['source'] = source
        
        # year (int) - НЕ car_year!
        if 'year' in car_dict and car_dict['year'] is not None:
            try:
                normalized['year'] = int(car_dict['year'])
            except (ValueError, TypeError):
                pass
        
        # mileage (int32) - НЕ car_mileage строка!
        if 'mileage' in car_dict and car_dict['mileage'] is not None:
            try:
                normalized['mileage'] = int(car_dict['mileage'])
            except (ValueError, TypeError):
                pass
        
        # price (float64) - НЕ sh_price строка!
        if 'price' in car_dict and car_dict['price'] is not None:
            try:
                # Если price строка, преобразуем в float
                if isinstance(car_dict['price'], str):
                    normalized['price'] = float(car_dict['price'])
                else:
                    normalized['price'] = float(car_dict['price'])
            except (ValueError, TypeError):
                pass
        
        # shop_id (int32) - НЕ строка!
        if 'shop_id' in car_dict and car_dict['shop_id'] is not None:
            try:
                normalized['shop_id'] = int(car_dict['shop_id'])
            except (ValueError, TypeError):
                normalized['shop_id'] = 0
        else:
            normalized['shop_id'] = 0
        
        # is_available (bool) - НЕ null!
        if 'is_available' in car_dict:
            normalized['is_available'] = bool(car_dict['is_available']) if car_dict['is_available'] is not None else True
        else:
            normalized['is_available'] = True
        
        # Копируем остальные поля как есть
        for key, value in car_dict.items():
            if key not in normalized and key not in ['car_year', 'car_mileage', 'sh_price']:  # Удаляем лишние поля
                normalized[key] = value
        
        return normalized

    def _build_payload_bytes(self, task_id: str, source: str, task_type: TaskType, data: list) -> bytes:
        """Сериализует полезную нагрузку и освобождает исходные данные из памяти."""
        # Нормализуем данные перед отправкой
        normalized_data = []
        skipped_count = 0
        for car_dict in data:
            normalized = self._normalize_car_data(car_dict, source)
            if normalized:
                normalized_data.append(normalized)
            else:
                skipped_count += 1
        
        if skipped_count > 0:
            logger.warning(f"Skipped {skipped_count} cars due to missing car_id")
        
        # Логируем информацию о данных перед сериализацией
        if normalized_data and len(normalized_data) > 0:
            sample_car = normalized_data[0]
            logger.info(f"Building payload for task {task_id} (source={source}, type={task_type}): {len(normalized_data)} cars (skipped {skipped_count}), sample car keys: {list(sample_car.keys())[:20] if isinstance(sample_car, dict) else type(sample_car)}")
        
        payload = {
            "task_id": task_id,
            "source": source,
            "task_type": str(task_type.value) if isinstance(task_type, TaskType) else str(task_type),
            "status": "done",
            "data": normalized_data,
        }
        payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        logger.info(f"Payload size for task {task_id}: {len(payload_bytes)} bytes")
        if hasattr(data, "clear"):
            data.clear()
        gc.collect()
        return payload_bytes

    async def send_task_to_datahub(self, task_id: str, source: str, task_type: TaskType, status: str, data: list = None) -> bool:
        """Отправить задачу в datahub (при создании или обновлении статуса)"""
        try:
            session = await self.get_session()
            url = f"{self.datahub_url}/api/tasks/{task_id}/complete"
            headers = {"Content-Type": "application/json"}
            
            # Если данные не переданы, используем пустой массив
            if data is None:
                data = []
            
            payload = {
                "task_id": task_id,
                "source": source,
                "task_type": str(task_type.value) if isinstance(task_type, TaskType) else str(task_type),
                "status": status,
                "data": data,
            }
            payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            
            async with session.post(
                url,
                data=payload_bytes,
                headers=headers,
                timeout=self._session_timeout,
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent task {task_id} to datahub with status {status}")
                    return True
                else:
                    text = await response.text()
                    payload_preview = payload_bytes[:1000].decode('utf-8', errors='ignore') if len(payload_bytes) > 0 else "empty"
                    logger.error(f"Failed to send task {task_id} to datahub (source={source}, type={task_type}, status={status}): {response.status} body={text[:500]}")
                    logger.debug(f"Payload preview (first 1000 chars): {payload_preview}")
                    return False
                    
        except Exception as e:
            logger.exception(f"Error sending task {task_id} to datahub: {e}")
            return False

    async def send_to_datahub(self, task_id: str, source: str, task_type: TaskType, payload_bytes: bytes) -> bool:
        """Отправить сериализованные данные в datahub (legacy метод для обратной совместимости)"""
        try:
            session = await self.get_session()
            url = f"{self.datahub_url}/api/tasks/{task_id}/complete"
            headers = {"Content-Type": "application/json"}
            
            async with session.post(
                url,
                data=payload_bytes,
                headers=headers,
                timeout=self._session_timeout,
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent data to datahub for task {task_id}")
                    return True
                else:
                    text = await response.text()
                    # Логируем первые 1000 символов payload для отладки
                    payload_preview = payload_bytes[:1000].decode('utf-8', errors='ignore') if len(payload_bytes) > 0 else "empty"
                    logger.error(f"Failed to send data to datahub for task {task_id} (source={source}, type={task_type}): {response.status} body={text[:500]}")
                    logger.debug(f"Payload preview (first 1000 chars): {payload_preview}")
                    return False
                    
        except Exception as e:
            logger.exception(f"Error sending data to datahub for task {task_id}: {e}")
            return False
    
    async def retry_send_to_datahub(self, task_id: str, source: str, task_type: TaskType, payload_bytes: bytes):
        """Повторять отправку в datahub каждые 30 секунд до успеха"""
        while True:
            success = await self.send_to_datahub(task_id, source, task_type, payload_bytes)
            if success:
                # Обновляем статус задачи на DONE после успешной отправки
                if task_id in self.tasks:
                    self.update_task_status(task_id, TaskStatus.DONE)
                # Удаляем данные из памяти после успешной отправки
                if task_id in self.tasks:
                    del self.tasks[task_id]
                payload_bytes = b""  # Освобождаем ссылку
                del payload_bytes  # Явно удаляем
                gc.collect()
                break
            
            logger.info(f"Retrying send to datahub for task {task_id} in 30 seconds...")
            await asyncio.sleep(30)
    
    async def process_task(self, task_id: str):
        """Обработать задачу парсинга"""
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found")
            return
        
        task = self.tasks[task_id]
        
        # Отправляем задачу в datahub со статусом "pending" при создании
        await self.send_task_to_datahub(task_id, task.source, task.task_type, "pending", [])
        
        # Обновляем статус на IN_PROGRESS и отправляем в datahub
        self.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        await self.send_task_to_datahub(task_id, task.source, task.task_type, "in_progress", [])
        
        try:
            data = []
            
            # Обработка по типу задачи
            if task.source == "dongchedi":
                if task.task_type == TaskType.FULL:
                    data = await self._parse_dongchedi_full()
                else:
                    data = await self._parse_dongchedi_incremental(task.existing_ids or [], task.id_field or "sku_id")
            elif task.source == "che168":
                if task.task_type == TaskType.FULL:
                    data = await self._parse_che168_full()
                else:
                    data = await self._parse_che168_incremental(task.existing_ids or [], task.id_field or "car_id")
            else:
                logger.error(f"Unknown source: {task.source}")
                self.update_task_status(task_id, TaskStatus.FAILED)
                # Отправляем задачу как failed в datahub
                await self.send_task_to_datahub(task_id, task.source, task.task_type, "failed", [])
                return
            
            # Уникальность по car_id
            ids = [d.get('car_id') for d in data]
            unique_ids = set(ids)
            dup_count = len(ids) - len(unique_ids)
            logger.info(f"Collected {len(data)} cars for source {task.source} (task {task_id}); unique car_id={len(unique_ids)}, duplicates={dup_count}")

            if data:
                # Отправляем задачу как выполненную с данными
                payload_bytes = self._build_payload_bytes(task_id, task.source, task.task_type, data)
                asyncio.create_task(self.retry_send_to_datahub(task_id, task.source, task.task_type, payload_bytes))
                # Пока отправляем, держим задачу IN_PROGRESS; DONE поставит отправка при очистке
                return
            else:
                logger.warning(f"No data collected for task {task_id} source {task.source}")
                self.update_task_status(task_id, TaskStatus.FAILED)
                # Отправляем задачу как failed в datahub
                await self.send_task_to_datahub(task_id, task.source, task.task_type, "failed", [])
                
        except Exception as e:
            logger.exception(f"Error processing task {task_id}: {e}")
            self.update_task_status(task_id, TaskStatus.FAILED)
            # Отправляем задачу как failed в datahub
            await self.send_task_to_datahub(task_id, task.source, task.task_type, "failed", [])
    
    async def _parse_dongchedi_full(self) -> list:
        """Полный парсинг dongchedi (все страницы) с защитой от параллельных запусков"""
        lock = self._get_source_lock("dongchedi_full")
        async with lock:
            return await self._parse_dongchedi_full_unlocked()

    async def _parse_dongchedi_full_unlocked(self) -> list:
        """Внутренняя реализация полного парсинга dongchedi"""
        try:
            parser = DongchediParser()
            # Собираем все страницы
            all_data = MemoryOptimizedList()
            page = 1
            loop = asyncio.get_event_loop()
            while True:
                # Выполняем синхронный вызов парсера в отдельном потоке, чтобы не блокировать event loop
                response = await loop.run_in_executor(self._executor, parser.fetch_cars_by_page, page)
                if not response.data or not response.data.search_sh_sku_info_list:
                    if response.status != 200:
                        logger.warning(f"Dongchedi API returned status {response.status} for page {page}: {response.message}")
                    else:
                        logger.info(f"No more data available for dongchedi page {page}")
                    break
                cars_list = response.data.search_sh_sku_info_list
                filtered_cars = filter_cars_by_year(cars_list, min_year=2017)
                for i, car in enumerate(filtered_cars):
                    car_dict = car.dict()
                    car_dict.update({
                        'sort_number': len(filtered_cars) - i,
                        'source': 'dongchedi'
                    })
                    if car_dict.get('sh_price'):
                        car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
                    if 'car_id' in car_dict and car_dict['car_id'] is not None:
                        try:
                            car_dict['car_id'] = int(car_dict['car_id'])
                        except (ValueError, TypeError):
                            car_dict['car_id'] = 0
                    # Тип силовой установки определяется в datahub
                    all_data.append(car_dict)
                if not getattr(response.data, 'has_more', False):
                    break
                page += 1
            return all_data
        except Exception as e:
            logger.error(f"Error parsing dongchedi: {e}")
            return []
    
    async def _parse_dongchedi_incremental(self, existing_ids: List[str], id_field: str) -> list:
        """Инкрементальный парсинг dongchedi (первые страницы до первого совпадения)"""
        try:
            parser = DongchediParser()
            data = MemoryOptimizedList()
            limited_existing_ids = (str(x) for idx, x in enumerate(existing_ids) if x and idx < INCREMENTAL_EXISTING_LIMIT)
            existing_set = set(limited_existing_ids)
            del limited_existing_ids  # Освобождаем генератор

            loop = asyncio.get_event_loop()
            for page in range(1, 101):
                # Выполняем синхронный вызов парсера в отдельном потоке
                response = await loop.run_in_executor(self._executor, parser.fetch_cars_by_page, page)
                if not response.data or not response.data.search_sh_sku_info_list:
                    break
                cars_list = response.data.search_sh_sku_info_list
                filtered_cars = filter_cars_by_year(cars_list, min_year=2017)
                found_existing = False
                for i, car in enumerate(filtered_cars):
                    car_dict = car.dict()
                    # Остановка при первом совпадении по нужному полю
                    key_val = car_dict.get(id_field)
                    key_val = str(key_val) if key_val is not None else None
                    if key_val and key_val in existing_set:
                        found_existing = True
                        break
                    car_dict.update({
                        'sort_number': len(filtered_cars) - i,
                        'source': 'dongchedi'
                    })
                    if car_dict.get('sh_price'):
                        car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
                    if 'car_id' in car_dict and car_dict['car_id'] is not None:
                        try:
                            car_dict['car_id'] = int(car_dict['car_id'])
                        except (ValueError, TypeError):
                            car_dict['car_id'] = 0
                    # Тип силовой установки определяется в datahub
                    data.append(car_dict)
                if found_existing:
                    break
                if not getattr(response.data, 'has_more', False):
                    break
            # Очищаем existing_set для освобождения памяти
            existing_set.clear()
            del existing_set
            gc.collect()
            return data
        except Exception as e:
            logger.error(f"Error parsing dongchedi incremental: {e}")
            return []

    async def _parse_che168_full(self) -> list:
        """Полный парсинг che168 (все страницы до 100) с защитой от параллельных запусков"""
        lock = self._get_source_lock("che168_full")
        async with lock:
            return await self._parse_che168_full_unlocked()

    async def _parse_che168_full_unlocked(self) -> list:
        """Внутренняя реализация полного парсинга che168"""
        try:
            parser = Che168Parser()
            data = MemoryOptimizedList()
            missing_id_count = 0
            filtered_by_year = 0
            empty_pages_count = 0  # Счетчик подряд идущих пустых страниц
            max_empty_pages = 3  # Останавливаемся после 3 подряд идущих пустых страниц
            loop = asyncio.get_event_loop()
            # Собираем страницы 1..100 или до конца
            for page in range(1, 101):
                # Выполняем синхронный вызов парсера в отдельном потоке, чтобы не блокировать event loop
                response = await loop.run_in_executor(self._executor, parser.fetch_cars_by_page, page)
                if not response.data or not response.data.search_sh_sku_info_list:
                    empty_pages_count += 1
                    logger.warning(f"che168 page {page}: пустая страница (статус: {response.status}, сообщение: {response.message})")
                    if empty_pages_count >= max_empty_pages:
                        logger.info(f"che168: остановка парсинга после {empty_pages_count} подряд идущих пустых страниц")
                        break
                    continue  # Пропускаем пустую страницу, но продолжаем парсинг
                
                # Если страница не пустая, сбрасываем счетчик пустых страниц
                empty_pages_count = 0
                cars_list = response.data.search_sh_sku_info_list
                logger.info(f"che168 page {page}: processing {len(cars_list)} cars")
                
                for i, car in enumerate(cars_list):
                    car_dict = car.dict(exclude_none=False)
                    # Нормализуем ссылку: всегда используем формат как в details
                    # https://m.che168.com/cardetail/index?infoid={car_id}
                    car_id = car_dict.get('car_id')
                    existing_link = car_dict.get('link', '')
                    
                    if car_id:
                        # Если есть car_id, всегда используем его для формирования ссылки
                        car_dict['link'] = f'https://m.che168.com/cardetail/index?infoid={car_id}'
                    elif existing_link:
                        # Если нет car_id, но есть ссылка, пытаемся извлечь car_id из ссылки
                        match = re.search(r'/(\d+)\.html|infoid=(\d+)', existing_link)
                        if match:
                            extracted_id = match.group(1) or match.group(2)
                            car_dict['link'] = f'https://m.che168.com/cardetail/index?infoid={extracted_id}'
                    # Если нет ни car_id, ни link, оставляем как есть (будет None или пустая строка)
                    car_dict.update({
                        'sort_number': len(cars_list) - i,
                        'source': 'che168'
                    })
                    # price должен быть float64, не строка!
                    if car_dict.get('sh_price') is not None and car_dict.get('sh_price') != '':
                        try:
                            price_str = str(car_dict['sh_price']).strip()
                            car_dict['price'] = float(price_str)
                        except (ValueError, TypeError):
                            pass
                    year_val = car_dict.get('car_year')
                    if year_val is not None:
                        try:
                            car_dict['year'] = int(year_val)
                        except (ValueError, TypeError):
                            car_dict['year'] = None
                    if car_dict.get('year') in (None, 0):
                        title_text = car_dict.get('title') or ''
                        m = re.search(r'(19|20)\d{2}', title_text)
                        if m:
                            try:
                                y = int(m.group(0))
                                if 1990 <= y <= 2030:
                                    car_dict['year'] = y
                            except Exception:
                                pass
                    
                    # Логируем фильтрацию по году
                    if car_dict.get('year') is not None and car_dict.get('year') < 2017:
                        filtered_by_year += 1
                        logger.debug(f"che168: filtered car {car_dict.get('car_id')} - year {car_dict.get('year')} < 2017")
                        continue  # Пропускаем машины старше 2017
                    
                    if car_dict.get('car_source_city_name'):
                        car_dict['city'] = car_dict.get('car_source_city_name')
                    # Тип силовой установки определяется в datahub
                    mileage_raw = car_dict.get('car_mileage')
                    if isinstance(mileage_raw, str) and mileage_raw.strip() != '':
                        text = mileage_raw.strip()
                        num_match = re.search(r"[0-9]+(?:\.[0-9]+)?", text)
                        if num_match:
                            num_str = num_match.group(0)
                            try:
                                if '万' in text:
                                    km_val = int(float(num_str) * 10000.0)
                                else:
                                    km_val = int(float(num_str))
                                if km_val >= 0:
                                    car_dict['mileage'] = km_val
                            except Exception:
                                pass
                    try:
                        if 'car_id' in car_dict and car_dict['car_id'] is not None:
                            car_dict['car_id'] = int(car_dict['car_id'])
                        else:
                            raise ValueError('missing car_id')
                    except Exception:
                        missing_id_count += 1
                        link = car_dict.get('link') or ''
                        import hashlib
                        h = hashlib.md5(link.encode('utf-8')).digest()
                        car_dict['car_id'] = int.from_bytes(h[:8], byteorder='big', signed=False)
                    data.append(car_dict)
                if not getattr(response.data, 'has_more', False):
                    break
            
            logger.info(f"che168 full parsing: {len(data)} cars collected, {filtered_by_year} filtered by year < 2017, {missing_id_count} had no car_id")
            if missing_id_count:
                logger.info(f"che168: {missing_id_count} cars had no car_id; generated from link hash")
            return data
            
        except Exception as e:
            logger.error(f"Error parsing che168 full: {e}")
            return []

    async def _parse_che168_incremental(self, existing_ids: List[str], id_field: str) -> list:
        """Инкрементальный парсинг che168 (первые страницы)"""
        try:
            parser = Che168Parser()
            data = MemoryOptimizedList()
            missing_id_count = 0
            filtered_by_year = 0
            limited_existing_ids = (str(x) for idx, x in enumerate(existing_ids) if x and idx < INCREMENTAL_EXISTING_LIMIT)
            existing_set = set(limited_existing_ids)
            del limited_existing_ids  # Освобождаем генератор
            logger.info(f"che168 incremental: checking against {len(existing_set)} existing IDs")

            loop = asyncio.get_event_loop()
            for page in range(1, 101):
                # Выполняем синхронный вызов парсера в отдельном потоке
                response = await loop.run_in_executor(self._executor, parser.fetch_cars_by_page, page)
                if not response.data or not response.data.search_sh_sku_info_list:
                    break
                cars_list = response.data.search_sh_sku_info_list
                logger.info(f"che168 incremental page {page}: processing {len(cars_list)} cars")
                found_existing = False
                for i, car in enumerate(cars_list):
                    car_dict = car.dict(exclude_none=False)
                    # Убеждаемся, что link всегда есть, формируем на основе car_id если нужно
                    if not car_dict.get('link') and car_dict.get('car_id'):
                        car_dict['link'] = f'https://m.che168.com/cardetail/index?infoid={car_dict["car_id"]}'
                    # Остановка при первом совпадении по нужному полю
                    stop_id = car_dict.get(id_field)
                    if stop_id is not None:
                        try:
                            stop_id = str(int(stop_id)) if isinstance(stop_id, (int, float, str)) else str(stop_id)
                        except Exception:
                            stop_id = str(stop_id)
                    if stop_id and stop_id in existing_set:
                        found_existing = True
                        logger.info(f"che168 incremental: found existing car {stop_id} on page {page}, stopping")
                        break
                    car_dict.update({
                        'sort_number': len(cars_list) - i,
                        'source': 'che168'
                    })
                    # price должен быть float64, не строка!
                    if car_dict.get('sh_price') is not None and car_dict.get('sh_price') != '':
                        try:
                            price_str = str(car_dict['sh_price']).strip()
                            car_dict['price'] = float(price_str)
                        except (ValueError, TypeError):
                            pass
                    year_val = car_dict.get('car_year')
                    if year_val is not None:
                        try:
                            car_dict['year'] = int(year_val)
                        except (ValueError, TypeError):
                            car_dict['year'] = None
                    if car_dict.get('year') in (None, 0):
                        title_text = car_dict.get('title') or ''
                        m = re.search(r'(19|20)\d{2}', title_text)
                        if m:
                            try:
                                y = int(m.group(0))
                                if 1990 <= y <= 2030:
                                    car_dict['year'] = y
                            except Exception:
                                pass
                    
                    # Логируем фильтрацию по году
                    if car_dict.get('year') is not None and car_dict.get('year') < 2017:
                        filtered_by_year += 1
                        logger.debug(f"che168 incremental: filtered car {car_dict.get('car_id')} - year {car_dict.get('year')} < 2017")
                        continue  # Пропускаем машины старше 2017
                    
                    if car_dict.get('car_source_city_name'):
                        car_dict['city'] = car_dict.get('car_source_city_name')
                    mileage_raw = car_dict.get('car_mileage')
                    if isinstance(mileage_raw, str) and mileage_raw.strip() != '':
                        text = mileage_raw.strip()
                        num_match = re.search(r"[0-9]+(?:\.[0-9]+)?", text)
                        if num_match:
                            num_str = num_match.group(0)
                            try:
                                if '万' in text:
                                    km_val = int(float(num_str) * 10000.0)
                                else:
                                    km_val = int(float(num_str))
                                if km_val >= 0:
                                    car_dict['mileage'] = km_val
                            except Exception:
                                pass
                    try:
                        if 'car_id' in car_dict and car_dict['car_id'] is not None:
                            car_dict['car_id'] = int(car_dict['car_id'])
                        else:
                            raise ValueError('missing car_id')
                    except Exception:
                        missing_id_count += 1
                        link = car_dict.get('link') or ''
                        import hashlib
                        h = hashlib.md5(link.encode('utf-8')).digest()
                        car_dict['car_id'] = int.from_bytes(h[:8], byteorder='big', signed=False)
                    data.append(car_dict)
                if found_existing:
                    break
            
            logger.info(f"che168 incremental: {len(data)} cars collected, {filtered_by_year} filtered by year < 2017, {missing_id_count} had no car_id")
            if missing_id_count:
                logger.info(f"che168: {missing_id_count} cars had no car_id; generated from link hash")
            # Очищаем existing_set для освобождения памяти
            existing_set.clear()
            del existing_set
            gc.collect()
            return data
        except Exception as e:
            logger.error(f"Error parsing che168 incremental: {e}")
            return []

# Глобальный экземпляр сервиса
task_service = TaskService()

