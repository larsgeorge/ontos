import uuid
from sqlalchemy import Column, String, Text, ForeignKey, UniqueConstraint, Enum as SQLAlchemyEnum, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # For explicit PostgreSQL UUID type if desired
from sqlalchemy.sql import func

from api.common.database import Base
# Assuming TagStatus and TagAccessLevel might be used for default values or constraints later,
# but their primary definition will be in Pydantic models.
# For DB, we'll typically store enums as strings.

# Enum for Tag Status (can be used for default values or constraints if needed at DB level)
# For simplicity, this will be a string column in DB, validated by Pydantic.

# Default namespace name, can be used in default value functions if needed
DEFAULT_NAMESPACE_NAME = "default"

class TagNamespaceDb(Base):
    __tablename__ = "tag_namespaces"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    created_by = Column(String, nullable=True) # User email or ID
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tags = relationship("TagDb", back_populates="namespace", cascade="all, delete-orphan")
    permissions = relationship("TagNamespacePermissionDb", back_populates="namespace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TagNamespaceDb(id={self.id}, name='{self.name}')>"

class TagDb(Base):
    __tablename__ = "tags"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    possible_values = Column(JSON, nullable=True) # Store as JSON, expecting a list of strings
    status = Column(String, nullable=False, default="active", index=True) # e.g., active, draft, deprecated
    version = Column(String, nullable=True) # e.g., v1.0

    namespace_id = Column(PG_UUID(as_uuid=True), ForeignKey("tag_namespaces.id"), nullable=False)
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey("tags.id"), nullable=True) # For hierarchical tags

    created_by = Column(String, nullable=True) # User email or ID
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    namespace = relationship("TagNamespaceDb", back_populates="tags")
    parent = relationship("TagDb", remote_side=[id], back_populates="children", foreign_keys=[parent_id])
    children = relationship("TagDb", back_populates="parent", foreign_keys=[parent_id])

    # Unique constraint for tag name within a namespace
    __table_args__ = (UniqueConstraint("namespace_id", "name", name="uq_tag_namespace_name"),)

    def __repr__(self):
        return f"<TagDb(id={self.id}, name='{self.name}', namespace_id='{self.namespace_id}')>"

class TagNamespacePermissionDb(Base):
    __tablename__ = "tag_namespace_permissions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    namespace_id = Column(PG_UUID(as_uuid=True), ForeignKey("tag_namespaces.id"), nullable=False)
    # Using string for group_id to accommodate various identity systems (e.g., Databricks group names or UUIDs)
    group_id = Column(String, nullable=False, index=True) 
    access_level = Column(String, nullable=False) # e.g., "read_only", "read_write", "admin"

    created_by = Column(String, nullable=True) # User email or ID
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    namespace = relationship("TagNamespaceDb", back_populates="permissions")

    __table_args__ = (UniqueConstraint("namespace_id", "group_id", name="uq_permission_namespace_group"),)

    def __repr__(self):
        return f"<TagNamespacePermissionDb(id={self.id}, namespace_id='{self.namespace_id}', group_id='{self.group_id}', access_level='{self.access_level}')>"

class EntityTagAssociationDb(Base):
    __tablename__ = "entity_tag_associations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag_id = Column(PG_UUID(as_uuid=True), ForeignKey("tags.id"), nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True) # ID of the tagged entity (e.g., DataProduct ID)
    entity_type = Column(String, nullable=False, index=True) # Type of the entity (e.g., "data_product")
    
    # Optional value assigned from the tag's 'possible_values'
    assigned_value = Column(String, nullable=True) 
    
    assigned_by = Column(String, nullable=True) # User email or ID
    assigned_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships (optional, depending on query needs)
    # tag = relationship("TagDb") 
    # Consider a generic way to link back to entities if needed, or handle at application level.

    __table_args__ = (
        UniqueConstraint("tag_id", "entity_id", "entity_type", name="uq_entity_tag_assignment"),
    )

    def __repr__(self):
        return f"<EntityTagAssociationDb(id={self.id}, tag_id='{self.tag_id}', entity_id='{self.entity_id}', entity_type='{self.entity_type}')>" 