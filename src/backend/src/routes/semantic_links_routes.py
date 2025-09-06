from typing import List
from fastapi import APIRouter, Depends, HTTPException, Body

from src.common.dependencies import DBSessionDep, AuditCurrentUserDep
from src.controller.semantic_links_manager import SemanticLinksManager
from src.models.semantic_links import EntitySemanticLink, EntitySemanticLinkCreate


router = APIRouter(prefix="/api/semantic-links", tags=["semantic-links"])


def get_manager(db: DBSessionDep) -> SemanticLinksManager:
    return SemanticLinksManager(db)


@router.get("/entity/{entity_type}/{entity_id}", response_model=List[EntitySemanticLink])
async def list_links(entity_type: str, entity_id: str, manager: SemanticLinksManager = Depends(get_manager)):
    try:
        return manager.list_for_entity(entity_id=entity_id, entity_type=entity_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/iri/{iri:path}", response_model=List[EntitySemanticLink])
async def list_links_by_iri(iri: str, manager: SemanticLinksManager = Depends(get_manager)):
    try:
        return manager.list_for_iri(iri=iri)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=EntitySemanticLink)
async def add_link(current_user: AuditCurrentUserDep, payload: EntitySemanticLinkCreate = Body(...), db: DBSessionDep = None, manager: SemanticLinksManager = Depends(get_manager)):
    try:
        created = manager.add(payload, created_by=(current_user.username if current_user else None))
        if db is not None:
            db.commit()
        return created
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{link_id}")
async def delete_link(link_id: str, db: DBSessionDep = None, manager: SemanticLinksManager = Depends(get_manager)):
    try:
        ok = manager.remove(link_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Link not found")
        if db is not None:
            db.commit()
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def register_routes(app):
    app.include_router(router)

