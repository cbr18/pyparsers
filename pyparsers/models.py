from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"

class TaskType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"

class Task(BaseModel):
    id: str
    source: str
    task_type: TaskType
    id_field: Optional[str] = None
    existing_ids: Optional[List[str]] = None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

class TaskCreateRequest(BaseModel):
    source: str
    task_type: TaskType = TaskType.FULL
    id_field: Optional[str] = None
    existing_ids: Optional[List[str]] = None

class TaskCreateResponse(BaseModel):
    task_id: str

class TaskCompleteRequest(BaseModel):
    task_id: str
    source: str
    task_type: TaskType
    status: str
    data: List[Dict[str, Any]]

