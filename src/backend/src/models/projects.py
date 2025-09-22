from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import json

from .teams import TeamSummary


class ProjectBase(BaseModel):
    """Base model for projects"""
    name: str = Field(..., min_length=1, description="Unique name of the project")
    title: Optional[str] = Field(None, description="Display title for the project")
    description: Optional[str] = Field(None, description="Optional description of the project")
    tags: Optional[List[str]] = Field(None, description="Optional list of tags")
    metadata: Optional[dict] = Field(None, description="Optional metadata (links, images, etc.)")


class ProjectCreate(ProjectBase):
    """Model for creating projects"""
    team_ids: Optional[List[str]] = Field(None, description="Optional list of team IDs to assign to project")


class ProjectUpdate(BaseModel):
    """Model for updating projects"""
    name: Optional[str] = Field(None, min_length=1, description="Updated name of the project")
    title: Optional[str] = Field(None, description="Updated display title")
    description: Optional[str] = Field(None, description="Updated description")
    tags: Optional[List[str]] = Field(None, description="Updated list of tags")
    metadata: Optional[dict] = Field(None, description="Updated metadata")


class ProjectTeamAssignment(BaseModel):
    """Model for project-team assignments"""
    team_id: str = Field(..., description="Team ID to assign/remove")


class ProjectRead(ProjectBase):
    """Model for reading projects"""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    teams: List[TeamSummary] = Field(default_factory=list, description="Assigned teams")

    # Field validators to parse JSON strings from database
    @field_validator('tags', mode='before')
    def parse_tags(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            return []
        return value

    @field_validator('metadata', mode='before')
    def parse_metadata(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            return {}
        return value

    # Custom property to handle mapping from database field
    @classmethod
    def model_validate(cls, obj, **kwargs):
        if hasattr(obj, 'extra_metadata'):
            obj.metadata = obj.extra_metadata
        return super().model_validate(obj, **kwargs)

    model_config = {
        "from_attributes": True
    }


class ProjectSummary(BaseModel):
    """Summary model for projects (for lists/dropdowns)"""
    id: str
    name: str
    title: Optional[str] = None
    team_count: int = Field(0, description="Number of assigned teams")

    model_config = {
        "from_attributes": True
    }


class UserProjectAccess(BaseModel):
    """Model for user's accessible projects"""
    projects: List[ProjectSummary] = Field(default_factory=list, description="Projects user has access to")
    current_project_id: Optional[str] = Field(None, description="Currently selected project ID")


class ProjectContext(BaseModel):
    """Model for setting project context"""
    project_id: Optional[str] = Field(None, description="Project ID to set as current (null for no project)")