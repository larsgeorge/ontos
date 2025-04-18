from pydantic import BaseModel
from typing import Optional, List


class UserInfo(BaseModel):
    """Model representing user information from request headers"""
    email: str | None
    username: str | None
    user: str | None
    ip: str | None
    groups: Optional[List[str]] = None
