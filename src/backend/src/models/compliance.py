from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class CompliancePolicy(BaseModel):
    id: str = Field(..., description="Unique identifier for the policy")
    name: str = Field(..., description="Name of the compliance policy")
    description: str = Field(..., description="Description of what the policy checks")
    rule: str = Field(..., description="Policy rule using the compliance DSL")
    compliance: float = Field(..., description="Current compliance score (0-100)")
    history: List[float] = Field(default_factory=list, description="Historical compliance scores")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True, description="Whether the policy is active")
    severity: str = Field(default="medium", description="Severity level: low, medium, high")
    category: str = Field(default="general", description="Category of the policy")
