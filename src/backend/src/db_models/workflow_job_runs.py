import uuid
from sqlalchemy import Column, String, Text, BigInteger, func, TIMESTAMP, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.common.database import Base


class WorkflowJobRunDb(Base):
    __tablename__ = 'workflow_job_runs'

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to workflow installation
    workflow_installation_id = Column(String, ForeignKey('workflow_installations.id', ondelete='CASCADE'), nullable=False)

    # Databricks run ID (unique across all jobs)
    run_id = Column(BigInteger, unique=True, nullable=False, index=True)

    # Run name (optional, from Databricks)
    run_name = Column(String, nullable=True)

    # Run state
    life_cycle_state = Column(String, nullable=True)  # PENDING, RUNNING, TERMINATING, TERMINATED, SKIPPED
    result_state = Column(String, nullable=True)  # SUCCESS, FAILED, CANCELED, TIMEDOUT
    state_message = Column(Text, nullable=True)

    # Timing (Unix timestamps in milliseconds from Databricks)
    start_time = Column(BigInteger, nullable=True)
    end_time = Column(BigInteger, nullable=True)
    duration_ms = Column(BigInteger, nullable=True)  # Calculated: end_time - start_time

    # Notification tracking
    notified_at = Column(TIMESTAMP(timezone=True), nullable=True)  # When we sent notification for failure

    # Audit timestamps
    discovered_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship to workflow installation
    workflow_installation = relationship("WorkflowInstallationDb", back_populates="job_runs")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_workflow_job_runs_installation_start', 'workflow_installation_id', 'start_time'),
        Index('idx_workflow_job_runs_result_state', 'result_state'),
    )

    def __repr__(self):
        return f"<WorkflowJobRunDb(run_id={self.run_id}, state={self.life_cycle_state}/{self.result_state})>"
