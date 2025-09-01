from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class CatalogItem(BaseModel):
    """Represents a catalog item (table, view, etc.)"""
    name: str
    type: str  # table, view, etc.
    catalog: str
    schema: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    owner: Optional[str] = None
    tags: Dict[str, str] = {}
    properties: Dict[str, Any] = {}

class CatalogOperation(BaseModel):
    """Represents a catalog operation (copy, move, etc.)"""
    operation_type: str  # copy, move, etc.
    source: CatalogItem
    target: CatalogItem
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
