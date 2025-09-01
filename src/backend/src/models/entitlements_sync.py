from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class EntitlementSyncConfig(BaseModel):
    id: str = Field(..., description="Unique identifier for the sync configuration")
    name: str = Field(..., description="Name of the sync configuration")
    connection_id: str = Field(..., description="ID of the Unity Catalog connection to use")
    schedule: str = Field(..., description="Cron expression for the sync schedule")
    is_enabled: bool = Field(default=True, description="Whether the sync is enabled")
    catalogs: List[str] = Field(default=[], description="List of catalogs to sync. If empty, all catalogs are synced")
    last_sync: Optional[datetime] = Field(None, description="Timestamp of the last successful sync")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "sync-1",
                "name": "Snowflake Production",
                "connection_id": "conn-123",
                "schedule": "0 0 * * *",
                "is_enabled": True,
                "catalogs": ["prod", "analytics"],
                "last_sync": "2024-03-29T12:00:00Z",
                "created_at": "2024-03-29T10:00:00Z",
                "updated_at": "2024-03-29T10:00:00Z"
            }
        }
    }
