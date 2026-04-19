from __future__ import annotations

import asyncio
import functools
import gc
import hashlib
import logging
import os
import re
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, Optional

import requests

from api.memory_optimized import MemoryOptimizedList
from car_filter import filter_cars_by_year
from converters import decode_dongchedi_list_sh_price
from models import TaskCreateRequest, TaskResultEnvelope, TaskSnapshot, TaskStage, TaskStatus, TaskType

logger = logging.getLogger(__name__)

INCREMENTAL_EXISTING_LIMIT = int(os.getenv("INCREMENTAL_EXISTING_LIMIT", "15000"))
TASK_TTL_HOURS = int(os.getenv("TASK_TTL_HOURS", "24"))
TASK_RESULT_TTL_MINUTES = int(os.getenv("TASK_RESULT_TTL_MINUTES", "30"))
MAX_TASKS = int(os.getenv("MAX_TASKS", "1000"))
BATCH_DELIVERY_DEFAULT_SIZE = int(os.getenv("BATCH_DELIVERY_DEFAULT_SIZE", "500"))
BATCH_DELIVERY_TIMEOUT_SECONDS = int(os.getenv("BATCH_DELIVERY_TIMEOUT_SECONDS", "30"))
BATCH_DELIVERY_MAX_RETRIES = int(os.getenv("BATCH_DELIVERY_MAX_RETRIES", "3"))


class TaskCancelledError(Exception):
    pass


@dataclass
class TaskRecord:
    id: str
    source: str
    task_type: TaskType
    status: TaskStatus
    stage: TaskStage
    parameters: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    heartbeat_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    message: Optional[str] = None
    error_message: Optional[str] = None
    progress_current: Optional[int] = None
    progress_total: Optional[int] = None
    progress_unit: Optional[str] = None
    items_found: int = 0
    items_processed: int = 0
    items_sent: int = 0
    cancel_requested: bool = False
    result_available: bool = False
    result_summary: Dict[str, Any] = field(default_factory=dict)
    result_fetched_at: Optional[datetime] = None

    def to_snapshot(self) -> TaskSnapshot:
        return TaskSnapshot(
            id=self.id,
            source=self.source,
            task_type=self.task_type,
            status=self.status,
            stage=self.stage,
            message=self.message,
            error_message=self.error_message,
            parameters=self.parameters,
            metadata=self.metadata,
            progress_current=self.progress_current,
            progress_total=self.progress_total,
            progress_unit=self.progress_unit,
            items_found=self.items_found,
            items_processed=self.items_processed,
            items_sent=self.items_sent,
            cancel_requested=self.cancel_requested,
            result_available=self.result_available,
            result_summary=self.result_summary,
            created_at=self.created_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            updated_at=self.updated_at,
            heartbeat_at=self.heartbeat_at,
            result_fetched_at=self.result_fetched_at,
        )


@dataclass
class TaskRunResult:
    result: Any
    summary: Dict[str, Any]


@dataclass
class BatchDeliveryState:
    endpoint: str
    batch_size: int
    timeout_seconds: int
    max_retries: int
    auth_token: Optional[str] = None
    buffer: list[dict[str, Any]] = field(default_factory=list)
    batches_sent: int = 0
    items_sent: int = 0
    failed_batches: int = 0


