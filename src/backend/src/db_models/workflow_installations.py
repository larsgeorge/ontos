import uuid
from sqlalchemy import Column, String, Text, BigInteger, func, TIMESTAMP
from sqlalchemy.orm import relationship

from src.common.database import Base


class WorkflowInstallationDb(Base):
    __tablename__ = 'workflow_installations'

    # Use UUID for primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Workflow identifier (matches directory name in workflows/)
    workflow_id = Column(String, nullable=False, unique=True)

    # Workflow display name
    name = Column(String, nullable=False)

    # Databricks job ID (returned from jobs.create()) - BigInteger for large IDs
    job_id = Column(BigInteger, nullable=False)

    # Workspace ID for multi-workspace support
    workspace_id = Column(String, nullable=True)

    # Status: 'installed', 'failed', 'updating', 'uninstalling'
    status = Column(String, nullable=False, default='installed')

    # Error message if installation failed
    error_message = Column(Text, nullable=True)

    # Last known job state (for background polling)
    last_job_state = Column(Text, nullable=True)  # JSON with lifecycle_state, result_state, etc.

    # Timestamps
    installed_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_polled_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationship to job runs
    job_runs = relationship("WorkflowJobRunDb", back_populates="workflow_installation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<WorkflowInstallationDb(id='{self.id}', workflow_id='{self.workflow_id}', job_id={self.job_id}, status='{self.status}')>"
