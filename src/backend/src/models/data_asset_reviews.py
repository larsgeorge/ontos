from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid

from pydantic import BaseModel, Field, EmailStr, field_validator

# --- Enums --- #
class ReviewRequestStatus(str, Enum):
    QUEUED = "queued"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review" # Similar to 'rejected' or 'requires changes'
    DENIED = "denied"
    CANCELLED = "cancelled"

class ReviewedAssetStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"

class AssetType(str, Enum):
    TABLE = "table"
    VIEW = "view"
    FUNCTION = "function"
    MODEL = "model"
    VOLUME = "volume"
    NOTEBOOK = "notebook"
    DATA_CONTRACT = "data_contract"  # For data contract reviews
    DATA_PRODUCT = "data_product"  # For data product reviews
    # Add others as needed, e.g., DASHBOARD, JOB

# --- Pydantic Models --- #

# Model for an asset being reviewed within a request
class ReviewedAsset(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for this reviewed asset entry")
    asset_fqn: str = Field(..., description="Fully qualified name of the Databricks asset (e.g., catalog.schema.table)")
    asset_type: AssetType = Field(..., description="Type of the Databricks asset")
    status: ReviewedAssetStatus = Field(default=ReviewedAssetStatus.PENDING, description="Current review status of this specific asset")
    comments: Optional[str] = Field(None, description="Reviewer comments specific to this asset")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the last update for this asset review")

    model_config = {
        "from_attributes": True
    }

# Model for creating a new review request (might have fewer fields initially)
class DataAssetReviewRequestCreate(BaseModel):
    requester_email: EmailStr
    reviewer_email: EmailStr
    asset_fqns: List[str] = Field(..., description="List of fully qualified names of assets to review")
    # We need to determine AssetType based on fqn, perhaps in the manager
    notes: Optional[str] = Field(None, description="Optional notes for the reviewer")

# Model representing a full data asset review request (including its reviewed assets)
class DataAssetReviewRequest(BaseModel):
    id: str = Field(..., description="Unique identifier for the review request")
    requester_email: EmailStr
    reviewer_email: EmailStr
    status: ReviewRequestStatus = Field(default=ReviewRequestStatus.QUEUED, description="Overall status of the review request")
    notes: Optional[str] = Field(None, description="Optional notes for the reviewer")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    assets: List[ReviewedAsset] = Field(default_factory=list, description="List of assets included in this review request")

    model_config = {
        "from_attributes": True
    }

# Model for updating the status of a review request (typically done by reviewer)
class DataAssetReviewRequestUpdateStatus(BaseModel):
    status: ReviewRequestStatus
    notes: Optional[str] = None # Allow updating notes when changing status

# Model for updating the status of a specific asset within a review (by reviewer)
class ReviewedAssetUpdate(BaseModel):
    status: ReviewedAssetStatus
    comments: Optional[str] = None

# --- LLM Analysis Models ---
class AssetAnalysisRequest(BaseModel):
    asset_content: str = Field(..., description="The content of the asset (e.g., SQL or Python code) to be analyzed.")
    asset_type: AssetType = Field(..., description="The type of asset being analyzed.")

class AssetAnalysisResponse(BaseModel):
    request_id: str = Field(..., description="The ID of the review request.")
    asset_id: str = Field(..., description="The ID of the reviewed asset.")
    analysis_summary: str = Field(..., description="The LLM-generated summary of the asset review.")
    llm_model_used: Optional[str] = Field(None, alias="model_used", description="The name of the LLM model used for analysis.")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of when the analysis was performed.")
    # Security metadata for two-phased verification
    phase1_passed: bool = Field(True, description="Whether the security check (phase 1) passed.")
    render_as_markdown: bool = Field(True, description="Whether the content is safe to render as markdown (phase 1 passed).")
    
    class Config:
        populate_by_name = True