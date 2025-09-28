from typing import List, Optional, Union
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import json

from .tags import AssignedTag, AssignedTagCreate


class MemberType(str, Enum):
    """Enum for team member types"""
    USER = "user"
    GROUP = "group"


class TeamMemberBase(BaseModel):
    """Base model for team members"""
    member_type: MemberType = Field(..., description="Type of member: user or group")
    member_identifier: str = Field(..., min_length=1, description="Email for user, name for group")
    app_role_override: Optional[str] = Field(None, description="Optional app role override for this member")


class TeamMemberCreate(TeamMemberBase):
    """Model for creating team members"""
    pass


class TeamMemberUpdate(BaseModel):
    """Model for updating team members"""
    app_role_override: Optional[str] = Field(None, description="Updated app role override")


class TeamMemberRead(TeamMemberBase):
    """Model for reading team members"""
    id: str
    team_id: str
    member_name: Optional[str] = Field(None, description="Display name for the member")
    created_at: datetime
    updated_at: datetime
    added_by: str

    model_config = {
        "from_attributes": True
    }

    @field_validator('member_type', mode='before')
    @classmethod
    def convert_member_type(cls, value):
        """Convert member_type from various formats to string"""
        if value is None:
            return None

        # Handle enum objects (both Python enum and Pydantic str enum)
        if hasattr(value, 'value'):
            return value.value
        elif hasattr(value, 'name'):
            return value.name.lower() if hasattr(value.name, 'lower') else str(value.name)

        # Handle string values
        if isinstance(value, str):
            return value.lower() if value.lower() in ['user', 'group'] else value

        # Fallback - convert to string
        return str(value).lower()

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Create the instance first
        instance = super().model_validate(obj, **kwargs)
        # Set member_name to member_identifier if not already set
        if not instance.member_name and hasattr(obj, 'member_identifier'):
            instance.member_name = obj.member_identifier
        return instance


class TeamBase(BaseModel):
    """Base model for teams"""
    name: str = Field(..., min_length=1, description="Unique name of the team")
    title: Optional[str] = Field(None, description="Display title for the team")
    description: Optional[str] = Field(None, description="Optional description of the team")
    domain_id: Optional[str] = Field(None, description="Optional parent data domain ID")
    tags: Optional[List[AssignedTagCreate]] = Field(None, description="Optional list of rich tags with metadata")
    metadata: Optional[dict] = Field(None, description="Optional metadata (links, images, etc.)")


class TeamCreate(TeamBase):
    """Model for creating teams"""
    pass


class TeamUpdate(BaseModel):
    """Model for updating teams"""
    name: Optional[str] = Field(None, min_length=1, description="Updated name of the team")
    title: Optional[str] = Field(None, description="Updated display title")
    description: Optional[str] = Field(None, description="Updated description")
    domain_id: Optional[str] = Field(None, description="Updated parent data domain ID")
    tags: Optional[List[AssignedTagCreate]] = Field(None, description="Updated list of rich tags with metadata")
    metadata: Optional[dict] = Field(None, description="Updated metadata")


class TeamRead(TeamBase):
    """Model for reading teams"""
    id: str
    domain_name: Optional[str] = Field(None, description="Domain name for display")
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    members: List[TeamMemberRead] = Field(default_factory=list, description="Team members")

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


class TeamSummary(BaseModel):
    """Summary model for teams (for lists/dropdowns)"""
    id: str
    name: str
    title: Optional[str] = None
    domain_id: Optional[str] = None
    member_count: int = Field(0, description="Number of team members")

    model_config = {
        "from_attributes": True
    }