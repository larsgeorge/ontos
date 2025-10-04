import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.common.manager_dependencies import get_jobs_manager
from src.common.database import get_db
from src.controller.jobs_manager import JobsManager
from src.repositories.workflow_job_runs_repository import workflow_job_run_repo
from src.models.workflow_job_runs import WorkflowJobRun

# Configure logging
from src.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])

@router.get('/jobs/{run_id}/status')
async def get_job_status(
    run_id: int,
    jobs_manager: JobsManager = Depends(get_jobs_manager)
) -> Dict[str, Any]:
    """Get status of a job run."""
    try:
        status = jobs_manager.get_job_status(run_id=run_id)
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job run {run_id} not found"
            )
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status for run {run_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )

@router.get('/jobs/runs')
async def get_job_runs(
    workflow_installation_id: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
) -> List[WorkflowJobRun]:
    """Get recent job runs, optionally filtered by workflow installation.

    Args:
        workflow_installation_id: Optional filter by workflow installation
        limit: Maximum number of runs to return (default 10, max 100)

    Returns:
        List of job runs ordered by start_time descending
    """
    try:
        # Cap limit at 100
        limit = min(limit, 100)

        runs = workflow_job_run_repo.get_recent_runs(
            db,
            workflow_installation_id=workflow_installation_id,
            limit=limit
        )

        # Convert to Pydantic models
        return [WorkflowJobRun.from_orm(run) for run in runs]
    except Exception as e:
        logger.error(f"Error getting job runs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job runs: {str(e)}"
        )

@router.post('/jobs/{run_id}/cancel')
async def cancel_job(
    run_id: int,
    jobs_manager: JobsManager = Depends(get_jobs_manager)
) -> Dict[str, bool]:
    """Cancel a running job."""
    try:
        jobs_manager.cancel_run(run_id=run_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error cancelling job run {run_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job run: {str(e)}"
        )

def register_routes(app):
    """Register job routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Job routes registered")
