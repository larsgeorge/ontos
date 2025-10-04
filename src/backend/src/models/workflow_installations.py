from datetime import datetime
from pydantic import BaseModel


class WorkflowInstallation(BaseModel):
    id: str = None
    workflow_id: str
    name: str
    job_id: int
    workspace_id: str = None
    status: str
    installed_at: datetime
    updated_at: datetime
