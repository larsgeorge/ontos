"""
Workspace API Models

Models for Databricks workspace asset search and discovery.
"""

from typing import Optional
from pydantic import BaseModel, Field


class WorkspaceAsset(BaseModel):
    """Model representing a Databricks workspace asset (table, notebook, job, etc.)"""
    
    type: str = Field(..., description="Type of the asset (e.g., 'table', 'notebook', 'job')")
    identifier: str = Field(..., description="Unique identifier for the asset")
    name: str = Field(..., description="Display name of the asset")
    path: Optional[str] = Field(None, description="Path or location of the asset")
    url: Optional[str] = Field(None, description="URL to access the asset in Databricks workspace")
    
    class Config:
        schema_extra = {
            "example": {
                "type": "table",
                "identifier": "main.default.sales_data",
                "name": "sales_data",
                "path": "/main/default/sales_data",
                "url": None
            }
        }

