from __future__ import annotations
from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class RichTextBase(BaseModel):
    entity_id: str
    entity_type: str = Field(..., pattern=r"^(data_domain|data_product|data_contract)$")
    title: str = Field(..., min_length=1, max_length=255)
    short_description: Optional[str] = Field(None, max_length=1000)
    content_markdown: str


class RichTextCreate(RichTextBase):
    pass


class RichTextUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    short_description: Optional[str] = Field(None, max_length=1000)
    content_markdown: Optional[str] = None


class RichText(RichTextBase):
    id: UUID
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class LinkBase(BaseModel):
    entity_id: str
    entity_type: str = Field(..., pattern=r"^(data_domain|data_product|data_contract)$")
    title: str = Field(..., min_length=1, max_length=255)
    short_description: Optional[str] = Field(None, max_length=1000)
    url: str = Field(..., min_length=1)


class LinkCreate(LinkBase):
    pass


class LinkUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    short_description: Optional[str] = Field(None, max_length=1000)
    url: Optional[str] = Field(None, min_length=1)


class Link(LinkBase):
    id: UUID
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class DocumentBase(BaseModel):
    entity_id: str
    entity_type: str = Field(..., pattern=r"^(data_domain|data_product|data_contract)$")
    title: str = Field(..., min_length=1, max_length=255)
    short_description: Optional[str] = Field(None, max_length=1000)


class DocumentCreate(DocumentBase):
    # These are filled during upload processing
    pass


class Document(DocumentBase):
    id: UUID
    original_filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    storage_path: str
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

from pydantic import BaseModel

# Structure for returning metastore table info
class MetastoreTableInfo(BaseModel):
    catalog_name: str
    schema_name: str
    table_name: str
    full_name: str # Helper for display/selection

# Add other metadata models here later (e.g., CatalogInfo, SchemaInfo, ClusterInfo) 