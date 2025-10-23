from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.common.dependencies import DBSessionDep, CurrentUserDep
from src.common.authorization import ApprovalChecker, PermissionChecker
from src.common.features import FeatureAccessLevel
from src.common.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["approvals"])


@router.get('/approvals/queue')
async def get_approvals_queue(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    _: bool = Depends(PermissionChecker('data-contracts', FeatureAccessLevel.READ_ONLY)),
):
    try:
        items: Dict[str, List[Dict[str, Any]]] = { 'contracts': [], 'products': [] }

        # Contracts awaiting approval (proposed or under_review)
        try:
            from src.db_models.data_contracts import DataContractDb
            q = db.query(DataContractDb).filter(DataContractDb.status.in_(['proposed', 'under_review']))
            for c in q.all():
                items['contracts'].append({ 'id': c.id, 'name': c.name, 'status': c.status })
        except Exception:
            logger.debug("Approvals queue: contracts query failed", exc_info=True)

        # Products pending certification
        try:
            from src.db_models.data_products import DataProductDb
            # ODPS v1.0.0: Query products in 'draft' status (awaiting approval to become 'active')
            q = db.query(DataProductDb).filter(DataProductDb.status == 'draft')
            for p in q.all():
                items['products'].append({ 'id': p.id, 'title': p.name, 'status': p.status })
        except Exception:
            logger.debug("Approvals queue: products query failed", exc_info=True)

        return items
    except Exception as e:
        logger.exception("Failed to build approvals queue")
        raise HTTPException(status_code=500, detail=str(e))


def register_routes(app):
    app.include_router(router)
    logger.info("Approvals routes registered")


