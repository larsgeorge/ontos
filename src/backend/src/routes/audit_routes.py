from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from src.common.dependencies import DBSessionDep, AuditManagerDep
from src.common.authorization import PermissionChecker
from src.common.features import FeatureAccessLevel
from src.models.audit_log import PaginatedAuditLogResponse

router = APIRouter(prefix="/api", tags=["Audit Trail"])

@router.get(
    "/audit",
    response_model=PaginatedAuditLogResponse,
)
async def get_audit_trail(
    db: DBSessionDep,
    audit_manager: AuditManagerDep,
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    start_time: Optional[datetime] = Query(None, description="Filter logs from this time (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="Filter logs up to this time (ISO 8601)"),
    username: Optional[str] = Query(None, description="Filter logs by username"),
    feature: Optional[str] = Query(None, description="Filter logs by feature name"),
    action: Optional[str] = Query(None, description="Filter logs by action type (e.g., CREATE, UPDATE, DELETE)"),
    success: Optional[bool] = Query(None, description="Filter logs by success status"),
    _: bool = Depends(PermissionChecker('audit', FeatureAccessLevel.READ_ONLY))
):
    """Retrieve audit log entries with optional filtering and pagination."""
    total, logs = await audit_manager.get_audit_logs(
        db=db,
        skip=skip,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
        username=username,
        feature=feature,
        action=action,
        success=success,
    )
    return PaginatedAuditLogResponse(total=total, items=logs)

# --- Register Routes --- #
def register_routes(app: APIRouter):
    """Register audit routes with the FastAPI app."""
    app.include_router(router)
    # Optional: Add logging confirmation
    # from src.common.logging import get_logger
    # logger = get_logger(__name__)
    # logger.info("Audit routes registered") 