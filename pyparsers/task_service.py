import asyncio
import aiohttp
import logging
import re
from datetime import datetime
from typing import Dict, Optional, List
from models import Task, TaskStatus, TaskCompleteRequest, TaskType
from api.dongchedi.parser import DongchediParser
from api.che168.parser import Che168Parser
from converters import decode_dongchedi_list_sh_price
from car_filter import filter_cars_by_year
import uuid

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self, datahub_url: str = "http://datahub:8080"):
        self.datahub_url = datahub_url
        self.tasks: Dict[str, Task] = {}
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Получить или создать HTTP сессию"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close_session(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def create_task(self, source: str, task_type: TaskType = TaskType.FULL, id_field: Optional[str] = None, existing_ids: Optional[List[str]] = None) -> Task:
        """Создать новую задачу"""
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
        logger.info(f"Created task {task_id} for source {source}")
        return task
    
    def update_task_status(self, task_id: str, status: TaskStatus):
        """Обновить статус задачи"""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.tasks[task_id].updated_at = datetime.now()
            logger.info(f"Updated task {task_id} status to {status}")
    
    async def send_to_datahub(self, task_id: str, source: str, task_type: TaskType, data: list) -> bool:
        """Отправить данные в datahub"""
        try:
            session = await self.get_session()
            url = f"{self.datahub_url}/api/tasks/{task_id}/complete"
            logger.info(f"POST to datahub: {url} with {len(data)} items")
            
            payload = {
                "task_id": task_id,
                "source": source,
                "task_type": task_type,
                "status": "done",
                "data": data
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent data to datahub for task {task_id}")
                    return True
                else:
                    text = await response.text()
                    logger.error(f"Failed to send data to datahub for task {task_id}: {response.status} body={text[:500]}")
                    return False
                    
        except Exception as e:
            logger.exception(f"Error sending data to datahub for task {task_id}: {e}")
            return False
    
    async def retry_send_to_datahub(self, task_id: str, source: str, task_type: TaskType, data: list):
        """Повторять отправку в datahub каждые 30 секунд до успеха"""
        while True:
            success = await self.send_to_datahub(task_id, source, task_type, data)
            if success:
                # Удаляем данные из памяти после успешной отправки
                if task_id in self.tasks:
                    del self.tasks[task_id]
                break
            
            logger.info(f"Retrying send to datahub for task {task_id} in 30 seconds...")
            await asyncio.sleep(30)
    
    async def process_task(self, task_id: str):
        """Обработать задачу парсинга"""
        if task_id not in self.tasks:
            logger.error(f"Task {task_id} not found")
            return
        
        task = self.tasks[task_id]
        self.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        
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
                return
            
            # Уникальность по car_id
            ids = [d.get('car_id') for d in data]
            unique_ids = set(ids)
            dup_count = len(ids) - len(unique_ids)
            logger.info(f"Collected {len(data)} cars for source {task.source} (task {task_id}); unique car_id={len(unique_ids)}, duplicates={dup_count}")

            if data:
                # Запускаем отправку в фоне с повторными попытками
                asyncio.create_task(self.retry_send_to_datahub(task_id, task.source, task.task_type, data))
                # Пока отправляем, держим задачу IN_PROGRESS; DONE поставит отправка при очистке
                return
            else:
                logger.warning(f"No data collected for task {task_id} source {task.source}")
                self.update_task_status(task_id, TaskStatus.FAILED)
                
        except Exception as e:
            logger.exception(f"Error processing task {task_id}: {e}")
            self.update_task_status(task_id, TaskStatus.FAILED)
    
    async def _parse_dongchedi_full(self) -> list:
        """Полный парсинг dongchedi (все страницы)"""
        try:
            parser = DongchediParser()
            # Собираем все страницы
            all_data = []
            page = 1
            while True:
                response = parser.fetch_cars_by_page(page)
                if not response.data or not response.data.search_sh_sku_info_list:
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
                    all_data.append(car_dict)
                if not getattr(response.data, 'has_more', False):
                    break
                page += 1
            return all_data
            
            if not response.data or not response.data.search_sh_sku_info_list:
                return []
            
            cars_list = response.data.search_sh_sku_info_list
            filtered_cars = filter_cars_by_year(cars_list, min_year=2017)
            
            data = []
            for i, car in enumerate(filtered_cars):
                car_dict = car.dict()
                
                # Добавляем метаданные
                car_dict.update({
                    'sort_number': len(filtered_cars) - i,
                    'source': 'dongchedi'
                })
                
                # Декодируем цену
                if car_dict.get('sh_price'):
                    car_dict['sh_price'] = decode_dongchedi_list_sh_price(car_dict['sh_price'])
                
                # Преобразуем car_id в int64
                if 'car_id' in car_dict and car_dict['car_id'] is not None:
                    try:
                        car_dict['car_id'] = int(car_dict['car_id'])
                    except (ValueError, TypeError):
                        car_dict['car_id'] = 0
                
                data.append(car_dict)
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing dongchedi: {e}")
            return []
    
    async def _parse_dongchedi_incremental(self, existing_ids: List[str], id_field: str) -> list:
        """Инкрементальный парсинг dongchedi (первые страницы до первого совпадения)"""
        try:
            parser = DongchediParser()
            data = []
            existing_set = set(str(x) for x in existing_ids if x)

            for page in range(1, 101):
                response = parser.fetch_cars_by_page(page)
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
                    data.append(car_dict)
                if found_existing:
                    break
                if not getattr(response.data, 'has_more', False):
                    break
            return data
        except Exception as e:
            logger.error(f"Error parsing dongchedi incremental: {e}")
            return []

    async def _parse_che168_full(self) -> list:
        """Полный парсинг che168 (все страницы до 100)"""
        try:
            parser = Che168Parser()
            data = []
            missing_id_count = 0
            # Собираем страницы 1..100 или до конца
            for page in range(1, 101):
                response = parser.fetch_cars_by_page(page)
                if not response.data or not response.data.search_sh_sku_info_list:
                    break
                cars_list = response.data.search_sh_sku_info_list
                for i, car in enumerate(cars_list):
                    car_dict = car.dict()
                    car_dict.update({
                        'sort_number': len(cars_list) - i,
                        'source': 'che168'
                    })
                    if car_dict.get('sh_price') is not None and car_dict.get('sh_price') != '':
                        car_dict['price'] = str(car_dict['sh_price'])
                    year_val = car_dict.get('car_year')
                    if year_val is not None:
                        try:
                            car_dict['year'] = int(year_val)
                        except (ValueError, TypeError):
                            car_dict['year'] = None
                    if car_dict.get('year') in (None, 0):
                        title_text = car_dict.get('title') or ''
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
                if not getattr(response.data, 'has_more', False):
                    break
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
            data = []
            missing_id_count = 0
            existing_set = set(str(x) for x in existing_ids if x)

            for page in range(1, 101):
                response = parser.fetch_cars_by_page(page)
                if not response.data or not response.data.search_sh_sku_info_list:
                    break
                cars_list = response.data.search_sh_sku_info_list
                found_existing = False
                for i, car in enumerate(cars_list):
                    car_dict = car.dict()
                    # Остановка при первом совпадении по нужному полю
                    stop_id = car_dict.get(id_field)
                    if stop_id is not None:
                        try:
                            stop_id = str(int(stop_id)) if isinstance(stop_id, (int, float, str)) else str(stop_id)
                        except Exception:
                            stop_id = str(stop_id)
                    if stop_id and stop_id in existing_set:
                        found_existing = True
                        break
                    car_dict.update({
                        'sort_number': len(cars_list) - i,
                        'source': 'che168'
                    })
                    if car_dict.get('sh_price') is not None and car_dict.get('sh_price') != '':
                        car_dict['price'] = str(car_dict['sh_price'])
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
            if missing_id_count:
                logger.info(f"che168: {missing_id_count} cars had no car_id; generated from link hash")
            return data
        except Exception as e:
            logger.error(f"Error parsing che168 incremental: {e}")
            return []

# Глобальный экземпляр сервиса
task_service = TaskService()