class TaskContext:
    def __init__(self, service: "TaskService", task_id: str):
        self._service = service
        self.task_id = task_id

    async def set_stage(
        self,
        stage: TaskStage,
        *,
        message: Optional[str] = None,
        progress_current: Optional[int] = None,
        progress_total: Optional[int] = None,
        progress_unit: Optional[str] = None,
    ) -> None:
        await self._service._update_task(
            self.task_id,
            stage=stage,
            message=message,
            progress_current=progress_current,
            progress_total=progress_total,
            progress_unit=progress_unit,
        )

    async def update(
        self,
        *,
        message: Optional[str] = None,
        progress_current: Optional[int] = None,
        progress_total: Optional[int] = None,
        progress_unit: Optional[str] = None,
        items_found: Optional[int] = None,
        items_processed: Optional[int] = None,
        items_sent: Optional[int] = None,
        result_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        await self._service._update_task(
            self.task_id,
            message=message,
            progress_current=progress_current,
            progress_total=progress_total,
            progress_unit=progress_unit,
            items_found=items_found,
            items_processed=items_processed,
            items_sent=items_sent,
            result_summary=result_summary,
        )

    async def check_cancelled(self) -> None:
        task = self._service.tasks.get(self.task_id)
        if task and task.cancel_requested:
            raise TaskCancelledError(f"Task {self.task_id} was cancelled")

    async def run_sync(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        if kwargs:
            return await loop.run_in_executor(self._service._executor, functools.partial(func, *args, **kwargs))
        return await loop.run_in_executor(self._service._executor, func, *args)


class TaskService:
    def __init__(
        self,
        *,
        source: str,
        runners: Dict[TaskType, Callable[[TaskContext, Dict[str, Any]], Awaitable[TaskRunResult]]],
    ):
        self.source = source
        self.runners = runners
        self.tasks: OrderedDict[str, TaskRecord] = OrderedDict()
        self.results: Dict[str, Any] = {}
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix=f"{source}-task")
        self._worker_task: Optional[asyncio.Task] = None

    async def startup(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop(), name=f"{self.source}-task-worker")

    async def shutdown(self) -> None:
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self._executor.shutdown(wait=False)

    def create_task(self, request: TaskCreateRequest) -> TaskSnapshot:
        if request.task_type not in self.runners:
            raise ValueError(f"Unsupported task type '{request.task_type}' for source '{self.source}'")

        self._cleanup_old_tasks()
        self._trim_if_needed()

        now = datetime.now(timezone.utc)
        task_id = str(uuid.uuid4())
        record = TaskRecord(
            id=task_id,
            source=self.source,
            task_type=request.task_type,
            status=TaskStatus.QUEUED,
            stage=TaskStage.QUEUED,
            parameters=request.parameters,
            metadata=request.metadata,
            created_at=now,
            updated_at=now,
            heartbeat_at=now,
            message="Task is queued",
        )
        self.tasks[task_id] = record
        self.tasks.move_to_end(task_id)
        self._queue.put_nowait(task_id)
        return record.to_snapshot()

    def list_tasks(self) -> list[TaskSnapshot]:
        self._cleanup_old_tasks()
        return [task.to_snapshot() for task in reversed(self.tasks.values())]

    def get_task(self, task_id: str) -> Optional[TaskSnapshot]:
        self._cleanup_old_tasks()
        task = self.tasks.get(task_id)
        if not task:
            return None
        self.tasks.move_to_end(task_id)
        return task.to_snapshot()

    def get_task_result(self, task_id: str) -> Optional[TaskResultEnvelope]:
        self._cleanup_old_tasks()
        task = self.tasks.get(task_id)
        if not task or task_id not in self.results:
            return None
        task.result_fetched_at = datetime.now(timezone.utc)
        task.updated_at = task.result_fetched_at
        self.tasks.move_to_end(task_id)
        return TaskResultEnvelope(task=task.to_snapshot(), result=self.results[task_id])

    def cancel_task(self, task_id: str) -> Optional[TaskSnapshot]:
        task = self.tasks.get(task_id)
        if task is None:
            return None

        now = datetime.now(timezone.utc)
        if task.status == TaskStatus.QUEUED:
            task.status = TaskStatus.CANCELLED
            task.stage = TaskStage.CANCELLED
            task.message = "Task was cancelled before execution"
            task.finished_at = now
        elif task.status == TaskStatus.RUNNING:
            task.cancel_requested = True
            task.message = "Cancellation requested"
        task.updated_at = now
        task.heartbeat_at = now
        self.tasks.move_to_end(task_id)
        return task.to_snapshot()

    async def _worker_loop(self) -> None:
        while True:
            task_id = await self._queue.get()
            try:
                await self._execute(task_id)
            finally:
                self._queue.task_done()

    async def _execute(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if task is None or task.status == TaskStatus.CANCELLED:
            return

        task.status = TaskStatus.RUNNING
        task.stage = TaskStage.INITIALIZING
        task.started_at = datetime.now(timezone.utc)
        task.message = "Task is running"
        task.updated_at = task.started_at
        task.heartbeat_at = task.started_at
        self.tasks.move_to_end(task_id)

        context = TaskContext(self, task_id)
        runner = self.runners[task.task_type]

        try:
            result = await runner(context, task.parameters)
            result_items_sent = task.items_sent
            if result.summary.get("delivery_mode") == "push_batches":
                try:
                    result_items_sent = int(result.summary.get("items_sent", task.items_sent))
                except (TypeError, ValueError):
                    result_items_sent = task.items_sent
            elif isinstance(result.result, Iterable) and not isinstance(result.result, (dict, str, bytes)):
                result_items_sent = len(result.result)

            result_items_found = None
            if "items_found" in result.summary:
                try:
                    result_items_found = int(result.summary["items_found"])
                except (TypeError, ValueError):
                    result_items_found = None

            await self._update_task(
                task_id,
                status=TaskStatus.SUCCEEDED,
                stage=TaskStage.COMPLETED,
                message="Task completed successfully",
                items_found=result_items_found,
                items_sent=result_items_sent,
                result_summary=result.summary,
                finished_at=datetime.now(timezone.utc),
                result_available=True,
            )
            self.results[task_id] = result.result
        except TaskCancelledError:
            await self._update_task(
                task_id,
                status=TaskStatus.CANCELLED,
                stage=TaskStage.CANCELLED,
                message="Task execution was cancelled",
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.exception("Task %s failed", task_id)
            await self._update_task(
                task_id,
                status=TaskStatus.FAILED,
                stage=TaskStage.FAILED,
                message="Task failed",
                error_message=str(exc) or exc.__class__.__name__,
                finished_at=datetime.now(timezone.utc),
            )

    async def _update_task(
        self,
        task_id: str,
        *,
        status: Optional[TaskStatus] = None,
        stage: Optional[TaskStage] = None,
        message: Optional[str] = None,
        error_message: Optional[str] = None,
        progress_current: Optional[int] = None,
        progress_total: Optional[int] = None,
        progress_unit: Optional[str] = None,
        items_found: Optional[int] = None,
        items_processed: Optional[int] = None,
        items_sent: Optional[int] = None,
        result_summary: Optional[Dict[str, Any]] = None,
        finished_at: Optional[datetime] = None,
        result_available: Optional[bool] = None,
    ) -> None:
        task = self.tasks.get(task_id)
        if task is None:
            return

        now = datetime.now(timezone.utc)
        if status is not None:
            task.status = status
        if stage is not None:
            task.stage = stage
        if message is not None:
            task.message = message
        if error_message is not None:
            task.error_message = error_message
        if progress_current is not None:
            task.progress_current = progress_current
        if progress_total is not None:
            task.progress_total = progress_total
        if progress_unit is not None:
            task.progress_unit = progress_unit
        if items_found is not None:
            task.items_found = items_found
        if items_processed is not None:
            task.items_processed = items_processed
        if items_sent is not None:
            task.items_sent = items_sent
        if result_summary is not None:
            task.result_summary = result_summary
        if finished_at is not None:
            task.finished_at = finished_at
        if result_available is not None:
            task.result_available = result_available
        task.updated_at = now
        task.heartbeat_at = now
        self.tasks.move_to_end(task_id)

    def _cleanup_old_tasks(self) -> None:
        now = datetime.now(timezone.utc)
        task_cutoff = now - timedelta(hours=TASK_TTL_HOURS)
        result_cutoff = now - timedelta(minutes=TASK_RESULT_TTL_MINUTES)

        to_delete: list[str] = []
        for task_id, task in self.tasks.items():
            if task.created_at < task_cutoff:
                to_delete.append(task_id)
                continue
            if task_id in self.results and task.finished_at and task.finished_at < result_cutoff:
                del self.results[task_id]
                task.result_available = False

        for task_id in to_delete:
            self.tasks.pop(task_id, None)
            self.results.pop(task_id, None)

    def _trim_if_needed(self) -> None:
        while len(self.tasks) >= MAX_TASKS:
            task_id, task = next(iter(self.tasks.items()))
            if task.status in {TaskStatus.RUNNING, TaskStatus.QUEUED}:
                break
            self.tasks.pop(task_id, None)
            self.results.pop(task_id, None)


def _hash_car_id_from_link(link: str) -> int:
    digest = hashlib.md5(link.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def _build_batch_delivery_state(parameters: Dict[str, Any]) -> Optional[BatchDeliveryState]:
    delivery_mode = str(parameters.get("delivery_mode") or "result").strip().lower()
    if delivery_mode in ("", "result", "pull_result"):
        return None
    if delivery_mode != "push_batches":
        raise ValueError(f"Unsupported delivery_mode '{delivery_mode}'")

    endpoint = (
        parameters.get("batch_endpoint")
        or parameters.get("datahub_batch_endpoint")
        or os.getenv("DATAHUB_BATCH_ENDPOINT")
    )
    if not endpoint:
        datahub_url = os.getenv("DATAHUB_URL", "").rstrip("/")
        if datahub_url:
            endpoint = f"{datahub_url}/parser/batches"
    if not endpoint:
        raise ValueError("delivery_mode=push_batches requires parameters.batch_endpoint or DATAHUB_BATCH_ENDPOINT")

    batch_size = parameters.get("batch_size") or parameters.get("batch_items") or BATCH_DELIVERY_DEFAULT_SIZE
    try:
        batch_size = max(1, int(batch_size))
    except (TypeError, ValueError):
        raise ValueError("parameters.batch_size must be a positive integer") from None

    timeout_seconds = parameters.get("batch_timeout_seconds") or BATCH_DELIVERY_TIMEOUT_SECONDS
    max_retries = parameters.get("batch_max_retries") or BATCH_DELIVERY_MAX_RETRIES

    return BatchDeliveryState(
        endpoint=str(endpoint),
        batch_size=batch_size,
        timeout_seconds=max(1, int(timeout_seconds)),
        max_retries=max(1, int(max_retries)),
        auth_token=parameters.get("batch_auth_token") or os.getenv("DATAHUB_BATCH_TOKEN"),
    )


def _batch_item_key(source: str, car_dict: dict[str, Any]) -> Optional[str]:
    for field_name in ("car_id", "sku_id", "link"):
        value = car_dict.get(field_name)
        if value not in (None, ""):
            return f"{source}:{field_name}:{value}"
    return None


def _append_unique_listing(seen_keys: set[str], source: str, car_dict: dict[str, Any]) -> bool:
    key = _batch_item_key(source, car_dict)
    if key is None:
        return True
    if key in seen_keys:
        return False
    seen_keys.add(key)
    return True


def _post_parser_batch(
    *,
    endpoint: str,
    payload: dict[str, Any],
    timeout_seconds: int,
    auth_token: Optional[str],
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "X-Parser-Task-Id": str(payload["task_id"]),
        "X-Parser-Batch-Id": str(payload["batch_id"]),
        "Idempotency-Key": str(payload["batch_id"]),
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout_seconds)
    response.raise_for_status()
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        return {"raw_response": response.text}


async def _flush_listing_batch(
    context: TaskContext,
    delivery: Optional[BatchDeliveryState],
    *,
    source: str,
    task_type: TaskType,
    page: int,
    final: bool = False,
) -> None:
    if delivery is None:
        return
    if not delivery.buffer and not final:
        return

    batch_items = delivery.buffer
    delivery.buffer = []
    batch_sequence = delivery.batches_sent + delivery.failed_batches + 1
    batch_id = f"{context.task_id}:{batch_sequence}"
    payload = {
        "task_id": context.task_id,
        "source": source,
        "task_type": task_type.value,
        "batch_id": batch_id,
        "batch_sequence": batch_sequence,
        "page": page,
        "is_final": final,
        "items": batch_items,
        "item_count": len(batch_items),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    last_error: Optional[Exception] = None
    for attempt in range(1, delivery.max_retries + 1):
        try:
            await context.run_sync(
                _post_parser_batch,
                endpoint=delivery.endpoint,
                payload=payload,
                timeout_seconds=delivery.timeout_seconds,
                auth_token=delivery.auth_token,
            )
            delivery.batches_sent += 1
            delivery.items_sent += len(batch_items)
            await context.update(
                message=f"Delivered {source} batch {batch_sequence}",
                items_sent=delivery.items_sent,
                result_summary={
                    "delivery_mode": "push_batches",
                    "batches_sent": delivery.batches_sent,
                    "items_sent": delivery.items_sent,
                    "failed_batches": delivery.failed_batches,
                },
            )
            return
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Failed to deliver %s batch %s attempt %s/%s: %s",
                source,
                batch_id,
                attempt,
                delivery.max_retries,
                exc,
            )
            if attempt < delivery.max_retries:
                await asyncio.sleep(min(2 ** (attempt - 1), 10))

    delivery.failed_batches += 1
    raise RuntimeError(f"Failed to deliver parser batch {batch_id}: {last_error}") from last_error


async def _emit_or_collect_listing(
    context: TaskContext,
    delivery: Optional[BatchDeliveryState],
    data: MemoryOptimizedList,
    car_dict: dict[str, Any],
    *,
    source: str,
    task_type: TaskType,
    page: int,
) -> None:
    if delivery is None:
        data.append(car_dict)
        return

    delivery.buffer.append(car_dict)
    if len(delivery.buffer) >= delivery.batch_size:
        await _flush_listing_batch(
            context,
            delivery,
            source=source,
            task_type=task_type,
            page=page,
        )


def _delivery_summary(delivery: Optional[BatchDeliveryState]) -> dict[str, Any]:
    if delivery is None:
        return {"delivery_mode": "result"}
    return {
        "delivery_mode": "push_batches",
        "batches_sent": delivery.batches_sent,
        "items_sent": delivery.items_sent,
        "failed_batches": delivery.failed_batches,
        "batch_size": delivery.batch_size,
    }


def _normalize_che168_listing_car(car_dict: dict, index: int, total: int) -> Optional[dict]:
    if not car_dict.get("link") and car_dict.get("car_id"):
        car_dict["link"] = f'https://m.che168.com/cardetail/index?infoid={car_dict["car_id"]}'

    car_dict.update({
        "sort_number": total - index,
        "source": "che168",
    })

    if car_dict.get("sh_price") not in (None, ""):
        try:
            car_dict["price"] = float(str(car_dict["sh_price"]).strip())
        except (ValueError, TypeError):
            pass

    year_val = car_dict.get("car_year")
    if year_val is not None:
        try:
            car_dict["year"] = int(year_val)
        except (ValueError, TypeError):
            car_dict["year"] = None

    if car_dict.get("year") in (None, 0):
        title_text = car_dict.get("title") or ""
        match = re.search(r"(19|20)\d{2}", title_text)
        if match:
            try:
                candidate_year = int(match.group(0))
                if 1990 <= candidate_year <= 2030:
                    car_dict["year"] = candidate_year
            except ValueError:
                pass

    if car_dict.get("year") is not None and car_dict["year"] < 2017:
        return None

    if car_dict.get("car_source_city_name"):
        car_dict["city"] = car_dict.get("car_source_city_name")

    mileage_raw = car_dict.get("car_mileage")
    if isinstance(mileage_raw, str) and mileage_raw.strip():
        match = re.search(r"[0-9]+(?:\.[0-9]+)?", mileage_raw)
        if match:
            try:
                mileage = float(match.group(0))
                car_dict["mileage"] = int(mileage * 10000 if "万" in mileage_raw else mileage)
            except Exception:
                pass

    try:
        if car_dict.get("car_id") is None:
            raise ValueError("missing car_id")
        car_dict["car_id"] = int(car_dict["car_id"])
    except Exception:
        link = car_dict.get("link") or ""
        car_dict["car_id"] = _hash_car_id_from_link(link)

    return car_dict


def _normalize_encar_listing_car(car_dict: dict, index: int, total: int) -> Optional[dict]:
    year_val = car_dict.get("year") or car_dict.get("car_year")
    if year_val is not None:
        try:
            if int(year_val) < 2017:
                return None
        except (ValueError, TypeError):
            pass

    car_dict.update({
        "sort_number": total - index,
        "source": "encar",
    })

    if car_dict.get("car_id") is not None:
        try:
            car_dict["car_id"] = int(car_dict["car_id"])
        except (ValueError, TypeError):
            car_dict["car_id"] = 0

    if not car_dict.get("sku_id") and car_dict.get("car_id") is not None:
        car_dict["sku_id"] = str(car_dict["car_id"])

    if not car_dict.get("city") and car_dict.get("car_source_city_name"):
        car_dict["city"] = car_dict["car_source_city_name"]

    return car_dict


def _normalize_detailed_items(source: str, parameters: Dict[str, Any]) -> list[dict[str, Any]]:
    items = parameters.get("items") or []
    if not items:
        raise ValueError(f"parameters.items must contain at least one {source} detailed item")

    normalized_items: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"each {source} detailed item must be an object")

        external_id = str(item.get("external_id", "")).strip()
        secondary_id = str(item.get("secondary_id", "")).strip()
        if not external_id:
            raise ValueError(f"each {source} detailed item must include external_id")
        if source == "che168" and not secondary_id:
            raise ValueError("each che168 detailed item must include secondary_id")

        normalized_items.append(
            {
                "external_id": external_id,
                "secondary_id": secondary_id or None,
                "force_update": bool(item.get("force_update", False)),
            }
        )

    return normalized_items


def build_task_service(source: str) -> TaskService:
    if source == "dongchedi":
        return TaskService(source=source, runners=_build_dongchedi_runners())
    if source == "che168":
        return TaskService(source=source, runners=_build_che168_runners())
    if source == "encar":
        return TaskService(source=source, runners=_build_encar_runners())
    raise ValueError(f"Unsupported source '{source}'")


def _build_dongchedi_runners():
    from api.dongchedi.parser import DongchediParser

    async def full(context: TaskContext, parameters: Dict[str, Any]) -> TaskRunResult:
        parser = DongchediParser()
        data = MemoryOptimizedList()
        delivery = _build_batch_delivery_state(parameters)
        seen_keys: set[str] = set()
        page = 1
        pages_scanned = 0

        await context.set_stage(TaskStage.LISTING, message="Collecting full dongchedi listing", progress_current=0, progress_total=100, progress_unit="page")

        while True:
            await context.check_cancelled()
            response = await context.run_sync(parser.fetch_cars_by_page, page)
            pages_scanned = page
            cars_list = getattr(response.data, "search_sh_sku_info_list", None)
            if not cars_list:
                break

            filtered = filter_cars_by_year(cars_list, min_year=2017)
            total_filtered = len(filtered)
            for index, car in enumerate(filtered):
                car_dict = car.dict()
                car_dict.update({"sort_number": total_filtered - index, "source": "dongchedi"})
                if car_dict.get("sh_price"):
                    car_dict["sh_price"] = decode_dongchedi_list_sh_price(car_dict["sh_price"])
                if car_dict.get("car_id") is not None:
                    try:
                        car_dict["car_id"] = int(car_dict["car_id"])
                    except (ValueError, TypeError):
                        car_dict["car_id"] = 0
                if not _append_unique_listing(seen_keys, "dongchedi", car_dict):
                    continue
                await _emit_or_collect_listing(
                    context,
                    delivery,
                    data,
                    car_dict,
                    source="dongchedi",
                    task_type=TaskType.FULL,
                    page=page,
                )

            await context.update(
                message=f"Parsed dongchedi page {page}",
                progress_current=page,
                items_found=len(seen_keys) if delivery is not None else len(data),
            )

            if not getattr(response.data, "has_more", False):
                break
            page += 1

        await _flush_listing_batch(
            context,
            delivery,
            source="dongchedi",
            task_type=TaskType.FULL,
            page=pages_scanned,
            final=True,
        )

        summary = {
            "pages_scanned": pages_scanned,
            "items_found": len(seen_keys) if delivery is not None else len(data),
            **_delivery_summary(delivery),
        }
        await context.set_stage(TaskStage.FINALIZING, message="Finalizing full dongchedi result")
        return TaskRunResult(result=[] if delivery is not None else list(data), summary=summary)

    async def incremental(context: TaskContext, parameters: Dict[str, Any]) -> TaskRunResult:
        parser = DongchediParser()
        data = MemoryOptimizedList()
        delivery = _build_batch_delivery_state(parameters)
        seen_keys: set[str] = set()
        existing_ids = parameters.get("existing_ids") or []
        id_field = parameters.get("id_field") or "sku_id"
        existing_set = {str(x) for idx, x in enumerate(existing_ids) if x and idx < INCREMENTAL_EXISTING_LIMIT}
        pages_scanned = 0

        await context.set_stage(TaskStage.LISTING, message="Collecting incremental dongchedi listing", progress_current=0, progress_total=100, progress_unit="page")

        for page in range(1, 101):
            await context.check_cancelled()
            response = await context.run_sync(parser.fetch_cars_by_page, page)
            pages_scanned = page
            cars_list = getattr(response.data, "search_sh_sku_info_list", None)
            if not cars_list:
                break

            filtered = filter_cars_by_year(cars_list, min_year=2017)
            total_filtered = len(filtered)
            found_existing = False
            for index, car in enumerate(filtered):
                car_dict = car.dict()
                key_val = car_dict.get(id_field)
                key_val = str(key_val) if key_val is not None else None
                if key_val and key_val in existing_set:
                    found_existing = True
                    break

                car_dict.update({"sort_number": total_filtered - index, "source": "dongchedi"})
                if car_dict.get("sh_price"):
                    car_dict["sh_price"] = decode_dongchedi_list_sh_price(car_dict["sh_price"])
                if car_dict.get("car_id") is not None:
                    try:
                        car_dict["car_id"] = int(car_dict["car_id"])
                    except (ValueError, TypeError):
                        car_dict["car_id"] = 0
                if not _append_unique_listing(seen_keys, "dongchedi", car_dict):
                    continue
                await _emit_or_collect_listing(
                    context,
                    delivery,
                    data,
                    car_dict,
                    source="dongchedi",
                    task_type=TaskType.INCREMENTAL,
                    page=page,
                )

            await context.update(
                message=f"Parsed dongchedi page {page}",
                progress_current=page,
                items_found=len(seen_keys) if delivery is not None else len(data),
            )

            if found_existing or not getattr(response.data, "has_more", False):
                break

        await _flush_listing_batch(
            context,
            delivery,
            source="dongchedi",
            task_type=TaskType.INCREMENTAL,
            page=pages_scanned,
            final=True,
        )

        summary = {
            "pages_scanned": pages_scanned,
            "items_found": len(seen_keys) if delivery is not None else len(data),
            "id_field": id_field,
            **_delivery_summary(delivery),
        }
        await context.set_stage(TaskStage.FINALIZING, message="Finalizing incremental dongchedi result")
        existing_set.clear()
        gc.collect()
        return TaskRunResult(result=[] if delivery is not None else list(data), summary=summary)

    async def detailed(context: TaskContext, parameters: Dict[str, Any]) -> TaskRunResult:
        parser = DongchediParser()
        normalized_items = _normalize_detailed_items("dongchedi", parameters)

        await context.set_stage(
            TaskStage.DETAILED,
            message="Parsing dongchedi detailed cars",
            progress_current=0,
            progress_total=len(normalized_items),
            progress_unit="car",
        )

        results = []
        success_count = 0
        for index, item in enumerate(normalized_items, start=1):
            await context.check_cancelled()
            external_id = item["external_id"]
            secondary_id = item["secondary_id"]
            car_obj, meta = await context.run_sync(parser.fetch_car_detail, external_id)
            if car_obj is not None:
                results.append({
                    "status": meta.get("status", 200),
                    "car": car_obj.dict(),
                    "meta": meta,
                })
                success_count += 1
            else:
                results.append({
                    "status": meta.get("status", 500),
                    "car": {
                        "car_id": secondary_id or external_id,
                        "sku_id": external_id,
                        "is_available": False,
                        "source": "dongchedi",
                        "error": meta.get("error"),
                    },
                    "meta": meta,
                })

            await context.update(
                message=f"Processed dongchedi detailed car {index}/{len(normalized_items)}",
                progress_current=index,
                items_processed=index,
            )

        summary = {"requested": len(normalized_items), "successful": success_count, "failed": len(normalized_items) - success_count}
        await context.set_stage(TaskStage.FINALIZING, message="Finalizing dongchedi detailed result")
        return TaskRunResult(result=results, summary=summary)

    return {
        TaskType.FULL: full,
        TaskType.INCREMENTAL: incremental,
        TaskType.DETAILED: detailed,
    }


def _build_che168_runners():
    from api.che168.parser import Che168Parser

    async def full(context: TaskContext, parameters: Dict[str, Any]) -> TaskRunResult:
        parser = Che168Parser()
        data = MemoryOptimizedList()
        delivery = _build_batch_delivery_state(parameters)
        seen_keys: set[str] = set()
        pages_scanned = 0
        empty_pages = 0

        await context.set_stage(TaskStage.LISTING, message="Collecting full che168 listing", progress_current=0, progress_total=100, progress_unit="page")

        for page in range(1, 101):
            await context.check_cancelled()
            response = await context.run_sync(parser.fetch_cars_by_page, page)
            pages_scanned = page
            cars_list = getattr(response.data, "search_sh_sku_info_list", None)
            if not cars_list:
                empty_pages += 1
                if empty_pages >= 3:
                    break
                await context.update(message=f"che168 page {page} returned no cars", progress_current=page)
                continue

            empty_pages = 0
            total_cars = len(cars_list)
            for index, car in enumerate(cars_list):
                normalized = _normalize_che168_listing_car(car.dict(exclude_none=False), index, total_cars)
                if normalized is not None:
                    if not _append_unique_listing(seen_keys, "che168", normalized):
                        continue
                    await _emit_or_collect_listing(
                        context,
                        delivery,
                        data,
                        normalized,
                        source="che168",
                        task_type=TaskType.FULL,
                        page=page,
                    )

            await context.update(
                message=f"Parsed che168 page {page}",
                progress_current=page,
                items_found=len(seen_keys) if delivery is not None else len(data),
            )

            if not getattr(response.data, "has_more", False):
                break

        await _flush_listing_batch(
            context,
            delivery,
            source="che168",
            task_type=TaskType.FULL,
            page=pages_scanned,
            final=True,
        )

        summary = {
            "pages_scanned": pages_scanned,
            "items_found": len(seen_keys) if delivery is not None else len(data),
            **_delivery_summary(delivery),
        }
        await context.set_stage(TaskStage.FINALIZING, message="Finalizing full che168 result")
        return TaskRunResult(result=[] if delivery is not None else list(data), summary=summary)

    async def incremental(context: TaskContext, parameters: Dict[str, Any]) -> TaskRunResult:
        parser = Che168Parser()
        data = MemoryOptimizedList()
        delivery = _build_batch_delivery_state(parameters)
        seen_keys: set[str] = set()
        existing_ids = parameters.get("existing_ids") or []
        id_field = parameters.get("id_field") or "car_id"
        existing_set = {str(x) for idx, x in enumerate(existing_ids) if x and idx < INCREMENTAL_EXISTING_LIMIT}
        pages_scanned = 0

        await context.set_stage(TaskStage.LISTING, message="Collecting incremental che168 listing", progress_current=0, progress_total=100, progress_unit="page")

        for page in range(1, 101):
            await context.check_cancelled()
            response = await context.run_sync(parser.fetch_cars_by_page, page)
            pages_scanned = page
            cars_list = getattr(response.data, "search_sh_sku_info_list", None)
            if not cars_list:
                break

            total_cars = len(cars_list)
            found_existing = False
            for index, car in enumerate(cars_list):
                car_dict = car.dict(exclude_none=False)
                stop_id = car_dict.get(id_field)
                if stop_id is not None:
                    try:
                        stop_id = str(int(stop_id))
                    except Exception:
                        stop_id = str(stop_id)
                if stop_id and stop_id in existing_set:
                    found_existing = True
                    break

                normalized = _normalize_che168_listing_car(car_dict, index, total_cars)
                if normalized is not None:
                    if not _append_unique_listing(seen_keys, "che168", normalized):
                        continue
                    await _emit_or_collect_listing(
                        context,
                        delivery,
                        data,
                        normalized,
                        source="che168",
                        task_type=TaskType.INCREMENTAL,
                        page=page,
                    )

            await context.update(
                message=f"Parsed che168 page {page}",
                progress_current=page,
                items_found=len(seen_keys) if delivery is not None else len(data),
            )

            if found_existing:
                break

        await _flush_listing_batch(
            context,
            delivery,
            source="che168",
            task_type=TaskType.INCREMENTAL,
            page=pages_scanned,
            final=True,
        )

        summary = {
            "pages_scanned": pages_scanned,
            "items_found": len(seen_keys) if delivery is not None else len(data),
            "id_field": id_field,
            **_delivery_summary(delivery),
        }
        await context.set_stage(TaskStage.FINALIZING, message="Finalizing incremental che168 result")
        existing_set.clear()
        gc.collect()
        return TaskRunResult(result=[] if delivery is not None else list(data), summary=summary)

    async def detailed(context: TaskContext, parameters: Dict[str, Any]) -> TaskRunResult:
        from api.che168.detailed_api import CarDetailRequest, parse_car_details

        normalized_items = _normalize_detailed_items("che168", parameters)

        await context.set_stage(
            TaskStage.DETAILED,
            message="Parsing che168 detailed cars",
            progress_current=0,
            progress_total=len(normalized_items),
            progress_unit="car",
        )

        results = []
        success_count = 0
        for index, item in enumerate(normalized_items, start=1):
            await context.check_cancelled()
            detail_request = CarDetailRequest(
                car_id=int(item["external_id"]),
                shop_id=int(item["secondary_id"]),
                force_update=bool(item.get("force_update", False)),
            )
            detail = await parse_car_details(detail_request)
            detail_payload = detail.model_dump() if hasattr(detail, "model_dump") else detail.dict()
            results.append(detail_payload)
            if detail_payload.get("success"):
                success_count += 1

            await context.update(
                message=f"Processed che168 detailed car {index}/{len(normalized_items)}",
                progress_current=index,
                items_processed=index,
            )

        summary = {"requested": len(normalized_items), "successful": success_count, "failed": len(normalized_items) - success_count}
        await context.set_stage(TaskStage.FINALIZING, message="Finalizing che168 detailed result")
        return TaskRunResult(result=results, summary=summary)

    return {
        TaskType.FULL: full,
        TaskType.INCREMENTAL: incremental,
        TaskType.DETAILED: detailed,
    }


def _build_encar_runners():
    from api.encar.parser import EncarParser

    async def full(context: TaskContext, parameters: Dict[str, Any]) -> TaskRunResult:
        parser = EncarParser()
        data = MemoryOptimizedList()
        delivery = _build_batch_delivery_state(parameters)
        seen_keys: set[str] = set()
        page = 1
        pages_scanned = 0

        await context.set_stage(TaskStage.LISTING, message="Collecting full encar listing", progress_current=0, progress_total=100, progress_unit="page")

        while True:
            await context.check_cancelled()
            response = await context.run_sync(parser.fetch_cars_by_page, page)
            pages_scanned = page
            cars_list = getattr(response.data, "search_sh_sku_info_list", None)
            if not cars_list:
                break

            total_cars = len(cars_list)
            for index, car in enumerate(cars_list):
                normalized = _normalize_encar_listing_car(car.dict(exclude_none=False), index, total_cars)
                if normalized is not None:
                    if not _append_unique_listing(seen_keys, "encar", normalized):
                        continue
                    await _emit_or_collect_listing(
                        context,
                        delivery,
                        data,
                        normalized,
                        source="encar",
                        task_type=TaskType.FULL,
                        page=page,
                    )

            await context.update(
                message=f"Parsed encar page {page}",
                progress_current=page,
                items_found=len(seen_keys) if delivery is not None else len(data),
            )

            if not getattr(response.data, "has_more", False):
                break
            page += 1

        await _flush_listing_batch(
            context,
            delivery,
            source="encar",
            task_type=TaskType.FULL,
            page=pages_scanned,
            final=True,
        )

        summary = {
            "pages_scanned": pages_scanned,
            "items_found": len(seen_keys) if delivery is not None else len(data),
            **_delivery_summary(delivery),
        }
        await context.set_stage(TaskStage.FINALIZING, message="Finalizing full encar result")
        return TaskRunResult(result=[] if delivery is not None else list(data), summary=summary)

    async def incremental(context: TaskContext, parameters: Dict[str, Any]) -> TaskRunResult:
        parser = EncarParser()
        data = MemoryOptimizedList()
        delivery = _build_batch_delivery_state(parameters)
        seen_keys: set[str] = set()
        existing_ids = parameters.get("existing_ids") or []
        id_field = parameters.get("id_field") or "car_id"
        existing_set = {str(x) for idx, x in enumerate(existing_ids) if x and idx < INCREMENTAL_EXISTING_LIMIT}
        page = 1
        pages_scanned = 0

        await context.set_stage(TaskStage.LISTING, message="Collecting incremental encar listing", progress_current=0, progress_total=100, progress_unit="page")

        while True:
            await context.check_cancelled()
            response = await context.run_sync(parser.fetch_cars_by_page, page)
            pages_scanned = page
            cars_list = getattr(response.data, "search_sh_sku_info_list", None)
            if not cars_list:
                break

            found_existing = False
            total_cars = len(cars_list)
            for index, car in enumerate(cars_list):
                car_dict = car.dict(exclude_none=False)
                stop_id = car_dict.get(id_field)
                stop_id = str(stop_id) if stop_id is not None else None
                if stop_id and stop_id in existing_set:
                    found_existing = True
                    break

                normalized = _normalize_encar_listing_car(car_dict, index, total_cars)
                if normalized is not None:
                    if not _append_unique_listing(seen_keys, "encar", normalized):
                        continue
                    await _emit_or_collect_listing(
                        context,
                        delivery,
                        data,
                        normalized,
                        source="encar",
                        task_type=TaskType.INCREMENTAL,
                        page=page,
                    )

            await context.update(
                message=f"Parsed encar page {page}",
                progress_current=page,
                items_found=len(seen_keys) if delivery is not None else len(data),
            )

            if found_existing or not getattr(response.data, "has_more", False):
                break
            page += 1

        await _flush_listing_batch(
            context,
            delivery,
            source="encar",
            task_type=TaskType.INCREMENTAL,
            page=pages_scanned,
            final=True,
        )

        summary = {
            "pages_scanned": pages_scanned,
            "items_found": len(seen_keys) if delivery is not None else len(data),
            "id_field": id_field,
            **_delivery_summary(delivery),
        }
        await context.set_stage(TaskStage.FINALIZING, message="Finalizing incremental encar result")
        existing_set.clear()
        gc.collect()
        return TaskRunResult(result=[] if delivery is not None else list(data), summary=summary)

    async def detailed(context: TaskContext, parameters: Dict[str, Any]) -> TaskRunResult:
        parser = EncarParser()
        normalized_items = _normalize_detailed_items("encar", parameters)

        await context.set_stage(
            TaskStage.DETAILED,
            message="Parsing encar detailed cars",
            progress_current=0,
            progress_total=len(normalized_items),
            progress_unit="car",
        )

        results = []
        success_count = 0
        for index, item in enumerate(normalized_items, start=1):
            await context.check_cancelled()
            external_id = item["external_id"]
            car_obj, meta = await context.run_sync(parser.fetch_car_detail, external_id)
            if car_obj is not None:
                results.append({
                    "status": meta.get("status", 200),
                    "car": car_obj.dict(),
                    "meta": meta,
                })
                success_count += 1
            else:
                results.append({
                    "status": meta.get("status", 500),
                    "car": {
                        "car_id": external_id,
                        "sku_id": external_id,
                        "is_available": False,
                        "source": "encar",
                        "error": meta.get("error"),
                    },
                    "meta": meta,
                })

            await context.update(
                message=f"Processed encar detailed car {index}/{len(normalized_items)}",
                progress_current=index,
                items_processed=index,
            )

        summary = {"requested": len(normalized_items), "successful": success_count, "failed": len(normalized_items) - success_count}
        await context.set_stage(TaskStage.FINALIZING, message="Finalizing encar detailed result")
        return TaskRunResult(result=results, summary=summary)

    return {
        TaskType.FULL: full,
        TaskType.INCREMENTAL: incremental,
        TaskType.DETAILED: detailed,
    }
