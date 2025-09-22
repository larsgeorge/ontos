import uuid
from sqlalchemy import Column, String, Text, Enum, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP
import enum

from src.common.database import Base


class CommentStatus(enum.Enum):
    ACTIVE = "active"
    DELETED = "deleted"


class CommentDb(Base):
    __tablename__ = "comments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)  # data_domain | data_product | data_contract | etc.

    title = Column(String, nullable=True)  # Optional title for comment
    comment = Column(Text, nullable=False)
    audience = Column(Text, nullable=True)  # JSON array of group names who can see the comment
    status = Column(Enum(CommentStatus), nullable=False, default=CommentStatus.ACTIVE)

    # Project relationship (nullable for backward compatibility)
    project_id = Column(String, nullable=True, index=True)  # Note: Removed ForeignKey to avoid circular import
    
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_comments_entity", "entity_type", "entity_id"),
        Index("ix_comments_status", "status"),
        Index("ix_comments_created_at", "created_at"),
    )