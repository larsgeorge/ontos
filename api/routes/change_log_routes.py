from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from api.common.dependencies import DBSessionDep, CurrentUserDep, require_permission
from api.common.features import FeatureAccessLevel
from api.db_models.change_log import ChangeLogDb
from api.repositories.change_log_repository import change_log_repo

router = APIRouter(prefix="/api", tags=["Change Log"]) 


@router.post("/change-log", dependencies=[Depends(lambda: require_permission(feature='audit', level=FeatureAccessLevel.READ_WRITE))])
async def create_change_log(
    request: Request,
    db: DBSessionDep,
    current_user: CurrentUserDep,
    payload: dict = Body(...)
):
    try:
        entity_type = payload.get('entity_type')
        entity_id = payload.get('entity_id')
        action = payload.get('action')
        details_json = payload.get('details_json')
        if not entity_type or not entity_id or not action:
            raise HTTPException(status_code=400, detail="entity_type, entity_id, and action are required")
        entry = ChangeLogDb(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            username=current_user.username if current_user else None,
            details_json=details_json,
        )
        db.add(entry)
        db.commit()
        return {"id": entry.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/change-log",
    dependencies=[Depends(lambda: require_permission(feature='audit', level=FeatureAccessLevel.READ))]
)
async def list_change_log(
    db: DBSessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
):
    try:
        rows = change_log_repo.list_filtered(
            db,
            skip=skip,
            limit=limit,
            entity_type=entity_type,
            entity_id=entity_id,
            username=username,
            action=action,
            start_time=start_time,
            end_time=end_time,
        )
        return [
            {
                'id': r.id,
                'entity_type': r.entity_type,
                'entity_id': r.entity_id,
                'action': r.action,
                'username': r.username,
                'timestamp': r.timestamp.isoformat() if r.timestamp else None,
                'details_json': r.details_json,
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def register_routes(app):
    app.include_router(router)

