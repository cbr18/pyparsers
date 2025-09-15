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

class Task(BaseModel):
    id: str
    source: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

class TaskCreateRequest(BaseModel):
    source: str

class TaskCreateResponse(BaseModel):
    task_id: str

class TaskCompleteRequest(BaseModel):
    task_id: str
    source: str
    status: str
    data: List[Dict[str, Any]]

