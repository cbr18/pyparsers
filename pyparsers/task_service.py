import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, Optional
from models import Task, TaskStatus, TaskCompleteRequest
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
    
    def create_task(self, source: str) -> Task:
        """Создать новую задачу"""
        task_id = str(uuid.uuid4())
        now = datetime.now()
        
        task = Task(
            id=task_id,
            source=source,
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
    
    async def send_to_datahub(self, task_id: str, source: str, data: list) -> bool:
        """Отправить данные в datahub"""
        try:
            session = await self.get_session()
            url = f"{self.datahub_url}/api/tasks/{task_id}/complete"
            logger.info(f"POST to datahub: {url} with {len(data)} items")
            
            payload = {
                "task_id": task_id,
                "source": source,
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
    
    async def retry_send_to_datahub(self, task_id: str, source: str, data: list):
        """Повторять отправку в datahub каждые 30 секунд до успеха"""
        while True:
            success = await self.send_to_datahub(task_id, source, data)
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
            
            if task.source == "dongchedi":
                data = await self._parse_dongchedi()
            elif task.source == "che168":
                data = await self._parse_che168()
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
                asyncio.create_task(self.retry_send_to_datahub(task_id, task.source, data))
                # Пока отправляем, держим задачу IN_PROGRESS; DONE поставит отправка при очистке
                return
            else:
                logger.warning(f"No data collected for task {task_id} source {task.source}")
                self.update_task_status(task_id, TaskStatus.FAILED)
                
        except Exception as e:
            logger.exception(f"Error processing task {task_id}: {e}")
            self.update_task_status(task_id, TaskStatus.FAILED)
    
    async def _parse_dongchedi(self) -> list:
        """Парсинг dongchedi"""
        try:
            parser = DongchediParser()
            response = parser.fetch_cars()
            
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
    
    async def _parse_che168(self) -> list:
        """Парсинг che168"""
        try:
            parser = Che168Parser()
            response = parser.fetch_cars()
            
            if not response.data or not response.data.search_sh_sku_info_list:
                return []
            
            cars_list = response.data.search_sh_sku_info_list
            # В che168 часто нет поля year — временно не фильтруем по году
            filtered_cars = cars_list
            logger.info(f"che168: fetched {len(cars_list)} cars, using {len(filtered_cars)} after filtering")
            
            data = []
            missing_id_count = 0
            for i, car in enumerate(filtered_cars):
                car_dict = car.dict()
                
                # Добавляем метаданные
                car_dict.update({
                    'sort_number': len(filtered_cars) - i,
                    'source': 'che168'
                })
                # Гарантируем уникальный int64 car_id: если нет car_id, используем хеш от link
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
                    # берем первые 8 байт как беззнаковое целое и вписываем в диапазон int64
                    car_dict['car_id'] = int.from_bytes(h[:8], byteorder='big', signed=False)

                data.append(car_dict)
            
            if missing_id_count:
                logger.info(f"che168: {missing_id_count} cars had no car_id; generated from link hash")

            # Логируем первые 5 ссылок для отладки
            try:
                sample_links = [d.get('link') for d in data[:5]]
                logger.info(f"che168 sample links: {sample_links}")
            except Exception:
                pass

            return data
            
        except Exception as e:
            logger.error(f"Error parsing che168: {e}")
            return []

# Глобальный экземпляр сервиса
task_service = TaskService()

