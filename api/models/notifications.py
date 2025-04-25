from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict


class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ACTION_REQUIRED = "action_required"

class Notification(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    type: NotificationType
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    read: bool = False
    can_delete: bool = True
    recipient: Optional[str] = None
    action_type: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
