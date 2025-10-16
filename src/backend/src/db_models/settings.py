import json
import uuid
from sqlalchemy import Column, String, Text, func, UniqueConstraint, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB # Use JSONB if available, falls back for others

from src.common.database import Base

class AppRoleDb(Base):
    __tablename__ = 'app_roles'

    # Use UUID for primary key, store as string
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    # Store lists/dicts as JSON strings or Text
    # Using Text for broader compatibility, can switch to JSONB if needed
    assigned_groups = Column(Text, nullable=False, default='[]')
    feature_permissions = Column(Text, nullable=False, default='{}')
    home_sections = Column(Text, nullable=False, default='[]')
    # Approval privileges JSON (e.g., {"CONTRACTS": true, "PRODUCTS": true})
    approval_privileges = Column(Text, nullable=False, default='{}')
    
    # Deployment policy JSON (catalog/schema restrictions, nullable for backward compatibility)
    deployment_policy = Column(Text, nullable=True, comment="Deployment policy for this role (catalog/schema restrictions)")

    # Add timestamp columns - Make them nullable
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    # Define uniqueness constraint on 'name' if desired
    __table_args__ = (UniqueConstraint('name', name='uq_app_roles_name'),)

    def __repr__(self):
        return f"<AppRoleDb(id='{self.id}', name='{self.name}')>" 