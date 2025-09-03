import json
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, ConfigDict, field_validator


class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ACTION_REQUIRED = "action_required"
    JOB_PROGRESS = "job_progress"

class Notification(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    type: NotificationType
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    message: Optional[str] = None  # Alternative to description
    link: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    read: bool = False
    can_delete: bool = True
    recipient: Optional[str] = None
    target_roles: Optional[List[str]] = None  # For role-based notifications
    action_type: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None  # Additional data for job progress etc.

    @field_validator('action_payload', mode='before')
    @classmethod
    def parse_action_payload_json(cls, v: Any) -> Optional[Dict[str, Any]]:
        """Parse action_payload if it's a JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Handle error: return None, raise specific error, or return original string?
                # Returning None seems reasonable if parsing fails.
                return None 
        # If it's already a dict or None, return it as is
        return v

    @field_validator('data', mode='before')
    @classmethod
    def parse_data_json(cls, v: Any) -> Optional[Dict[str, Any]]:
        """Parse data if it's a JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v

class NotificationUpdate(BaseModel):
    """Model for updating notification fields."""
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    message: Optional[str] = None
    link: Optional[str] = None
    read: Optional[bool] = None
    data: Optional[Dict[str, Any]] = None
    updated_at: Optional[datetime] = None
