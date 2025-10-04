import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException

from src.common.manager_dependencies import get_jobs_manager
from src.controller.jobs_manager import JobsManager

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
