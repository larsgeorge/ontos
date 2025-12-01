"""
Genie Spaces API Models

This module defines Pydantic models for Genie Space API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class GenieSpaceCreate(BaseModel):
    """Model for creating a new Genie Space record."""
    space_id: str
    space_name: str
    space_url: Optional[str] = None
    status: str = "active"
    datasets: Optional[List[str]] = None
    product_ids: Optional[List[str]] = None
    instructions: Optional[str] = None
    created_by: Optional[str] = None
    error_message: Optional[str] = None


class GenieSpaceUpdate(BaseModel):
    """Model for updating an existing Genie Space record."""
    space_name: Optional[str] = None
    space_url: Optional[str] = None
    status: Optional[str] = None
    datasets: Optional[List[str]] = None
    instructions: Optional[str] = None
    error_message: Optional[str] = None


class GenieSpace(BaseModel):
    """Model for Genie Space API responses."""
    id: str
    space_id: str
    space_name: str
    space_url: Optional[str]
    status: str
    datasets: Optional[List[str]]
    product_ids: Optional[List[str]]
    instructions: Optional[str]
    created_by: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
