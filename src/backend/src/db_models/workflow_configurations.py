"""
Database models for workflow configurations.

Stores user-configurable parameters for background job workflows.
"""

import uuid
from sqlalchemy import Column, String, Text, func, TIMESTAMP

from src.common.database import Base


class WorkflowConfigurationDb(Base):
    """Store workflow-specific configuration parameters"""
    __tablename__ = 'workflow_configurations'

    # Use UUID for primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Workflow identifier (matches directory name in workflows/)
    workflow_id = Column(String, nullable=False, unique=True, index=True)

    # JSON configuration values (parameter name -> value mapping)
    configuration = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<WorkflowConfigurationDb(id='{self.id}', workflow_id='{self.workflow_id}')>"

