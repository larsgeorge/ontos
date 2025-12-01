"""
Genie Spaces Database Models

This module defines SQLAlchemy models for tracking Databricks Genie Spaces
created from Data Products.
"""

import uuid
from sqlalchemy import Column, String, Text, JSON, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from src.common.database import Base


class GenieSpaceDb(Base):
    """Database model for Genie Spaces."""
    __tablename__ = "genie_spaces"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id = Column(String, unique=True, nullable=False, index=True)  # Databricks space ID
    space_name = Column(String, nullable=False, index=True)
    space_url = Column(String, nullable=True)
    status = Column(String, nullable=False, index=True)  # 'active', 'failed', 'deleted'

    # Data included in space
    datasets = Column(JSON, nullable=True)  # ["catalog.schema.table1", ...]
    product_ids = Column(JSON, nullable=True)  # ["uuid1", "uuid2"]
    instructions = Column(Text, nullable=True)  # Formatted metadata context

    # Tracking
    created_by = Column(String, nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_genie_spaces_status_created_by", "status", "created_by"),
    )
