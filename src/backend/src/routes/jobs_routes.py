from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.common.manager_dependencies import get_jobs_manager
from src.common.database import get_db
from src.controller.jobs_manager import JobsManager
from src.repositories.workflow_job_runs_repository import workflow_job_run_repo
from src.models.workflow_job_runs import WorkflowJobRun
from src.repositories.workflow_installations_repository import workflow_installation_repo

# Configure logging
from src.common.logging import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])

@router.get('/jobs/runs')
async def get_job_runs(
    workflow_installation_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
) -> List[WorkflowJobRun]:
    """Get recent job runs, optionally filtered by workflow installation or workflow ID.

    Args:
        workflow_installation_id: Optional filter by workflow installation UUID
        workflow_id: Optional filter by workflow ID (e.g., 'business-glossary-sync')
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
            workflow_id=workflow_id,
            limit=limit
        )

        logger.info(f"get_job_runs: Found {len(runs)} runs (workflow_id={workflow_id}, installation_id={workflow_installation_id})")

        # Convert to Pydantic models (Pydantic v2)
        result = [WorkflowJobRun.model_validate(run) for run in runs]
        logger.info(f"get_job_runs: Returning {len(result)} validated runs")
        return result
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


@router.get('/jobs/workflows/status')
async def get_workflow_statuses(
    jobs_manager: JobsManager = Depends(get_jobs_manager)
) -> Dict[str, Any]:
    try:
        return jobs_manager.get_workflow_statuses()
    except Exception as e:
        logger.error(f"Error getting workflow statuses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch workflow statuses")

# Non-conflicting alias to avoid path-param capture by /jobs/{run_id}/status
@router.get('/jobs/workflows/statuses')
async def get_workflow_statuses_alias(
    jobs_manager: JobsManager = Depends(get_jobs_manager)
) -> Dict[str, Any]:
    try:
        return jobs_manager.get_workflow_statuses()
    except Exception as e:
        logger.error(f"Error getting workflow statuses: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch workflow statuses")


@router.post('/jobs/workflows/{workflow_id}/start')
async def start_workflow(
    workflow_id: str,
    jobs_manager: JobsManager = Depends(get_jobs_manager),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        # Lookup installation
        inst = workflow_installation_repo.get_by_workflow_id(db=db, workflow_id=workflow_id)
        if inst is None:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not installed")
        run_id = jobs_manager.run_job(job_id=int(inst.job_id), job_name=workflow_id)
        return {"run_id": run_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start workflow")


@router.post('/jobs/workflows/{workflow_id}/stop')
async def stop_workflow(
    workflow_id: str,
    jobs_manager: JobsManager = Depends(get_jobs_manager),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        # Lookup installation and active run
        inst = workflow_installation_repo.get_by_workflow_id(db=db, workflow_id=workflow_id)
        if inst is None:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not installed")
        active_run_id = jobs_manager.get_active_run_id(int(inst.job_id))
        if not active_run_id:
            raise HTTPException(status_code=400, detail="Workflow is not running")
        jobs_manager.cancel_run(active_run_id)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop workflow")


@router.post('/jobs/workflows/{workflow_id}/pause')
async def pause_workflow(
    workflow_id: str,
    jobs_manager: JobsManager = Depends(get_jobs_manager),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        inst = workflow_installation_repo.get_by_workflow_id(db=db, workflow_id=workflow_id)
        if not inst:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not installed")
        jobs_manager.pause_job(int(inst.job_id))
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to pause workflow")


@router.post('/jobs/workflows/{workflow_id}/resume')
async def resume_workflow(
    workflow_id: str,
    jobs_manager: JobsManager = Depends(get_jobs_manager),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        inst = workflow_installation_repo.get_by_workflow_id(db=db, workflow_id=workflow_id)
        if not inst:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not installed")
        jobs_manager.resume_job(int(inst.job_id))
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to resume workflow")

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
