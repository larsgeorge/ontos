from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.common.dependencies import DBSessionDep, CurrentUserDep
from src.common.authorization import ApprovalChecker, PermissionChecker
from src.common.features import FeatureAccessLevel
from src.controller.approvals_manager import ApprovalsManager
from src.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["approvals"])


def get_approvals_manager(request: Request) -> ApprovalsManager:
    """Dependency provider for ApprovalsManager."""
    manager = getattr(request.app.state, 'approvals_manager', None)
    if not manager:
        # Create on-demand if not in app.state
        logger.warning("ApprovalsManager not found in app.state, creating new instance")
        manager = ApprovalsManager()
    return manager


@router.get('/approvals/queue')
async def get_approvals_queue(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    manager: ApprovalsManager = Depends(get_approvals_manager),
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY)),
):
    """Get all items awaiting approval (contracts, products, etc.)."""
    try:
        return manager.get_approvals_queue(db)
    except Exception as e:
        logger.exception("Failed to build approvals queue")
        raise HTTPException(status_code=500, detail="Failed to build approvals queue")


def register_routes(app):
    app.include_router(router)
    logger.info("Approvals routes registered")


