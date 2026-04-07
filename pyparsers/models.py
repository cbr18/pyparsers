from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStage(str, Enum):
    QUEUED = "queued"
    INITIALIZING = "initializing"
    LISTING = "listing"
    DETAILED = "detailed"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DETAILED = "detailed"


class TaskCreateRequest(BaseModel):
    task_type: TaskType = TaskType.FULL
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskSnapshot(BaseModel):
    id: str
    source: str
    task_type: TaskType
    status: TaskStatus
    stage: TaskStage
    message: Optional[str] = None
    error_message: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    progress_current: Optional[int] = None
    progress_total: Optional[int] = None
    progress_unit: Optional[str] = None
    items_found: int = 0
    items_processed: int = 0
    items_sent: int = 0
    cancel_requested: bool = False
    result_available: bool = False
    result_summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: datetime
    heartbeat_at: datetime
    result_fetched_at: Optional[datetime] = None


class TaskResultEnvelope(BaseModel):
    task: TaskSnapshot
    result: Any
