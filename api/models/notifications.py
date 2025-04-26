import json
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, ConfigDict, field_validator


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
