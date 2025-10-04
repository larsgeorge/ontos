from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.common.repository import CRUDBase
from src.db_models.workflow_job_runs import WorkflowJobRunDb
from src.models.workflow_job_runs import WorkflowJobRun, WorkflowJobRunCreate, WorkflowJobRunUpdate
from src.common.logging import get_logger

logger = get_logger(__name__)


class WorkflowJobRunRepository(CRUDBase[WorkflowJobRunDb, WorkflowJobRunCreate, WorkflowJobRunUpdate]):
    """Repository for WorkflowJobRun CRUD operations."""

    def get_by_run_id(self, db: Session, *, run_id: int) -> Optional[WorkflowJobRunDb]:
        """Retrieves a job run by Databricks run_id."""
        return db.query(self.model).filter(self.model.run_id == run_id).first()

    def get_recent_runs(
        self,
        db: Session,
        *,
        workflow_installation_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 10
    ) -> List[WorkflowJobRunDb]:
        """Retrieves recent job runs, optionally filtered by workflow installation or workflow ID.

        Args:
            db: Database session
            workflow_installation_id: Optional filter by workflow installation UUID
            workflow_id: Optional filter by workflow ID (will look up installation)
            limit: Maximum number of runs to return (default 10)

        Returns:
            List of job runs ordered by start_time descending
        """
        from src.db_models.workflow_installations import WorkflowInstallationDb

        query = db.query(self.model)

        # If workflow_id is provided, join with installations to filter
        if workflow_id:
            query = query.join(
                WorkflowInstallationDb,
                self.model.workflow_installation_id == WorkflowInstallationDb.id
            ).filter(WorkflowInstallationDb.workflow_id == workflow_id)
            logger.debug(f"Filtering runs by workflow_id: {workflow_id}")
        elif workflow_installation_id:
            query = query.filter(self.model.workflow_installation_id == workflow_installation_id)
            logger.debug(f"Filtering runs by workflow_installation_id: {workflow_installation_id}")

        results = query.order_by(desc(self.model.start_time)).limit(limit).all()
        logger.info(f"get_recent_runs returned {len(results)} runs (workflow_id={workflow_id}, installation_id={workflow_installation_id}, limit={limit})")
        return results

    def mark_as_notified(self, db: Session, *, run_id: int) -> Optional[WorkflowJobRunDb]:
        """Marks a job run as notified by setting notified_at timestamp.

        Args:
            db: Database session
            run_id: Databricks run ID

        Returns:
            Updated job run record, or None if not found
        """
        run = self.get_by_run_id(db, run_id=run_id)
        if not run:
            return None

        run.notified_at = datetime.utcnow()
        db.commit()
        db.refresh(run)
        logger.info(f"Marked run {run_id} as notified")
        return run

    def upsert_run(
        self,
        db: Session,
        *,
        run_id: int,
        workflow_installation_id: str,
        run_data: dict
    ) -> WorkflowJobRunDb:
        """Creates or updates a job run record.

        Args:
            db: Database session
            run_id: Databricks run ID
            workflow_installation_id: Installation ID this run belongs to
            run_data: Dictionary with run state data

        Returns:
            Created or updated job run record
        """
        logger.debug(f"Upserting run_id {run_id} with state: {run_data.get('life_cycle_state')} / {run_data.get('result_state')}")
        existing = self.get_by_run_id(db, run_id=run_id)

        # Calculate duration if we have both start and end times
        duration_ms = None
        if run_data.get('end_time') and run_data.get('start_time'):
            duration_ms = run_data['end_time'] - run_data['start_time']

        if existing:
            # Update existing record
            existing.life_cycle_state = run_data.get('life_cycle_state')
            existing.result_state = run_data.get('result_state')
            existing.state_message = run_data.get('state_message')
            existing.start_time = run_data.get('start_time')
            existing.end_time = run_data.get('end_time')
            existing.duration_ms = duration_ms
            existing.run_name = run_data.get('run_name')
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated job run {run_id}: {existing.life_cycle_state} / {existing.result_state}")
            return existing
        else:
            # Create new record
            new_run = WorkflowJobRunDb(
                workflow_installation_id=workflow_installation_id,
                run_id=run_id,
                run_name=run_data.get('run_name'),
                life_cycle_state=run_data.get('life_cycle_state'),
                result_state=run_data.get('result_state'),
                state_message=run_data.get('state_message'),
                start_time=run_data.get('start_time'),
                end_time=run_data.get('end_time'),
                duration_ms=duration_ms
            )
            db.add(new_run)
            db.commit()
            db.refresh(new_run)
            logger.info(f"Created job run record for run_id {run_id}")
            return new_run


# Create singleton instance of the repository
workflow_job_run_repo = WorkflowJobRunRepository(WorkflowJobRunDb)
