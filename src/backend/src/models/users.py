from pydantic import BaseModel
from typing import Optional, List, Dict

from src.common.features import FeatureAccessLevel


class UserInfo(BaseModel):
    """Model representing user information from request headers"""
    email: str | None
    username: str | None
    user: str | None
    ip: str | None
    groups: Optional[List[str]] = None

# Type alias for the permissions response
UserPermissions = Dict[str, FeatureAccessLevel]
