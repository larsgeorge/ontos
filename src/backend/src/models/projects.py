from typing import List, Optional, Union
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import json

from .teams import TeamSummary
from .tags import AssignedTag, AssignedTagCreate


class ProjectBase(BaseModel):
    """Base model for projects"""
    name: str = Field(..., min_length=1, description="Unique name of the project")
    title: Optional[str] = Field(None, description="Display title for the project")
    description: Optional[str] = Field(None, description="Optional description of the project")
    owner_team_id: Optional[str] = Field(None, description="UUID of the team that manages this project")
    tags: Optional[List[AssignedTagCreate]] = Field(None, description="Optional list of rich tags with metadata")
    metadata: Optional[dict] = Field(None, description="Optional metadata (links, images, etc.)")
    project_type: Optional[str] = Field(None, description="Type of project: PERSONAL or TEAM")


class ProjectCreate(ProjectBase):
    """Model for creating projects"""
    team_ids: Optional[List[str]] = Field(None, description="Optional list of team IDs to assign to project")


class ProjectUpdate(BaseModel):
    """Model for updating projects"""
    name: Optional[str] = Field(None, min_length=1, description="Updated name of the project")
    title: Optional[str] = Field(None, description="Updated display title")
    description: Optional[str] = Field(None, description="Updated description")
    owner_team_id: Optional[str] = Field(None, description="Updated UUID of the team that manages this project")
    tags: Optional[List[AssignedTagCreate]] = Field(None, description="Updated list of rich tags with metadata")
    metadata: Optional[dict] = Field(None, description="Updated metadata")
    project_type: Optional[str] = Field(None, description="Updated project type: PERSONAL or TEAM")


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
    owner_team_name: Optional[str] = Field(None, description="Name of the team that manages this project")
    teams: List[TeamSummary] = Field(default_factory=list, description="Assigned teams")

    # Override tags field to return AssignedTag objects
    tags: Optional[List[AssignedTag]] = Field(default_factory=list, description="List of assigned tags with rich metadata")

    # Field validators to parse JSON strings from database
    @field_validator('tags', mode='before')
    def parse_tags(cls, value):
        if value is None:
            return []
        # If it's already a list of AssignedTag objects, return as-is
        if isinstance(value, list) and value and hasattr(value[0], 'tag_id'):
            return value
        # Legacy support for JSON strings (should not be used anymore)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            return []
        return value or []

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


class ProjectAccessRequest(BaseModel):
    """Model for requesting access to a project"""
    project_id: str = Field(..., description="Project ID to request access to")
    message: Optional[str] = Field(None, description="Optional message explaining why access is needed")


class ProjectAccessRequestResponse(BaseModel):
    """Response model for project access requests"""
    message: str = Field(..., description="Status message")
    project_name: str = Field(..., description="Name of the project access was requested for")