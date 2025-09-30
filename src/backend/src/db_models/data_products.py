from sqlalchemy import Column, String, DateTime, Text, Boolean, func, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID # Generic UUID type
import uuid
import json # For links/custom

from src.common.database import Base

# --- Association Table for Many-to-Many Tags ---
# data_product_tag_association = Table(
#     'data_product_tag_association', Base.metadata,
#     Column('data_product_id', String, ForeignKey('data_products.id'), primary_key=True),
#     Column('tag_id', String, ForeignKey('tags.id'), primary_key=True)
# )

# --- Tag Table (Corrected for Databricks Unique Constraint) ---
# class Tag(Base):
#     __tablename__ = 'tags'
#     id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
#     
#     # Define uniqueness using a table-level constraint
#     __table_args__ = (UniqueConstraint('name', name='uq_tags_name'),)
#     
#     def __repr__(self):
#         return f"<Tag(id='{self.id}', name='{self.name}')>"

# --- Main DataProduct Table (Corrected Name & Relationships) ---
class DataProductDb(Base):
    """SQLAlchemy model for Data Products (Normalized)."""
    __tablename__ = 'data_products'

    # Core Fields
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataProductSpecification = Column(String, nullable=False, default="0.0.1")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    version = Column(String, nullable=False, default="1.0.0", index=True)
    product_type = Column(String, nullable=True, index=True)

    # Project relationship (nullable for backward compatibility)
    project_id = Column(String, ForeignKey('projects.id'), nullable=True, index=True)

    # Relationships (Corrected names)
    info = relationship("InfoDb", back_populates="data_product", uselist=False, cascade="all, delete-orphan")
    inputPorts = relationship("InputPortDb", back_populates="data_product", cascade="all, delete-orphan", lazy="selectin")
    outputPorts = relationship("OutputPortDb", back_populates="data_product", cascade="all, delete-orphan", lazy="selectin")
    # tags = relationship("Tag", secondary=data_product_tag_association, backref="data_products", lazy="selectin") # REMOVED relationship to old Tag model

    # Kept as JSON Strings
    links = Column(String, nullable=True, default='{}')
    custom = Column(String, nullable=True, default='{}')

    def __repr__(self):
        title = self.info.title if self.info else 'N/A'
        return f"<DataProductDb(id='{self.id}', title='{title}')>"

# --- Info Table (Restore index=True) ---
class InfoDb(Base):
    __tablename__ = 'data_product_info'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    data_product_id = Column(String, ForeignKey('data_products.id'), unique=True, nullable=False)
    
    title = Column(String, nullable=False)
    owner_team_id = Column(String, ForeignKey('teams.id'), nullable=True, index=True)  # Team UUID reference
    domain = Column(String, nullable=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=True, index=True)
    archetype = Column(String, nullable=True, index=True)
    
    # Relationships
    owner_team = relationship("TeamDb", foreign_keys=[owner_team_id])
    data_product = relationship("DataProductDb", back_populates="info")

# --- InputPort Table (Corrected relationship) ---
class InputPortDb(Base):
    __tablename__ = 'input_ports'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    data_product_id = Column(String, ForeignKey('data_products.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    port_type = Column('type', String, nullable=True) # Renamed to avoid keyword conflict
    asset_type = Column(String, nullable=True, index=True) # New: Asset Type
    asset_identifier = Column(String, nullable=True, index=True) # New: Asset Identifier
    location = Column(String, nullable=True)
    
    sourceSystemId = Column(String, nullable=False)
    sourceOutputPortId = Column(String, nullable=True) # Nullable for external sources or if link not specified
    links = Column(String, nullable=True, default='{}') # JSON String
    custom = Column(String, nullable=True, default='{}') # JSON String
    # tags: Moved to EntityTagAssociationDb for rich tag support
    
    # Relationship back to DataProductDb (Corrected reference)
    data_product = relationship("DataProductDb", back_populates="inputPorts")
    
# --- OutputPort Table (Restore index=True) ---
class OutputPortDb(Base):
    __tablename__ = 'output_ports'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    data_product_id = Column(String, ForeignKey('data_products.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    port_type = Column('type', String, nullable=True) # Renamed to avoid keyword conflict
    asset_type = Column(String, nullable=True, index=True) # New: Asset Type
    asset_identifier = Column(String, nullable=True, index=True) # New: Asset Identifier
    location = Column(String, nullable=True)
    
    status = Column(String, nullable=True, index=True)
    server = Column(String, nullable=True, default='{}') # JSON String
    containsPii = Column(Boolean, default=False)
    autoApprove = Column(Boolean, default=False)
    dataContractId = Column(String, nullable=True)
    links = Column(String, nullable=True, default='{}') # JSON String
    custom = Column(String, nullable=True, default='{}') # JSON String
    # tags: Moved to EntityTagAssociationDb for rich tag support
    
    # Relationship back to DataProductDb (Corrected reference)
    data_product = relationship("DataProductDb", back_populates="outputPorts") 