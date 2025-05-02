from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text
# Remove UUID import as we'll use String
# from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.sql import func
# Remove local declarative_base import and local Base definition
# from sqlalchemy.orm import declarative_base

# Import the shared Base from the common database module
from api.common.database import Base 

# Base = declarative_base()

class DataDomain(Base):
    __tablename__ = 'data_domains'

    # Use String for ID, default generates UUID string
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    # Store owners and tags as String, assuming JSON serialization happens elsewhere
    owner = Column(String, nullable=False) # Represents List[str]
    tags = Column(String, nullable=True) # Represents List[str]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(String, nullable=False) # Store user ID (e.g., email)

    def __repr__(self):
        return f"<DataDomain(id={self.id}, name='{self.name}')>" 