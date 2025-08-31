import uuid
from sqlalchemy import Column, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP, Index

from api.common.database import Base


class RichTextMetadataDb(Base):
    __tablename__ = "rich_text_metadata"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)  # data_domain | data_product | data_contract

    title = Column(String, nullable=False)
    short_description = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=False)

    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rich_text_entity", "entity_type", "entity_id"),
    )


class LinkMetadataDb(Base):
    __tablename__ = "link_metadata"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)

    title = Column(String, nullable=False)
    short_description = Column(Text, nullable=True)
    url = Column(String, nullable=False)

    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_link_entity", "entity_type", "entity_id"),
    )


class DocumentMetadataDb(Base):
    __tablename__ = "document_metadata"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)

    title = Column(String, nullable=False)
    short_description = Column(Text, nullable=True)

    original_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    storage_path = Column(String, nullable=False)  # Path in Databricks Volume

    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_document_entity", "entity_type", "entity_id"),
    )


