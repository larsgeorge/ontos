import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.common.features import FeatureAccessLevel, APP_FEATURES


class JobCluster(BaseModel):
    id: str
    name: str
    node_type_id: str
    autoscale: bool
    min_workers: int
    max_workers: int
    status: str
    workspace_id: str

# --- RBAC Models ---

# Enum for Home Sections (kept in sync with frontend)
class HomeSection(str, Enum):
    REQUIRED_ACTIONS = "REQUIRED_ACTIONS"
    DATA_CURATION = "DATA_CURATION"
    DISCOVERY = "DISCOVERY"

# Approval entities for route-agnostic approval privileges
class ApprovalEntity(str, Enum):
    DOMAINS = "DOMAINS"
    CONTRACTS = "CONTRACTS"
    PRODUCTS = "PRODUCTS"
    BUSINESS_TERMS = "BUSINESS_TERMS"
    ASSET_REVIEWS = "ASSET_REVIEWS"

# Base model for common fields
class AppRoleBase(BaseModel):
    name: str
    description: Optional[str] = None
    assigned_groups: List[str] = Field(default_factory=list)
    feature_permissions: Dict[str, FeatureAccessLevel] = Field(default_factory=dict)
    home_sections: List[HomeSection] = Field(default_factory=list, description="Home sections visible for this role")
    approval_privileges: Dict[ApprovalEntity, bool] = Field(default_factory=dict, description="Entity-level approval capabilities")

# Model for creating a new role (input)
class AppRoleCreate(AppRoleBase):
    # Inherits name, description, assigned_groups, feature_permissions
    # No id, created_at, updated_at needed here
    pass

# Model for updating a role (input, allows partial updates)
class AppRoleUpdate(AppRoleBase):
    # Make fields optional for partial updates
    name: Optional[str] = None
    description: Optional[str] = None
    assigned_groups: Optional[List[str]] = None
    feature_permissions: Optional[Dict[str, FeatureAccessLevel]] = None
    home_sections: Optional[List[HomeSection]] = None
    approval_privileges: Optional[Dict[ApprovalEntity, bool]] = None

# Model representing a role as returned by the API (output)
class AppRole(AppRoleBase):
    id: UUID # Required field for output
    # Inherits name, description, assigned_groups, feature_permissions
    # Add created_at and updated_at if they are in your DB model and you want to return them
    # created_at: Optional[datetime] = None
    # updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True # Enable ORM mode (formerly orm_mode)
    }

# --- Role Request Handling Model --- 

class HandleRoleRequest(BaseModel):
    """Model for the request body when handling a role access request."""
    requester_email: str = Field(..., description="Email address of the user who requested the role.")
    role_id: str = Field(..., description="ID of the role being requested.")
    approved: bool = Field(..., description="Whether the request was approved or denied.")
    message: Optional[str] = Field(None, description="Optional message from the admin to the requester.")
