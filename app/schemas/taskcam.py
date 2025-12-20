from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CurrentTaskOut(BaseModel):
    has_active_lease: bool
    device_id: int
    task_id: Optional[int]
    task_name: Optional[str]
    task_type: Optional[str]
    task_status: Optional[str]
    claimed_at: Optional[datetime]
    lease_expires_at: Optional[datetime]
    lease_seconds_remaining: Optional[int]
    lease_token_hint: Optional[str]
    context_key: Optional[str]


class TaskHistoryItemOut(BaseModel):
    task_id: int
    task_name: str
    task_type: str
    task_status: str
    claimed_at: Optional[datetime]
    finished_at: Optional[datetime]
    last_seen_at: Optional[datetime]
