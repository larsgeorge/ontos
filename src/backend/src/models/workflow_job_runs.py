from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WorkflowJobRunBase(BaseModel):
    """Base model for workflow job run."""
    run_id: int
    run_name: Optional[str] = None
    life_cycle_state: Optional[str] = None
    result_state: Optional[str] = None
    state_message: Optional[str] = None
    start_time: Optional[int] = None  # Unix timestamp in milliseconds
    end_time: Optional[int] = None  # Unix timestamp in milliseconds
    duration_ms: Optional[int] = None


class WorkflowJobRunCreate(WorkflowJobRunBase):
    """Model for creating a workflow job run."""
    workflow_installation_id: str


class WorkflowJobRunUpdate(BaseModel):
    """Model for updating a workflow job run."""
    run_name: Optional[str] = None
    life_cycle_state: Optional[str] = None
    result_state: Optional[str] = None
    state_message: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    duration_ms: Optional[int] = None
    notified_at: Optional[datetime] = None


class WorkflowJobRun(WorkflowJobRunBase):
    """Full model for workflow job run (includes all fields)."""
    id: str
    workflow_installation_id: str
    notified_at: Optional[datetime] = None
    discovered_at: datetime
    last_updated_at: datetime

    class Config:
        from_attributes = True
