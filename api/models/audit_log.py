import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

# Base properties shared by all audit log models
class AuditLogBase(BaseModel):
    username: str
    ip_address: Optional[str] = None
    feature: str
    action: str
    success: bool = True
    details: Optional[Dict[str, Any]] = None

# Properties to receive via API on creation (internal use)
class AuditLogCreate(AuditLogBase):
    pass # All fields come from AuditLogBase

# Properties properties stored in DB
class AuditLogInDB(AuditLogBase):
    id: uuid.UUID
    timestamp: datetime

    model_config = {
        "from_attributes": True # Pydantic v2 alias for orm_mode
    }

# Properties to return to client
class AuditLogRead(AuditLogInDB):
    pass # Inherits all fields from AuditLogInDB

# Model for paginated response
class PaginatedAuditLogResponse(BaseModel):
    total: int
    items: list[AuditLogRead] 