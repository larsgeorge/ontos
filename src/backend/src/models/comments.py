from __future__ import annotations
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CommentStatus(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"


class CommentBase(BaseModel):
    entity_id: str
    entity_type: str = Field(..., description="Type of entity being commented on (data_domain, data_product, data_contract, etc.)")
    title: Optional[str] = Field(None, max_length=255, description="Optional title for the comment")
    comment: str = Field(..., min_length=1, description="The comment content")
    audience: Optional[List[str]] = Field(None, description="List of audience tokens: plain groups, 'team:<team_id>', or 'role:<role_name>'. If null, visible to all users with access to the entity")
    project_id: Optional[str] = Field(None, description="Project ID to scope the comment. If null, visible globally (admin/owning team only)")


class CommentCreate(CommentBase):
    pass


class CommentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = Field(None, min_length=1)
    audience: Optional[List[str]] = None


class Comment(CommentBase):
    id: UUID
    status: CommentStatus = CommentStatus.ACTIVE
    project_id: Optional[str] = None
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class CommentListResponse(BaseModel):
    """Response model for listing comments with metadata"""
    comments: List[Comment]
    total_count: int
    visible_count: int  # Number of comments visible to current user